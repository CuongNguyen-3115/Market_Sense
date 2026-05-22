import os
import json
from kafka import KafkaConsumer
from pymongo import MongoClient
from dotenv import load_dotenv

# ==========================================
# 1. CẤU HÌNH HỆ THỐNG
# ==========================================
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

KAFKA_SERVER = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC_NAME = os.getenv("KAFKA_TOPIC_RAW_NEWS", "shb-raw-news")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
MONGO_DB = os.getenv("MONGO_DB_NAME", "shb_sentiment")

# ==========================================
# 2. KẾT NỐI MONGODB (TRẠM LƯU TRỮ)
# ==========================================
try:
    mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = mongo_client[MONGO_DB]
    clean_collection = db["clean_news"]        # Bảng dữ liệu sạch cho AI
    dlq_collection = db["dead_letter_queue"]   # Thùng rác chứa dữ liệu lỗi
    print("✅ Đã kết nối thành công tới Cơ sở dữ liệu MongoDB.")
except Exception as e:
    print(f"❌ LỖI DB: Không thể kết nối MongoDB. Chi tiết: {e}")
    exit(1)

# ==========================================
# 3. KẾT NỐI KAFKA (TRẠM LẮNG NGHE)
# ==========================================
try:
    consumer = KafkaConsumer(
        TOPIC_NAME,
        bootstrap_servers=[KAFKA_SERVER],
        auto_offset_reset='earliest', # Đọc lại từ đầu nếu bị lỡ tin nhắn
        enable_auto_commit=True,
        group_id='shb-sentiment-consumer-group',
        value_deserializer=lambda x: json.loads(x.decode('utf-8'))
    )
    print(f"🎧 Đang lắng nghe luồng dữ liệu từ Kafka Topic: '{TOPIC_NAME}'...")
except Exception as e:
    print(f"❌ LỖI KAFKA: Không thể kết nối Consumer. Chi tiết: {e}")
    exit(1)

# ==========================================
# 4. HỢP ĐỒNG DỮ LIỆU & LƯU TRỮ (DATA CONTRACT)
# ==========================================
def validate_article(article):
    """Kiểm duyệt chất lượng dữ liệu: Phải có Title, Summary và URL."""
    required_keys = ["id", "title", "summary", "url", "published_at"]
    for key in required_keys:
        if key not in article or not article[key]:
            return False
    return True

def start_consuming():
    """Vòng lặp vĩnh cửu lắng nghe và phân luồng dữ liệu"""
    for message in consumer:
        article = message.value
        
        # Bước 1: Kiểm duyệt
        is_valid = validate_article(article)
        
        try:
            # Bước 2: Phân luồng lưu trữ
            if is_valid:
                # Dùng update_one với upsert=True để CHỐNG TRÙNG LẶP DỮ LIỆU
                # Nếu bài báo (dựa vào id) đã có thì bỏ qua/cập nhật, chưa có thì thêm mới.
                clean_collection.update_one(
                    {"id": article["id"]}, 
                    {"$set": article}, 
                    upsert=True
                )
                print(f"🟢 [SẠCH] Đã lưu vào MongoDB: {article['title'][:50]}...")
            else:
                dlq_collection.insert_one(article)
                print(f"🔴 [LỖI SCHEMA] Bỏ vào thùng rác DLQ: {article.get('id', 'Unknown')}")
                
        except Exception as e:
            print(f"⚠️ Lỗi khi ghi vào Database: {e}")

if __name__ == "__main__":
    start_consuming()