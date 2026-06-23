import os
from pathlib import Path 
from uuid import uuid4

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

from app.config import QDRANT_URL, COLLECTION_NAME, VECTOR_SIZE
from app.embeddings import embed_text

client = QdrantClient(url=QDRANT_URL)

ALLOWED_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx",
    ".java", ".go", ".rs", ".cpp", ".c", ".h",
    ".md", ".yaml", ".yml"
}

IGNORED_DIRS = {
    ".git", "node_modules", "venv", ".venv", "__pycache__",
    "dist", "build", ".next", "coverage",
    "bin", "obj", ".vs",
    ".angular", "cache"
}

def ensure_collection() ->None:
    collections = client.get_collections().collections
    existing_names = {collection.name for collection in collections}

    if COLLECTION_NAME not in existing_names:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size = VECTOR_SIZE,
                distance = Distance.COSINE,
            ),
        )

def should_index_file(path: Path) -> bool:
    if path.suffix not in ALLOWED_EXTENSIONS:
        return False

    if any(part in IGNORED_DIRS for part in path.parts):
        return False

    return True

def chunk_text(text:str, max_char: int=2000) -> list[str]:
    chunks = []

    for i in range(0,len(text), max_char):
        chunk = text[i:i+max_char].strip()
        if chunk:
            chunks.append(chunk)
    
    return chunks

def index_repository(repo_path: str) -> dict:
    ensure_collection()

    root = Path(repo_path).resolve()

    if not root.exists():
        raise ValueError(f"Repository path does not exist: {repo_path}")

    points = []
    indexed_files = 0
    indexed_chunks = 0

    for file_path in root.rglob("*"):
        if not file_path.is_file():
            continue
        
        if not should_index_file(file_path):
            continue
        
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        
        except Exception:
            continue
        
        relative_path = str(file_path.relative_to(root))

        chunks = chunk_text(content)

        if not chunks:
            continue

        indexed_files +=1

        for chunk_index, chunk in enumerate(chunks):
            embedding = embed_text(chunk)

            points.append(
                PointStruct(
                    id = str(uuid4()),
                    vector=embedding,
                    payload={
                        "repo_path": str(root),
                        "file_path": relative_path,
                        "file_name": file_path.name,
                        "extension": file_path.suffix,
                        "chunk_index": chunk_index,
                        "content": chunk,
                    },
                )
            )

            indexed_chunks += 1

    if points:
        client.upsert(
            collection_name= COLLECTION_NAME,
            points = points,
        )

    return{
        "repo_path": str(root),
        "indexed_files": indexed_files,
        "indexed_chunks": indexed_chunks,
    }