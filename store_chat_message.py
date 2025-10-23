import dotenv
import os
import json
import glob
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance
from openai import OpenAI


dotenv.load_dotenv()
qdrant = QdrantClient(host="localhost", port=6333)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

collection_name = "chat_messages"
qdrant.recreate_collection(
    collection_name=collection_name,
    vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
)

# Load conversations from merged_conversations directory (ChatGPT only)
MERGED_DIR = "./merged_conversations/chatgpt.com"
conversation_files = glob.glob(os.path.join(MERGED_DIR, "*__conversation_merged.json"))

print(f"Found {len(conversation_files)} ChatGPT conversations\n")

# Load each conversation
for filepath in conversation_files:
    with open(filepath, 'r', encoding='utf-8') as f:
        conversation = json.load(f)
    
    conversation_id = conversation['conversation_id']
    provider = conversation.get('provider', 'chatgpt.com')
    
    print(f"Loading ChatGPT conversation: {conversation_id}")
    
    # You can access:
    # - conversation_id: The unique conversation ID
    # - conversation['exchanges']: List of all exchanges
    # - Each exchange has: user_input, assistant_response, timestamp, model, etc.
    
    # Example: Print first exchange
    if conversation['exchanges']:
        first_exchange = conversation['exchanges'][0]
        second_exchange = conversation['exchanges'][1] if len(conversation['exchanges']) > 1 else None
        print(f"  First message: {first_exchange.get('user_input', '')[:50]}...")
        print(f"  Second message: {second_exchange.get('assistant_response', '')[:50]}..." if second_exchange else "  Second message: None")


# Example usage with conversation_id
# conversation_id = conversation["conversation_id"]

# embedding = client.embeddings.create(
#     model="text-embedding-3-small",
#     input=message
# ).data[0].embedding

# qdrant.upsert(
#     collection_name=collection_name,
#     points=[
#         {
#             "id": 1,
#             "vector": embedding,
#             "payload": {
#                 "role": "user",
#                 "message": message
#             }
#         }
#     ]
# )

# print("Message stored in Qdrant collection.")
