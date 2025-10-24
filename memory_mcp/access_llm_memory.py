from mcp.server.fastmcp import FastMCP
from qdrant_client import QdrantClient
from openai import OpenAI
import os, dotenv

dotenv.load_dotenv()

mcp = FastMCP()
qdrant = QdrantClient()
openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

collection_name = "chat_messages"

@mcp.tool()
def search_vector_db(query: str, top_k: int = 5) -> list:
    """
    Search the vector database for similar entries to the query.
    """

    query_embedding_response = openai.embeddings.create(
        input=query,
        model="text-embedding-3-small"
    )
    query_embedding = query_embedding_response.data[0].embedding
    # print(query_embedding)

    results = qdrant.search(
        collection_name=collection_name,
        query_vector=query_embedding,
    )
    return results


if __name__ == "__main__":
    mcp.run()