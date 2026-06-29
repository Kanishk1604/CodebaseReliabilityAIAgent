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
        calls = result.payload.get("calls", [])

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
            "calls": calls,
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

def is_noisy_call(call: dict) -> bool:

    object_name = (call.get("object") or "").lower()
    method_name = (call.get("method") or "").lower()

    noisy_objects = {"console", "logger"}
    noisy_methods = {"log", "debug", "info", "warn", "error"}

    return object_name in noisy_objects or method_name in noisy_methods

def is_test_file(chunk:dict) -> bool:
    file_path = (chunk.get("file_path") or "").lower()
    file_name = (chunk.get("file_name") or "").lower()

    return (
        ".spec." in file_name
        or ".test." in file_name
        or "/test/" in file_path
        or "/tests/" in file_path
    )
      
def build_relationships(chunks: dict) -> str:
    
    relationships = []
    seen = set()

    for chunk in chunks[:5]:
        if is_test_file(chunk):
            continue
        file_name = chunk["file_name"]
        
        for imported in chunk.get("imports", []):
            source = imported.get("source", "")
            for symbol in imported.get("imported_symbol", []):
                relationship = f"{file_name} imports {symbol} from {source}"

                if relationship not in seen:
                    seen.add(relationship)
                    relationships.append(relationship)
            
        for call in chunk.get("calls", []):
            if is_noisy_call(call):
                continue

            object_name = call.get("object") or ""
            method_name = call.get("method") or ""

            relationship = f"{file_name} calls {object_name}.{method_name}"

            if relationship not in seen:
                seen.add(relationship)
                relationships.append(relationship)

    if not relationships:
        return "RELATIONSHIPS:\n none\n"

    return "RELATIONSHIPS:\n" + "\n".join(
        f"- {relationship}" for relationship in relationships
    ) + "\n"


def build_reasoning_context(question: str, chunks: dict) -> str:
    reasoning_context = ""
    reasoning_context += f"QUESTION:\n{question}\n\n"
    reasoning_context += "RETRIEVED FILES:\n"

    for chunk in chunks[:5]:
        if chunk["extension"] == ".md":
            continue
        reasoning_context += f"{chunk['file_name']} {chunk['start_line']}-{chunk['end_line']}\n"
        symbol_count = 1
        import_count = 1
        calls_count = 1
        
        semantic_symbols = chunk["semantic_symbols"]
        reasoning_context += "Symbols: "
        if semantic_symbols:
            for semantic_symbol in semantic_symbols:
                reasoning_context += f"{semantic_symbol['symbol_name']}"
                if symbol_count >= len(semantic_symbols):
                    reasoning_context += "\n"
                else:
                    reasoning_context += ", "
                symbol_count += 1
        else:
            reasoning_context += "none\n"

        imported_symbols = chunk["imports"]
        reasoning_context += "Imports: "
        if imported_symbols:
            for imported_symbol in imported_symbols:
                imported_symboles_list = imported_symbol["imported_symbols"] 
                imported_symboles_source = imported_symbol["source"]
                imported_symboles_str = ", ".join(imported_symboles_list)

                reasoning_context += f"{imported_symboles_str} from {imported_symboles_source}"
                if import_count >= len(imported_symbols):
                    reasoning_context += "\n"
                else:
                    reasoning_context += ", "
                import_count += 1
        else:
            reasoning_context += "none\n"
        
        calls = chunk["calls"]
        reasoning_context += "Calls: "
        if calls:
            for called in calls:
                reasoning_context += f"{called['object']}.{called['method']}"
                if calls_count >= len(calls):
                    reasoning_context += "\n"
                else:
                    reasoning_context += ", "
                calls_count += 1
        else:
            reasoning_context += "none\n"
        
        reasoning_context += "\n"

    reasoning_context += build_relationships(chunks)


    return reasoning_context

#RAG function -> Retrieval-Augmented Generation => Search first, then answer using what you found
def answer_question(question: str, reasoning_context: str) -> dict:
    chunks = search_codebase(question)
    context = ""
    answer_chunks = [
        chunk for chunk in chunks
        if not is_test_file(chunk)
    ]
    context = "\n\n".join(
        f"FILE: {chunk['file_path']}\n"
        f"CHUNK: {chunk['chunk_index']}\n"
        f"CODE: \n{chunk['content']}"
        for chunk in answer_chunks
    )

    prompt = f"""
    You are a senior software engineer helping understand a codebase.

    Answer the user's question using only the provided repository context and structured evidence.
    
    When the evidence clearly identifies multiple cooperating files, explain them as a flow instead of saying the answer is unclear.

    Be precise about request direction. Interceptors attach headers to outgoing HTTP requests, not responses.

    When explaining a flow, order steps by runtime or dependency sequence using the retrieved calls, imports, and file relationships.
    
   Do not claim something is missing if a relevant symbol, file, or call appears in the structured evidence. If unsure, say "the retrieved context does not show the full implementation details."
   
   Before saying something is absent, check the Symbols, Imports, Calls, and Code sections.
   
   If the answer is not present in the context, say that the indexed context is insufficient.

    Repository context:

    {context}

    Structured evidence:

    {reasoning_context}

    User question:

    {question}

    """

    response = chat(
        model="llama3.2",
        messages =[
            {
                "role": "system",
                "content": "You explain code accurately using only the retrieved repository context. Cite file paths and line ranges when relevant."
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
    )

    validation = validate_answer(response["message"]["content"], chunks)


    return {
        "answer": response["message"]["content"],
        "validation": validation,
        "sources": [
            {
                "file_path": chunk["file_path"],
                "lines": f"{chunk['start_line']}-{chunk['end_line']}",
                "chunk_index": chunk["chunk_index"],
                "score": chunk["score"],
                "adjusted_score": chunk["adjusted_score"],
                "symbols": format_symbols(chunk),
            }
            for chunk in answer_chunks
        ],
    }

def validate_answer(answer: str, chunks: list[dict]) -> dict:
    warnings = []

    answer_lower = answer.lower()

    risky_phrases = [
        "not shown",
        "no explicit",
        "does not show",
        "missing",
        "not present",
        "not found",
    ]

    symbols = []
    for chunk in chunks:
        for symbol in chunk.get("semantic_symbols", []):
            symbol_name = symbol.get("symbol_name")
            if symbol_name:
                symbols.append(symbol_name.lower())

    for phrase in risky_phrases:
        if phrase in answer_lower:
            warnings.append({
                "type": "possible_unsupported_absence_claim",
                "phrase": phrase,
                "message": "The answer claims something may be absent. Check retrieved symbols before trusting this claim.",
                "retrieved_symbols": symbols,
            })

    return {
        "is_valid": len(warnings) == 0,
        "warnings": warnings,
    }