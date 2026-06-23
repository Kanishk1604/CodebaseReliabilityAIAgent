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

def keyword_boost(question: str, chunk: dict) -> float:
    text = f"{chunk['file_path']} {chunk['content']}".lower()
    terms = question.lower().replace("?","").split()

    boost = 1.0

    for term in terms:
        if term in text:
            boost += 0.08
    
    important_terms = ["auth", "authentication", "login", "jwt", "token", "interceptor"]

    for term in important_terms:
        if term in question.lower() and term in text:
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

        chunk = {
            "score" : result.score,
            "file_path" : result.payload["file_path"],
            "file_name": result.payload.get("file_name"),
            "extension": result.payload.get("extension"),
            "chunk_index": result.payload["chunk_index"],
            "content": result.payload["content"],
        }
        adjusted_boost = keyword_boost(question, chunk)
        adjusted_score = result.score * boost * adjusted_boost

        chunk["adjusted_score"] = adjusted_score
        chunks.append(chunk)

    chunks.sort(key=lambda chunk: chunk["adjusted_score"], reverse=True)

    return chunks[:limit]
    


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
                "chunk_index": chunk["chunk_index"],
                "score": chunk["score"],
                "adjusted_score": chunk["adjusted_score"],
            }
            for chunk in chunks
        ],
    }

