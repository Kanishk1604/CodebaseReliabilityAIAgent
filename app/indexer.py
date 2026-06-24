import os
from pathlib import Path 
from uuid import uuid4

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

from app.config import QDRANT_URL, COLLECTION_NAME, VECTOR_SIZE
from app.embeddings import embed_text
from app.symbol_extractor import extract_symbol_metadata

from collections import Counter
# counter is a dictionary

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


def get_indexed_summary() -> dict:
    collection_info = client.get_collection(COLLECTION_NAME)

    return{
        "collection_name": COLLECTION_NAME,
        "vector_count": collection_info.points_count,
        "vector_size": collection_info.config.params.vectors.size,
        "distance": collection_info.config.params.vectors.distance,

    }

#beginning of observability
def get_extension_summary(limit: int=1000) -> dict:
    #we store PointStruct... , each store object is a point
    # Qdrant returns ([point1, point2, point3],
    #                 next_page_offset)
    #we only care about points, so points, _ 
    # _ => ignore second value

    points, _ = client.scroll(
        collection_name=COLLECTION_NAME,
        limit=limit,
        with_payload=True,      #we want metadata 
        with_vectors=False,       #we dont want the vectors since they are numbers
    )

    counter = Counter() #this creates a dictionary called counter

    for point in points:
        extension = point.payload.get("extension", "unknown")   #unknown if extension isnt available
        counter[extension] += 1
    
    return {
        "collection_name": COLLECTION_NAME,
        "total_scanned_objects": len(points),
        "extensions": dict(counter),
    }

def get_file_inventory(limit: int =1000) -> dict:

    points, _ = client.scroll(
        collection_name= COLLECTION_NAME,
        limit=limit,
        with_payload=True,
        with_vectors=False,
    )

    counter = Counter()

    for point in points:
        file_name = point.payload.get("file_path")
        counter[file_name] +=1

    sorted_inventory = sorted(counter.items(),key = lambda item:item[1], reverse=True)

    return{
        "collection_name": COLLECTION_NAME,
        "inventory": [{
            "file_path": file_path,
            "chunk_count": chunk,
        }
        for file_path, chunk in sorted_inventory
        ],
    }

def reset_index() -> dict:
    collections = client.get_collections().collections
    existing_names = {collection.name for collection in collections}

    if COLLECTION_NAME in existing_names:
        client.delete_collection(collection_name= COLLECTION_NAME)

        return{
            "status": "deleted",
            "collection_name": COLLECTION_NAME,
        }
    
    return {
        "status": "not_found",
        "collection_name":  COLLECTION_NAME,
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

#strip removes whitespaces
def chunk_text(text:str, max_lines = 80) -> list[dict]:
    chunks = []
    lines = text.splitlines()

    for start in range(0,len(lines), max_lines):
        end = min(start+max_lines, len(lines))
        chunk = "\n".join(lines[start:end]).strip()

        if chunk:
            chunks.append({
                "content": chunk,
                "start_line": start+1,
                "end_line": end,
            })
    
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
            embedding = embed_text(chunk["content"])
            
            symbol_metadata = extract_symbol_metadata(chunk["content"], file_path.suffix)

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
                        "start_line": chunk["start_line"],
                        "end_line": chunk["end_line"],
                        "content": chunk["content"],
                        #symbol & symboltype
                        "symbol": symbol_metadata["symbol"],
                        "symbol_type": symbol_metadata["symbol_type"],
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

