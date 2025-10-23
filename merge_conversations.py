#!/usr/bin/env python3
"""
Merge parsed ChatGPT conversation streams into a readable format.
Groups messages by conversation_id and extracts user inputs and assistant responses.
"""

import json
import os
import glob
from datetime import datetime
from collections import defaultdict


def extract_text_from_patches(events):
    """Extract text content from patch events in the stream."""
    text_parts = []
    
    for event in events:
        if isinstance(event, dict):
            # Handle patch operations that append text
            if event.get("o") == "patch" and "v" in event:
                for patch in event["v"]:
                    if isinstance(patch, dict):
                        # Check for path targeting message content parts
                        if patch.get("p", "").endswith("/message/content/parts/0") and patch.get("o") == "append" and "v" in patch:
                            text_parts.append(patch["v"])
            
            # Also check for direct 'v' arrays with patches (more common format)
            elif "v" in event and isinstance(event["v"], list):
                for patch in event["v"]:
                    if isinstance(patch, dict):
                        # Check for path targeting message content parts
                        if patch.get("p", "").endswith("/message/content/parts/0") and patch.get("o") == "append" and "v" in patch:
                            text_parts.append(patch["v"])
    
    return "".join(text_parts)


def parse_conversation_file(filepath):
    """Parse a single conversation file and extract key information."""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    result = {
        "file": os.path.basename(filepath),
        "timestamp": data.get("timestamp"),
        "request_url": data.get("request_url"),
        "events_count": data.get("events_count"),
        "conversation_id": data.get("conversation_id"),  # First check top-level conversation_id
        "user_message": None,
        "assistant_response": None,
        "metadata": {}
    }
    
    # Check if this is a Claude conversation (has user_input at top level)
    if "user_input" in data:
        result["user_message"] = {
            "id": None,
            "content": data.get("user_input"),
            "create_time": None,
            "metadata": {
                "parent_message_uuid": data.get("parent_message_uuid"),
            }
        }
        # For Claude, reconstructed_text is the assistant response
        result["assistant_response"] = data.get("reconstructed_text", "")
        
        # Extract metadata from Claude events
        events = data.get("parsed_events_preview", [])
        for event in events:
            if not isinstance(event, dict):
                continue
            
            # Extract message_start metadata for Claude
            if event.get("type") == "message_start":
                message = event.get("message", {})
                result["metadata"]["assistant_message_id"] = message.get("id")
                result["metadata"]["assistant_uuid"] = message.get("uuid")
                result["metadata"]["parent_uuid"] = message.get("parent_uuid")
                result["metadata"]["model"] = message.get("model", "claude")
    
    else:
        # ChatGPT format - parse from events
        events = data.get("parsed_events_preview", [])
        
        for event in events:
            if not isinstance(event, dict):
                continue
            
            # Extract conversation ID from events if not found at top level
            if "conversation_id" in event and not result["conversation_id"]:
                result["conversation_id"] = event["conversation_id"]
            
            # Extract user input message
            if event.get("type") == "input_message":
                input_msg = event.get("input_message", {})
                result["user_message"] = {
                    "id": input_msg.get("id"),
                    "content": input_msg.get("content", {}).get("parts", [""])[0],
                    "create_time": input_msg.get("create_time"),
                    "metadata": {
                        "request_id": input_msg.get("metadata", {}).get("request_id"),
                        "turn_exchange_id": input_msg.get("metadata", {}).get("turn_exchange_id"),
                        "parent_id": input_msg.get("metadata", {}).get("parent_id"),
                    }
                }
            
            # Extract assistant message metadata
            if event.get("o") == "add" and "v" in event:
                v = event["v"]
                if isinstance(v, dict) and "message" in v:
                    msg = v["message"]
                    if msg.get("author", {}).get("role") == "assistant":
                        result["metadata"]["assistant_message_id"] = msg.get("id")
                        result["metadata"]["model_slug"] = msg.get("metadata", {}).get("model_slug")
                        result["metadata"]["parent_id"] = msg.get("metadata", {}).get("parent_id")
            
            # Extract server metadata
            if event.get("type") == "server_ste_metadata":
                result["metadata"]["server_metadata"] = {
                    "model_slug": event.get("metadata", {}).get("model_slug"),
                    "is_first_turn": event.get("metadata", {}).get("is_first_turn"),
                    "fast_convo": event.get("metadata", {}).get("fast_convo"),
                    "warmup_state": event.get("metadata", {}).get("warmup_state"),
                    "message_id": event.get("metadata", {}).get("message_id"),
                    "request_id": event.get("metadata", {}).get("request_id"),
                }
        
        # Extract assistant response text from patches (ChatGPT)
        result["assistant_response"] = extract_text_from_patches(events)
    
    return result


