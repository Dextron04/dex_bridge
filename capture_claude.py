# save_and_parse_claude_stream.py
import re
import os
import json
import time
import gzip
import subprocess
from mitmproxy import http, ctx

HOST_RE = re.compile(r"(?:^|\.)claude\.ai$", re.IGNORECASE)
PATH_RE = re.compile(r"^/api/organizations/[^/]+/chat_conversations/[^/]+/completion$", re.IGNORECASE)
OUT_DIR = "./parsed_matches"
os.makedirs(OUT_DIR, exist_ok=True)


def try_json_load(s):
    try:
        return json.loads(s)
    except Exception:
        return None


def extract_text_from_event(obj):
    """
    Extract streaming text pieces from Claude event JSON.
    Returns a list of text pieces (may be empty).
    Handles Claude-specific formats:
      - {"type":"content_block_start", "content_block":{"text":"..."}}
      - {"type":"content_block_delta", "delta":{"type":"text_delta","text":"..."}}
      - {"completion": "..."} (older format)
    """
    pieces = []

    if not isinstance(obj, dict):
        return pieces

    # 1) Claude content_block_start format
    if obj.get("type") == "content_block_start":
        content_block = obj.get("content_block", {})
        if isinstance(content_block, dict):
            text = content_block.get("text")
            if isinstance(text, str):
                pieces.append(text)

    # 2) Claude content_block_delta format (most common for streaming)
    if obj.get("type") == "content_block_delta":
        delta = obj.get("delta", {})
        if isinstance(delta, dict) and delta.get("type") == "text_delta":
            text = delta.get("text")
            if isinstance(text, str):
                pieces.append(text)

    # 3) Claude-specific: direct "completion" field (older format)
    completion = obj.get("completion")
    if isinstance(completion, str):
        pieces.append(completion)

    # 4) Generic delta format
    delta = obj.get("delta")
    if isinstance(delta, dict):
        text = delta.get("text")
        if isinstance(text, str) and not pieces:  # Only if not already extracted
            pieces.append(text)
    
    # 5) top-level typical 'choices' streaming format (fallback)
    choices = obj.get("choices")
    if isinstance(choices, list):
        for c in choices:
            # delta.content (streaming API)
            delta = c.get("delta", {})
            if isinstance(delta, dict):
                cont = delta.get("content")
                if isinstance(cont, str):
                    pieces.append(cont)
            # older shape: "text"
            text = c.get("text")
            if isinstance(text, str):
                pieces.append(text)

    # 6) direct top-level "text" / "content"
    if isinstance(obj.get("text"), str) and not pieces:
        pieces.append(obj.get("text"))
    if isinstance(obj.get("content"), str) and not pieces:
        pieces.append(obj.get("content"))

    return pieces


def parse_sse_like(text):
    """
    Parse SSE-like text into a list of JSON-parsed events.
    Claude SSE format looks like:
      event: content_block_start
      data: {"type":"content_block_start",...}
      
      event: content_block_delta
      data: {"type":"content_block_delta","delta":{"type":"text_delta","text":"..."}}
    
    We look for event: and data: pairs.
    """
    events = []
    lines = text.split("\n")
    i = 0
    
    while i < len(lines):
        line = lines[i].strip()
        
        # Skip empty lines
        if not line:
            i += 1
            continue
        
        # Look for event: line followed by data: line
        if line.startswith("event:"):
            event_type = line[len("event:"):].strip()
            i += 1
            
            # Next line should be data:
            if i < len(lines):
                data_line = lines[i].strip()
                if data_line.startswith("data:"):
                    data_content = data_line[len("data:"):].strip()
                    
                    if data_content and data_content != "[DONE]":
                        obj = try_json_load(data_content)
                        if obj is not None:
                            # Add event type to the object for reference
                            obj["_event_type"] = event_type
                            events.append(obj)
                        else:
                            events.append({"_raw": data_content, "_event_type": event_type})
            i += 1
            
        # Handle standalone data: lines (no event: prefix)
        elif line.startswith("data:"):
            data_content = line[len("data:"):].strip()
            if data_content and data_content != "[DONE]":
                obj = try_json_load(data_content)
                if obj is not None:
                    events.append(obj)
                else:
                    events.append({"_raw": data_content})
            i += 1
        else:
            # Try to parse as JSON directly
            obj = try_json_load(line)
            if obj is not None:
                events.append(obj)
            i += 1
    
    return events


def parse_ndjson_like(text):
    """
    Parse NDJSON where each newline is a JSON object.
    """
    events = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line == "[DONE]":
            continue
        obj = try_json_load(line)
        if obj is not None:
            events.append(obj)
        else:
            events.append({"_raw": line})
    return events


