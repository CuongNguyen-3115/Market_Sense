# Sử dụng mô hình keepitreal/vietnamese-sbert

import os
import logging
from pymongo import MongoClient
import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv

# Cấu hình Log
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

# 1. Cấu hình MongoDB
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = "sentiment"
COLLECTION_NAME = "clean_news"

# 2. Cấu hình ChromaDB (Lưu trữ Vector trên ổ cứng local)
# Dữ liệu sẽ được lưu vào thư mục 'chroma_data' ngay trong dự án của bạn
CHROMA_DB_DIR = os.path.join(os.path.dirname(__file__), '..', 'chroma_data')
chroma_client = chromadb.PersistentClient(path=CHROMA_DB_DIR)

# Sử dụng mô hình SBERT tiếng Việt để nhúng (Embedding)
# Lần đầu chạy sẽ mất khoảng 1-2 phút để tải weights của mô hình về máy
emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="keepitreal/vietnamese-sbert")

# Tạo hoặc lấy Collection trong ChromaDB
vector_collection = chroma_client.get_or_create_collection(
    name="market_knowledge",
    embedding_function=emb_fn
)

def get_mongo_collection():
    client = MongoClient(MONGO_URI)
    return client[DB_NAME][COLLECTION_NAME]

def sync_mongo_to_chroma():
    mongo_col = get_mongo_collection()
    
    # CHIẾN LƯỢC LỌC DỮ LIỆU SẠCH: 
    # Chỉ lấy các bài đã có sentiment VÀ KHÔNG PHẢI là tin rác (irrelevant)
    query = {
        "sentiment": {"$exists": True},
        "sentiment.label": {"$ne": "irrelevant"}
    }
    
    docs = list(mongo_col.find(query))
    total_docs = len(docs)
    logger.info(f"Tìm thấy {total_docs} bài báo HỢP LỆ từ MongoDB để nạp vào Vector DB.")
    
    if total_docs == 0:
        logger.warning("Không có dữ liệu hợp lệ. Hãy đảm bảo bạn đã chạy file llama_sentiment.py")
        return

    # Chuẩn bị cấu trúc dữ liệu cho ChromaDB (Dạng List)
    ids = []
    documents = []
    metadatas = []
    
    logger.info("Đang tiến hành chuẩn bị Vector và Metadata...")
    
    for doc in docs:
        doc_id = str(doc["_id"]) # Dùng ID của Mongo làm ID của Chroma
        
        # 1. TẠO DOCUMENT TEXT (Thứ sẽ được chuyển thành Vector Toán học)
        # Gộp cả Tiêu đề, Tóm tắt VÀ Lý do của AI để Vector mang ý nghĩa sâu nhất
        rich_text = f"Tiêu đề: {doc['title']}. Nội dung: {doc['summary']}. Đánh giá: {doc['sentiment'].get('reason', '')}"
        
        # 2. TẠO METADATA (Dùng để filter (Lọc) sau này khi Query)
        # Lưu ý: ChromaDB chỉ nhận giá trị string, int, float trong dict metadata
        metadata = {
            "source": doc["source"],
            "url": doc["url"],
            "label": doc["sentiment"]["label"],
            "score": float(doc["sentiment"]["score"]),
            "published_at": doc["published_at"]
        }
        
        ids.append(doc_id)
        documents.append(rich_text)
        metadatas.append(metadata)

    # Nạp (Upsert) dữ liệu vào ChromaDB theo từng Batch (Tránh tràn RAM)
    batch_size = 50
    logger.info(f"Bắt đầu nạp Vector vào ChromaDB. Model Embedding đang chạy (có thể mất 1-2 phút)...")
    
    for i in range(0, len(ids), batch_size):
        end_idx = i + batch_size
        vector_collection.upsert(
            ids=ids[i:end_idx],
            documents=documents[i:end_idx],
            metadatas=metadatas[i:end_idx]
        )
        logger.info(f" -> Đã nạp thành công batch {i} đến {min(end_idx, len(ids))}")

    logger.info("✅ HOÀN THÀNH CHECKPOINT 3.2! Cơ sở tri thức (Knowledge Base) đã sẵn sàng cho luồng RAG.")

if __name__ == "__main__":
    sync_mongo_to_chroma()