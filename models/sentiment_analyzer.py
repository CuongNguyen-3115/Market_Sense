import os
import time
import logging
from datetime import datetime
from pymongo import MongoClient
from dotenv import load_dotenv
from huggingface_hub import InferenceClient

# Cấu hình log tracking
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

# Cấu hình Database
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = "shb_sentiment"
COLLECTION_NAME = "clean_news"
HF_TOKEN = os.getenv("HF_TOKEN")

def get_mongo_collection():
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    return db[COLLECTION_NAME]

def process_sentiment():
    collection = get_mongo_collection()
    
    # Chiến lược lũy đẳng: Chỉ lấy các bài báo chưa được chấm điểm tâm lý
    query = {"sentiment": {"$exists": False}}
    unprocessed_docs = list(collection.find(query))
    
    total_docs = len(unprocessed_docs)
    logger.info(f"Tìm thấy {total_docs} bài báo cần phân tích tâm lý.")
    
    if total_docs == 0:
        logger.info("Tất cả dữ liệu hiện tại đã được chấm điểm.")
        return

    # Khởi tạo Client chính thức
    client = InferenceClient(model="ProsusAI/finbert", token=HF_TOKEN)
    success_count = 0
    
    for idx, doc in enumerate(unprocessed_docs):
        doc_id = doc['_id']
        
        # Tiền xử lý: Kết hợp title & summary, đồng thời CẮT NGẮN để tránh lỗi tràn bộ nhớ (Max 512 tokens của FinBERT)
        # 1500 ký tự tương đương khoảng 300-400 tokens, là ngưỡng cực kỳ an toàn
        combined_text = f"{doc['title']}. {doc['summary']}"[:1500] 
        
        logger.info(f"[{idx + 1}/{total_docs}] Đang xử lý bài báo ID: {doc_id}")
        
        try:
            # SỬ DỤNG HÀM CHUYÊN DỤNG THAY VÌ .post()
            # Hàm text_classification tự động gọi API, parse kết quả và trả về list các nhãn
            results = client.text_classification(combined_text)
            
            if results:
                # Hàm linh hoạt để đọc dữ liệu bất kể SDK trả về dạng Dictionary hay dạng Object
                def get_attr(item, key):
                    return item[key] if isinstance(item, dict) else getattr(item, key)

                # Tìm nhãn có độ tự tin (score) cao nhất
                best_prediction = max(results, key=lambda x: get_attr(x, 'score'))
                
                sentiment_data = {
                    "label": get_attr(best_prediction, 'label'),          # positive, negative, neutral
                    "score": round(get_attr(best_prediction, 'score'), 4),
                    "analyzed_at": datetime.utcnow().isoformat() + "Z"
                }
                
                # Ghi đè có chọn lọc vào MongoDB
                collection.update_one(
                    {"_id": doc_id},
                    {"$set": {"sentiment": sentiment_data}}
                )
                success_count += 1
                logger.info(f"-> Kết quả: {sentiment_data['label'].upper()} ({sentiment_data['score']})")
            else:
                logger.error("-> API trả về rỗng.")
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"-> Thất bại tại bài báo ID {doc_id}. Chi tiết lỗi: {error_msg}")
            
            # Xử lý Cold Start: Nếu máy chủ HF đang nạp mô hình, tự động đợi 10s
            if "loading" in error_msg.lower():
                logger.warning("Mô hình đang khởi động trên máy chủ HF. Đợi 10 giây...")
                time.sleep(10)
            else:
                time.sleep(2)
            
        # Giữ khoảng nghỉ nhỏ chống overload rate limit hệ thống
        time.sleep(0.5)

    logger.info(f"Hoàn thành cấu phần AI! Đã phân tích thành công {success_count}/{total_docs} bài báo.")

if __name__ == "__main__":
    process_sentiment()