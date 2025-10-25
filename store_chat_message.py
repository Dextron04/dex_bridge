import dotenv
import os
import json
import glob
import uuid
import hashlib
import ssl
import httpx
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, Filter, FieldCondition, MatchValue
from openai import OpenAI


dotenv.load_dotenv()
qdrant = QdrantClient(host="localhost", port=6333)

# Create custom httpx client that doesn't verify SSL (for proxy environments)
# This is needed when running through mitmproxy or in environments with SSL certificate issues
http_client = httpx.Client(verify=False)

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    http_client=http_client
)

collection_name = "chat_messages"

# Use create_collection instead of deprecated recreate_collection
if not qdrant.collection_exists(collection_name):
    qdrant.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
    )
    print(f"Created collection: {collection_name}")
else:
    print(f"Collection {collection_name} already exists, will skip duplicates")

# Load conversations from merged_conversations directory (ChatGPT only)
MERGED_DIR = "./merged_conversations/chatgpt.com"
conversation_files = glob.glob(os.path.join(MERGED_DIR, "*__conversation_merged.json"))

print(f"Found {len(conversation_files)} ChatGPT conversations\n")

def get_embedding(text):
    response = client.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
    return response.data[0].embedding

def generate_content_hash(text):
    """Generate SHA256 hash of text content for deduplication."""
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

def check_if_exists(content_hash):
    """Check if a message with this content hash already exists in Qdrant."""
    try:
        results = qdrant.scroll(
            collection_name=collection_name,
            scroll_filter=Filter(
                must=[
                    FieldCondition(
                        key="content_hash",
                        match=MatchValue(value=content_hash)
                    )
                ]
            ),
            limit=1
        )
        return len(results[0]) > 0
    except Exception as e:
        return False

# Load each conversation
for filepath in conversation_files:
    with open(filepath, 'r', encoding='utf-8') as f:
        conversation = json.load(f)
    
    conversation_id = conversation['conversation_id']
    provider = conversation.get('provider', 'chatgpt.com')

    points = []
    skipped_count = 0
    inserted_count = 0
    
    print(f"Loading ChatGPT conversation: {conversation_id}")
    
    # You can access:
    # - conversation_id: The unique conversation ID
    # - conversation['exchanges']: List of all exchanges
    # - Each exchange has: user_input, assistant_response, timestamp, model, etc.

    for idx, exch in enumerate(conversation["exchanges"], start=1):
        user_input = exch["user_input"].strip()
        user_content_hash = generate_content_hash(user_input)
        
        # Check if user message already exists
        if check_if_exists(user_content_hash):
            print(f"  Skipping exchange {idx}: User message already exists (hash: {user_content_hash[:16]}...)")
            skipped_count += 1
        else:
            user_vector = get_embedding(user_input)
            
            # Generate UUID for Qdrant point ID
            user_point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{conversation_id}__user__{exch['user_message_id']}"))
            print(f"  Processing exchange {idx}: User message ID {exch['user_message_id']}, Point ID {user_point_id}")

            
            points.append({
                "id": user_point_id,
                "vector": user_vector,
                "payload": {
                    "conversation_id": conversation_id,
                    "role": "user",
                    "text": user_input,
                    "timestamp": exch["timestamp"],
                    "message_id": exch["user_message_id"],
                    "model": exch.get("model", ""),
                    "exchange_index": idx,
                    "provider": provider,
                    "content_hash": user_content_hash,
                }
            })
            inserted_count += 1

        if exch.get("assistant_response"):
            assistant_response = exch["assistant_response"].strip()
            assistant_content_hash = generate_content_hash(assistant_response)
            
            # Check if assistant message already exists
            if check_if_exists(assistant_content_hash):
                print(f"  Skipping exchange {idx}: Assistant message already exists (hash: {assistant_content_hash[:16]}...)")
                skipped_count += 1
            else:
                assistant_vector = get_embedding(assistant_response)
                
                # Generate UUID for Qdrant point ID
                assistant_msg_id = exch['assistant_message_id'] or exch['user_message_id']
                assistant_point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{conversation_id}__assistant__{assistant_msg_id}"))
                
                points.append({
                    "id": assistant_point_id,
                    "vector": assistant_vector,
                    "payload": {
                        "conversation_id": conversation_id,
                        "role": "assistant",
                        "text": assistant_response,
                        "timestamp": exch["timestamp"],
                        "message_id": exch["assistant_message_id"],
                        "model": exch.get("model", ""),
                        "exchange_index": idx,
                        "provider": provider,
                        "content_hash": assistant_content_hash,
                    }
                })
                inserted_count += 1

    if points:
        qdrant.upsert(
            collection_name=collection_name,
            points=points
        )
        print(f"✓ Inserted {len(points)} messages from conversation {conversation_id}")
    else:
        print(f"⊘ No new messages to insert from conversation {conversation_id}")
    
    print(f"  Stats: {inserted_count} inserted, {skipped_count} skipped (duplicates)\n")



    
    # Example: Print first exchange
    # if conversation['exchanges']:
    #     first_exchange = conversation['exchanges'][0]
    #     second_exchange = conversation['exchanges'][1] if len(conversation['exchanges']) > 1 else None
    #     print(f"  First message: {first_exchange.get('user_input', '')[:50]}...")
    #     print(f"  Second message: {second_exchange.get('assistant_response', '')[:50]}..." if second_exchange else "  Second message: None")

