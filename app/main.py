from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.indexer import index_repository,  get_indexed_summary, get_extension_summary, get_file_inventory, reset_index, get_graph_dependencies, get_files_for_symbols
from app.retriever import answer_question, search_codebase

app = FastAPI(title = "AI Codebase Agent")

#BaseModel -> class that serves as foundation for defining request bodies, data validation, type conversion, and automated API docuemntation
class IndexRequest(BaseModel):
    repo_path: str

class AskRequest(BaseModel):
    question: str


@app.get("/")
def health_check():
    return {"status": "ok"}


#indexes local repo into Qdrant
@app.post("/index")
def index_repo(request: IndexRequest):
    try:
        return index_repository(request.repo_path)
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


#answer questions using retireved code context
@app.post("/ask")
def ask_question(request: AskRequest):
    try: 
        return answer_question(request.question)
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


#shows raw retrieval results without LLM
@app.post("/search")
def get_searched_database(request: AskRequest):
    try:
        chunks = search_codebase(request.question,limit=10)

        return {
            "question": request.question,
            "results":[{
                "file_path": chunk["file_path"],
                "file_name": chunk["file_name"],
                "extension": chunk["extension"],
                "chunk_index": chunk["chunk_index"],
                "start_line": chunk["start_line"],
                "end_line": chunk["end_line"],
                "score": chunk["score"],
                "symbol_matches": chunk["symbol_matches"],
                "adjusted_score": chunk["adjusted_score"],
                "semantic_symbols": chunk["semantic_symbols"],
                "imports": chunk["imports"],
                "preview": chunk["content"][:300],
            }
            for chunk in chunks
            ],
        }

    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))

#shows collection/vector info
@app.get("/summary")
def summary():
    try:
        return get_indexed_summary()
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


#shows what file types got indexed
@app.get("/summary/extensions")
def summary_extensions():
    try:
        return get_extension_summary()
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


#shows indexed files and their chunk counts
@app.get("/summary/inventory")
def summary_inventory():
    try:
        return get_file_inventory()
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error)) 

#removing a codebase
@app.delete("/index")
def delete_index():
    try:
        return reset_index()
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error)) 


@app.get("/graph/dependencies")
def get_dependencies():
    try:
        return get_graph_dependencies()
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error)) 


@app.get("/graph/dependents/{query}")
def get_dependents(query: str):
    try:
        return get_files_for_symbols(query)
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error)) 