class ClaudeStreamParserAddon:
    def __init__(self):
        self.response_buffers = {}
    
    def responseheaders(self, flow: http.HTTPFlow) -> None:
        """
        Called when response headers are received, before the body.
        Disable streaming for responses we want to capture.
        """
        try:
            host = getattr(flow.request, "host", None) or getattr(flow.request, "pretty_host", "")
            path = getattr(flow.request, "path", None)
            if path is None:
                url = getattr(flow.request, "pretty_url", "")
                path = re.sub(r"^https?://[^/]+", "", url)
        except Exception:
            return

        if HOST_RE.search(host) and PATH_RE.search(path):
            # Disable streaming for this response so we can capture the full content
            flow.response.stream = False
            ctx.log.info(f"[CLAUDE PARSER] disabled streaming for {host}{path}")
    
    def response(self, flow: http.HTTPFlow) -> None:
        # Only operate on matching host/path
        try:
            host = getattr(flow.request, "host", None) or getattr(flow.request, "pretty_host", "")
            path = getattr(flow.request, "path", None)
            if path is None:
                url = getattr(flow.request, "pretty_url", "")
                path = re.sub(r"^https?://[^/]+", "", url)
        except Exception:
            return

        if not (HOST_RE.search(host) and PATH_RE.search(path)):
            return

        ctx.log.info(f"[CLAUDE PARSER] matched response for {host}{path}")

        # Get response text - mitmproxy handles decompression automatically
        text = None
        
        try:
            # Use get_text which automatically handles content-encoding
            text = flow.response.get_text(strict=False)
            
            if text:
                ctx.log.info(f"[CLAUDE PARSER] got response text, length: {len(text)}")
            
        except Exception as e:
            ctx.log.warn(f"[CLAUDE PARSER] failed to get response text: {e}")
            
            # Fallback: try to decode raw content manually
            try:
                if getattr(flow.response, "raw_content", None) is not None:
                    raw_bytes = flow.response.raw_content
                elif getattr(flow.response, "content", None) is not None:
                    raw_bytes = flow.response.content
                else:
                    raw_bytes = None
                
                if raw_bytes:
                    # Check if it's gzip compressed
                    if raw_bytes[:2] == b'\x1f\x8b':
                        text = gzip.decompress(raw_bytes).decode("utf-8", errors="replace")
                        ctx.log.info("[CLAUDE PARSER] manually decompressed gzip")
                    else:
                        text = raw_bytes.decode("utf-8", errors="replace")
            except Exception as e2:
                ctx.log.warn(f"[CLAUDE PARSER] manual decode also failed: {e2}")

        if not text:
            ctx.log.warn("[CLAUDE PARSER] no response text to parse")
            return

        # Extract user input from request body
        user_input = None
        request_data = None
        parent_message_uuid = None
        try:
            request_text = flow.request.get_text(strict=False)
            if request_text:
                request_data = try_json_load(request_text)
                if request_data:
                    # Claude request format: {"prompt": "...", "parent_message_uuid": "...", ...}
                    user_input = request_data.get("prompt")
                    parent_message_uuid = request_data.get("parent_message_uuid")
                    ctx.log.info(f"[CLAUDE PARSER] extracted user prompt: {user_input[:50] if user_input else 'None'}...")
        except Exception as e:
            ctx.log.warn(f"[CLAUDE PARSER] failed to parse request body: {e}")

        # Heuristic: try SSE -> NDJSON -> full JSON
        events = parse_sse_like(text)
        if not events:
            events = parse_ndjson_like(text)
        if not events:
            # try full JSON parse
            obj = try_json_load(text)
            if obj is not None:
                events = [obj]

        # Extract textual pieces from each event
        pieces = []
        parsed_events = []
        for e in events:
            parsed_events.append(e)
            extracted = extract_text_from_event(e)
            if extracted:
                pieces.extend(extracted)

        reconstructed_text = "".join(pieces).strip()

        # Extract conversation_id from URL path
        conversation_id = None
        conv_match = re.search(r"/chat_conversations/([^/]+)/", path)
        if conv_match:
            conversation_id = conv_match.group(1)
        
        # Also check events if not found in URL
        if not conversation_id:
            for e in parsed_events:
                if isinstance(e, dict) and "conversation_id" in e:
                    conversation_id = e["conversation_id"]
                    break

        # Build final JSON structure
        result = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "request_url": flow.request.url,
            "host": host,
            "path": path,
            "conversation_id": conversation_id,
            "user_input": user_input,
            "parent_message_uuid": parent_message_uuid,
            "reconstructed_text": reconstructed_text,
            "events_count": len(events),
            "parsed_events_preview": parsed_events,  # save all events, not just preview
        }

        # Create provider-specific subdirectory
        safe_host = re.sub(r"[^\w\-\_\.]", "_", host)
        provider_dir = os.path.join(OUT_DIR, safe_host)
        os.makedirs(provider_dir, exist_ok=True)

        # write pretty JSON using conversation_id and timestamp
        ts = time.strftime("%Y%m%dT%H%M%S")
        if conversation_id:
            fname = os.path.join(provider_dir, f"{conversation_id}__{ts}__conversation_parsed.json")
        else:
            fname = os.path.join(provider_dir, f"{ts}__conversation_parsed.json")
        
        try:
            with open(fname, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            ctx.log.info(f"[CLAUDE PARSER] wrote parsed JSON -> {fname}")
            
            # Auto-run merge script
            try:
                ctx.log.info("[CLAUDE PARSER] running merge script...")
                subprocess.Popen(
                    ["python", "merge_conversations.py"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            except Exception as e:
                ctx.log.warn(f"[CLAUDE PARSER] failed to run merge script: {e}")
                
        except Exception as e:
            ctx.log.warn(f"[CLAUDE PARSER] failed to write {fname}: {e}")


addons = [
    ClaudeStreamParserAddon()
]
