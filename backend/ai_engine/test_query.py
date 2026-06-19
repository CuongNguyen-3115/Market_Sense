# test_query.py
import chromadb
from chromadb.utils import embedding_functions
import os

CHROMA_DB_DIR = r"C:\1. Project\2_Cuộc_thi\2026\3. HACK CX TOGETHER 2026\market_sense\backend\chroma_data"
client = chromadb.PersistentClient(path=CHROMA_DB_DIR)
emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="keepitreal/vietnamese-sbert")

collection = client.get_collection(name="market_knowledge", embedding_function=emb_fn)

# Thử query 1 câu hỏi thực tế
results = collection.query(
    query_texts=["rủi ro kinh tế số"],
    n_results=2
)
print(f"Kết quả tìm kiếm: {results['documents']}")