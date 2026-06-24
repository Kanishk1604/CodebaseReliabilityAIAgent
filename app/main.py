from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.indexer import index_repository,  get_indexed_summary, get_extension_summary, get_file_inventory
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

@app.post("/index")
def index_repo(request: IndexRequest):
    try:
        return index_repository(request.repo_path)
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


@app.post("/ask")
def ask_question(request: AskRequest):
    try: 
        return answer_question(request.question)
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))

@app.post("/search")
def get_searched_database(request: AskRequest):
    try:
        return {
            "question": request.question,
            "results": search_codebase(request.question,limit=10)
        }
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))

@app.get("/summary")
def sumamry():
    try:
        return get_indexed_summary()
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))

@app.get("/summary/extensions")
def sumamry():
    try:
        return get_extension_summary()
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))



@app.get("/summary/inventory")
def sumamry():
    try:
        return get_file_inventory()
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))