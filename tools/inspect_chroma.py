import chromadb
import os

CHROMA_DB_DIR = os.path.join(os.path.dirname(__file__), 'chroma_data')
client = chromadb.PersistentClient(path=CHROMA_DB_DIR)
collection = client.get_collection(name="shb_market_knowledge")

# Lấy 5 bản ghi đầu tiên
results = collection.peek(limit=5) 

print("--- DỮ LIỆU TRONG CHROMADB ---")
for i in range(len(results['ids'])):
    print(f"ID: {results['ids'][i]}")
    print(f"Metadata: {results['metadatas'][i]}")
    print(f"Content: {results['documents'][i][:500]}...") # In 100 ký tự đầu
    print("-" * 30)