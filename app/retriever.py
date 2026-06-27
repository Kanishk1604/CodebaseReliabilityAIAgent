# from openai import OpenAI
from ollama import chat
from qdrant_client import QdrantClient

from app.config import(
    OPENAI_API_KEY,
    QDRANT_URL,
    COLLECTION_NAME,
    CHAT_MODEL,
)
from app.embeddings import embed_text

qdrant = QdrantClient(url=QDRANT_URL)
# openai_client= OpenAI(api_key=OPENAI_API_KEY)

SOURCE_BOOSTS = {
    ".ts": 1.25,
    ".tsx": 1.25,
    ".js": 1.2,
    ".jsx": 1.2,
    ".cs": 1.25,
    ".py": 1.25,
    ".java": 1.25,
    ".md": 0.75,
    ".json": 0.5,
}

def is_code_question(question: str) -> bool:
    terms = question.lower().replace("?","").split()

    code_question_terms = {"where", "implemented", "defined", "class", "method", "function", "service", "component", "interceptor"}

    for term in terms:
        if term in code_question_terms:
            return True

    return False

def keyword_boost(question: str, chunk: dict, symbol_matches: list[str]) -> float:
    text = f"{chunk['file_path']} {chunk['content']}".lower()
    terms = question.lower().replace("?","").split()
    boost = 1.0

    for symbol in chunk.get("semantic_symbols", []):
        symbol_name = symbol.get("symbol_name") or ""
        symbol_type = symbol.get("symbol_type") or ""

        # symbol_text = f"{symbol_name} {symbol_type}".lower()
        
        for term in terms:
            if term == symbol_name.lower():
                symbol_matches.append(symbol_name)
                boost += 0.8
            elif term in symbol_name.lower():
                symbol_matches.append(symbol_name)
                boost += 0.4
            
            if term == symbol_type.lower():
                symbol_matches.append(symbol_type)
                boost += 0.15

    for term in terms:
        if term in text:
            boost += 0.08
    
    important_terms = ["auth", "authentication", "login", "jwt", "token", "interceptor"]

    for term in important_terms:
        if term in terms and term in text:      #question.lower()
            boost += 0.15
    
    return boost



def search_codebase(question: str, limit: int=5) -> list[dict]:
    query_vector = embed_text(question)

    results = qdrant.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        limit=limit * 3,
    ).points
    
    chunks =[]


    #sorts in 
    for result in results:
        extension = result.payload.get("extension")

        boost = SOURCE_BOOSTS.get(extension, 1.0)

        semantic_symbols = result.payload.get("semantic_symbols", [])
        imports = result.payload.get("imports", [])

        chunk = {
            "score" : result.score,
            "file_path" : result.payload["file_path"],
            "file_name": result.payload.get("file_name"),
            "extension": result.payload.get("extension"),
            "chunk_index": result.payload["chunk_index"],
            "start_line": result.payload["start_line"],
            "end_line": result.payload["end_line"],
            "content": result.payload["content"],
            "semantic_symbols": semantic_symbols,
            "imports": imports,
        }
        symbol_matches = []
        adjusted_boost = keyword_boost(question, chunk, symbol_matches)
        
        #if file is readme.md
        if chunk["extension"] == ".md" and is_code_question(question):
            boost *= 0.4

        adjusted_score = result.score * boost * adjusted_boost

        chunk["adjusted_score"] = adjusted_score
        chunk["symbol_matches"] = symbol_matches

        chunks.append(chunk)

    chunks.sort(key=lambda chunk: chunk["adjusted_score"], reverse=True)

    return chunks[:limit]
    
def format_symbols(chunk: dict)-> str:
    return ", ".join(f"{symbol.get("symbol_name") or ""} {symbol.get("symbol_type") or ""}".strip()
        for symbol in chunk.get("semantic_symbols",[])
    )

#RAG function -> Retrieval-Augmented Generation => Search first, then answer using what you found
def answer_question(question: str) -> dict:
    chunks = search_codebase(question)

    context = "/n/n".join(
        f"FILE: {chunk['file_path']}\n"
        f"CHUNK: {chunk['chunk_index']}\n"
        f"CODE: \n{chunk['content']}"
        for chunk in chunks
    )

    prompt = f"""
    You are a senior software engineer helping understand a codebase.

    Answer the user's question using only the provided repository context.

    If the answer is not present in the context, say that the indexed context is insufficient.

    Repository context:

    {context}

    User question:

    {question}

    """

    response = chat(
        model="llama3.2",
        messages =[
            {
                "role": "system",
                "content": "You explain code accurately and cite file paths from the retrieved"
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
    )

    return {
        "answer": response["message"]["content"],
        "sources": [
            {
                "file_path": chunk["file_path"],
                "lines": f"{chunk['start_line']}-{chunk['end_line']}",
                "chunk_index": chunk["chunk_index"],
                "score": chunk["score"],
                "adjusted_score": chunk["adjusted_score"],
                "symbols": format_symbols(chunk),
            }
            for chunk in chunks
        ],
    }

