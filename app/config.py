import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY= os.getenv("OPENAI_API_KEY")
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "codebase_chunks")

EMBEDDING_MODEL = "text-embedding-3-small"
CHAT_MODEL = "gpt-4.1-mini"

VECTOR_SIZE = 384