def merge_conversations(parsed_dir="./parsed_matches", output_dir="./merged_conversations"):
    """Merge all parsed conversation files grouped by conversation_id."""
    
    # Create output directory structure
    os.makedirs(output_dir, exist_ok=True)
    
    # Find all parsed JSON files (including in subdirectories)
    pattern = os.path.join(parsed_dir, "**", "*_parsed.json")
    files = sorted(glob.glob(pattern, recursive=True))
    
    # Also check for files directly in parsed_dir (backward compatibility)
    direct_pattern = os.path.join(parsed_dir, "*_parsed.json")
    direct_files = glob.glob(direct_pattern)
    
    # Combine and deduplicate
    all_files = list(set(files + direct_files))
    
    if not all_files:
        print(f"No parsed files found in {parsed_dir}")
        return
    
    print(f"Found {len(all_files)} parsed conversation files")
    
    # Group by provider and conversation_id
    conversations_by_provider = defaultdict(lambda: defaultdict(list))
    
    for filepath in all_files:
        try:
            parsed = parse_conversation_file(filepath)
            conv_id = parsed.get("conversation_id")
            
            if conv_id:
                # Determine provider from file path
                provider = None
                if "chatgpt.com" in filepath:
                    provider = "chatgpt.com"
                elif "claude.ai" in filepath:
                    provider = "claude.ai"
                else:
                    provider = "unknown"
                
                conversations_by_provider[provider][conv_id].append(parsed)
            else:
                print(f"Warning: No conversation_id found in {filepath}")
                
        except Exception as e:
            print(f"Error parsing {filepath}: {e}")
    
    # Process each provider
    total_conversations = 0
    total_exchanges = 0
    
    for provider, conversations in conversations_by_provider.items():
        print(f"\n{'='*60}")
        print(f"Processing {provider} conversations")
        print(f"{'='*60}")
        
        # Create provider subdirectory
        provider_dir = os.path.join(output_dir, provider)
        os.makedirs(provider_dir, exist_ok=True)
        
        # Sort exchanges within each conversation by timestamp
        for conv_id in conversations:
            conversations[conv_id].sort(key=lambda x: x.get("timestamp", ""))
        
        # Create output for each conversation
        for conv_id, exchanges in conversations.items():
            total_conversations += 1
            total_exchanges += len(exchanges)
            
            conversation = {
                "conversation_id": conv_id,
                "provider": provider,
                "exchange_count": len(exchanges),
                "first_timestamp": exchanges[0].get("timestamp") if exchanges else None,
                "last_timestamp": exchanges[-1].get("timestamp") if exchanges else None,
                "exchanges": []
            }
            
            for exchange in exchanges:
                exchange_data = {
                    "timestamp": exchange.get("timestamp"),
                    "file_source": exchange.get("file"),
                    "user_input": exchange.get("user_message", {}).get("content") if exchange.get("user_message") else None,
                    "assistant_response": exchange.get("assistant_response"),
                    "user_message_id": exchange.get("user_message", {}).get("id") if exchange.get("user_message") else None,
                    "assistant_message_id": exchange.get("metadata", {}).get("assistant_message_id"),
                    "model": exchange.get("metadata", {}).get("model") or
                             exchange.get("metadata", {}).get("model_slug") or 
                             exchange.get("metadata", {}).get("server_metadata", {}).get("model_slug"),
                    "metadata": exchange.get("metadata")
                }
                
                conversation["exchanges"].append(exchange_data)
            
            # Sort exchanges by timestamp
            conversation["exchanges"].sort(key=lambda x: x.get("timestamp", ""))
            
            # Write individual conversation file
            conv_filename = f"{conv_id}__conversation_merged.json"
            conv_filepath = os.path.join(provider_dir, conv_filename)
            
            with open(conv_filepath, 'w', encoding='utf-8') as f:
                json.dump(conversation, f, indent=2, ensure_ascii=False)
            
            print(f"  ✓ {conv_id}: {len(exchanges)} exchanges -> {conv_filename}")
            
            # Print conversation summary
            for i, ex in enumerate(conversation['exchanges'], 1):
                user_input = ex['user_input']
                if user_input:
                    preview = user_input[:60] + "..." if len(user_input) > 60 else user_input
                    print(f"      [{i}] User: {preview}")
                
                response = ex['assistant_response']
                if response:
                    preview = response[:60] + "..." if len(response) > 60 else response
                    print(f"          Assistant: {preview}")
    
    # Create summary file
    summary = {
        "merge_timestamp": datetime.now().isoformat(),
        "total_conversations": total_conversations,
        "total_exchanges": total_exchanges,
        "providers": {
            provider: {
                "conversation_count": len(convs),
                "exchange_count": sum(len(exs) for exs in convs.values()),
                "conversation_ids": list(convs.keys())
            }
            for provider, convs in conversations_by_provider.items()
        }
    }
    
    summary_file = os.path.join(output_dir, "merge_summary.json")
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*60}")
    print(f"✓ Total: {total_exchanges} exchanges from {total_conversations} conversations")
    print(f"✓ Output directory: {output_dir}")
    print(f"✓ Summary file: {summary_file}")
    print(f"{'='*60}")
    
    return summary


if __name__ == "__main__":
    import sys
    
    parsed_dir = sys.argv[1] if len(sys.argv) > 1 else "./parsed_matches"
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "./merged_conversations"
    
    merge_conversations(parsed_dir, output_dir)
