# from openai import OpenAI
# from app.config import OPENAI_API_KEY, EMBEDDING_MODEL

# client = OpenAI(api_key=OPENAI_API_KEY)

# def embed_text(text: str) -> list[float]:
#     response = client.embeddings.create(
#         model=EMBEDDING_MODEL,
#         input = text,
#     )

#     return response.data[0].embedding

from sentence_transformers import SentenceTransformer

model = SentenceTransformer(
    "sentence-transformers/all-MiniLM-L6-v2"
)
def embed_text(text):
    return model.encode(text).tolist()


#produced 384-dimensional vector