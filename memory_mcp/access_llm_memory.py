from mcp.server.fastmcp import FastMCP
from qdrant_client import QdrantClient
from openai import OpenAI
import httpx
import os, dotenv

dotenv.load_dotenv()

mcp = FastMCP()
qdrant = QdrantClient()

# Create custom httpx client with timeout and no SSL verification
http_client = httpx.Client(
    verify=False,
    timeout=60.0  # 60 second timeout
)

openai = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    http_client=http_client,
    max_retries=3  # Retry up to 3 times
)

collection_name = "chat_messages"

@mcp.tool()
def search_memory(query: str, top_k: int = 5) -> list:
    """
    Search the vector database for similar entries to the query.
    """
    try:
        query_embedding_response = openai.embeddings.create(
            input=query,
            model="text-embedding-3-small"
        )
        query_embedding = query_embedding_response.data[0].embedding
        
        results = qdrant.search(
            collection_name=collection_name,
            query_vector=query_embedding,
            limit=top_k
        )
        
        if results is None:
            return []
        
        # Format results for better readability
        # formatted_results = []
        # for result in results:
        #     formatted_results.append({
        #         "score": result.score,
        #         "text": result.payload.get("text", ""),
        #         "role": result.payload.get("role", ""),
        #         "timestamp": result.payload.get("timestamp", ""),
        #         "conversation_id": result.payload.get("conversation_id", ""),
        #         "model": result.payload.get("model", "")
        #     })
        
        return results
    
    except Exception as e:
        error_msg = f"Error searching vector database: {str(e)}"
        print(error_msg)
        return [{"error": error_msg}]


if __name__ == "__main__":
    mcp.run()