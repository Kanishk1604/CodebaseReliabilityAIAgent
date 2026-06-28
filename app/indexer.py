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

from app.ast_symbol_extractor import extract_ast_symbols 

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

def get_graph_summary(limit: int =1000) -> dict:
    points, _ = client.scroll(
        collection_name= COLLECTION_NAME,
        limit=limit,
        with_payload=True,
        with_vectors=False,
    )
    seen_import_files = set()
    seen_call_files = set()
    counter_import_files = 0
    counter_call_files = 0
    total_imported_symbols = 0
    total_calls = 0

    counter_symbols = Counter()
    counter_methods = Counter()

    max_method_frequency = 0
    max_imported_symbol_frequency = 0

    methods_with_most_frequency = []
    imported_symbols_with_most_frequency = []

    for point in points: 
        #imports
        imports = point.payload.get("imports")
        if imports:
            
            # How many files have imports?
            file_name = point.payload.get("file_path")
            
            if file_name not in seen_import_files:
                seen_import_files.add(file_name)
                counter_import_files += 1

            #What symbols are imported most?
            for imported in imports:
                imported_symbol_names = imported["imported_symbols"]
                for imported_symbol_name in imported_symbol_names:
                    counter_symbols[imported_symbol_name] += 1
                    total_imported_symbols += 1
                  
        #callers
        callers = point.payload.get("calls")
        if callers:

            # How many files have calls?
            file_name = point.payload.get("file_path")
            
            if file_name not in seen_call_files:
                seen_call_files.add(file_name)
                counter_call_files += 1
        
            # What methods are called most?
            for caller in callers:
                method_name = caller["method"]
                counter_methods[method_name] += 1
                total_calls += 1

    #max imported symbol frequency
    for imported_symbol_name, symbol_frequency in counter_symbols.items():
        if symbol_frequency >= max_imported_symbol_frequency:
            max_imported_symbol_frequency = symbol_frequency

    #all imported symbols with equal max frequency
    for imported_symbol_name, symbol_frequency in counter_symbols.items():
        if symbol_frequency == max_imported_symbol_frequency:
            imported_symbols_with_most_frequency.append(imported_symbol_name)

    #max method frequency
    for method_name, method_frequency in counter_methods.items():
        if method_frequency >= max_method_frequency:
            max_method_frequency = method_frequency
    
    #all methods with equal max frequency
    for method_name, method_frequency in counter_methods.items():
        if method_frequency == max_method_frequency:
            methods_with_most_frequency.append(method_name)

    return{
        "files_with_imports": counter_import_files,
        "files_with_calls": counter_call_files,
        "total_import_edges": total_imported_symbols,
        "total_calls_edges": total_calls,
        "top_imported_symbols":{
            "imported_symbols": [imported_symbols for imported_symbols in imported_symbols_with_most_frequency],
            "frequency_imported_symbol": max_imported_symbol_frequency
        }
        ,
        "top_method_called":{
            "methods_called": [methods for methods in methods_with_most_frequency],
            "frequency_method_calls": max_method_frequency,
        }
        
    }


def get_graph_dependencies(limit: int = 1000) -> dict:
    points, _ = client.scroll(
        collection_name= COLLECTION_NAME,
        limit=limit,
        with_payload=True,
        with_vectors=False,
    )
    dependencies = []

    for point in points:
        file_name = point.payload.get("file_path")
        imports = point.payload.get("imports", [])
        if imports: 
            dependencies.append({
                "file_name": file_name,
                "imports": imports,
            })
    
    return{
        "dependencies": dependencies
    }

def get_graph_dependents(query: str) -> dict:
    points, _ = client.scroll(
        collection_name= COLLECTION_NAME,
        limit=1000,
        with_payload=True,
        with_vectors=False,
    )

    dependants = []

    for point in points:
        imports = point.payload.get("imports", [])
        if imports:
            for imported in imports:
                if (query == imported["source"]) or (query in imported["imported_symbols"]):
                    file_name = point.payload.get("file_path")
                    dependants.append({
                        "file_path": file_name,
                        "source": imported["source"],
                        "matched_symbol": query,
                    })

    return{
        "query": query,
        "dependants": dependants,
    }


def get_files_for_calls(query: str) -> dict:
    points, _ = client.scroll(
        collection_name= COLLECTION_NAME,
        limit=1000,
        with_payload=True,
        with_vectors=False,
    )

    callers = []

    for point in points:
        seen = set()
        calls = point.payload.get("calls", [])
        if calls:
            for called_method in calls:
                if (query == called_method["object"]) or (query == called_method["method"]):
                    file_name = point.payload.get("file_path")
                    key = (file_name, called_method["object"], called_method["method"])
                    if key not in seen:
                        callers.append({
                            "file_path": file_name,
                            "object": called_method["object"],
                            "method": called_method["method"],
                            "start_line": point.payload.get("start_line"),
                            "end_line": point.payload.get("end_line"),
                        })
                        seen.add(key)

    return{
        "query": query,
        "callers": callers,
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
            
            # symbol_metadata = extract_symbol_metadata(chunk["content"], file_path.suffix)

            ast_metadata = extract_ast_symbols(file_path, chunk["content"])    #parsing using AST-Retrieval


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
                        "semantic_symbols": [
                            {
                                "symbol_name": symbol["name"],
                                "symbol_type": symbol["type"],
                            }
                            for symbol in ast_metadata["symbols"]
                        ],
                        "imports": [{
                            "source": imported["source"],
                            "imported_symbols": imported["imported_symbols"]
                        }
                        for imported in ast_metadata["imports"]
                        ],
                        "calls": [{
                            "object": called_method["object"],
                            "method": called_method["method"],
                        }
                        for called_method in ast_metadata["calls"]
                        ],
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

