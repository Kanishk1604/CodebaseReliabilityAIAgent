from qdrant_client import QdrantClient

from app.config import QDRANT_URL, COLLECTION_NAME

client = QdrantClient(url=QDRANT_URL)

def extract_symbol_metadata(chunk_content: str, extension: str) -> dict:
    