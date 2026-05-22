import os
import time
import json
import re
import logging
from datetime import datetime
from pymongo import MongoClient
from dotenv import load_dotenv
from huggingface_hub import InferenceClient
from groq import Groq
import itertools


# Cấu hình log
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = "shb_sentiment"
COLLECTION_NAME = "clean_news"
HF_TOKEN = os.getenv("HF_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    logger.error("Không tìm thấy GROQ_API_KEY trong file .env!")
    exit(1)

# 1. KHỞI TẠO POOL MÔ HÌNH (ROUND-ROBIN)
GROQ_MODELS = [
    "llama-3.1-8b-instant",
    "llama-3.3-70b-versatile",
    "mixtral-8x7b-32768"
]
groq_model_pool = itertools.cycle(GROQ_MODELS)

HF_MODELS = [
    "meta-llama/Meta-Llama-3-8B-Instruct",
    "meta-llama/Meta-Llama-3-70B-Instruct"
]
hf_model_pool = itertools.cycle(HF_MODELS)


def get_mongo_collection():
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    return db[COLLECTION_NAME]

def extract_json_from_text(text):
    """
    Hàm bọc lót: LLM đôi khi trả về JSON bị bọc trong markdown (```json ... 
```)
    hoặc kèm vài câu chào hỏi. Hàm này dùng Regex để moi đúng phần {...} ra.
    """
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        return match.group(0)
    return text

def map_score(label):
    """Ánh xạ nhãn LLM thành điểm số định lượng tuyệt đối"""
    mapping = {
        "positive": 1.0,
        "negative": -1.0,
        "neutral": 0.0,
        "irrelevant": 0.0 # Tin rác sẽ bị lọc bỏ ở phase sau, gán tạm 0
    }
    return mapping.get(label.lower(), 0.0)

def process_sentiment():
    # 1. BẮT ĐẦU ĐO THỜI GIAN CHẠY TỔNG THỂ
    start_time = time.time()

    collection = get_mongo_collection()
    
    query = {"sentiment": {"$exists": False}}
    unprocessed_docs = list(collection.find(query))
    total_docs = len(unprocessed_docs)
    
    logger.info(f"Tìm thấy {total_docs} bài báo cần phân tích bằng AI.")
    if total_docs == 0:
        return

    # Khởi tạo 2 Client song song, set max_retries=0 cho Groq để tự handle lỗi 429 trong code
    groq_client = Groq(api_key=GROQ_API_KEY, max_retries=0)
    
    # Biến trạng thái để kiểm soát Provider
    current_provider = "groq"
    current_groq_model = next(groq_model_pool)
    current_hf_model = next(hf_model_pool)
    
    hf_client = InferenceClient(model=current_hf_model, token=HF_TOKEN)
    
    success_count = 0
    
    # Định nghĩa System Prompt - "Trái tim" của mô hình
    system_prompt = """Bạn là một Chuyên gia phân tích rủi ro tài chính định lượng tại quỹ đầu tư SHB.
Nhiệm vụ của bạn là đọc bản tin và phân tích tâm lý thị trường (Market Sentiment).
CHỈ ĐƯỢC PHÉP trả về một object JSON duy nhất.
Quy tắc gán nhãn (label) cực kỳ nghiêm ngặt:
- "positive": Tin tức mang tính tích cực, thúc đẩy tăng trưởng tài sản, dòng tiền hoặc kinh tế vĩ mô.
- "negative": Tin tức tiêu cực, cảnh báo rủi ro lạm phát, nợ xấu, hoặc suy giảm thị trường.
- "neutral": Tin tức TÀI CHÍNH/VĨ MÔ nhưng đã được dự báo trước, không gây biến động xu hướng.
- "irrelevant": BẤT CỨ tin tức nào thuộc về an ninh trật tự (lừa đảo, công an, tai nạn), đời sống cá nhân, thông báo nội bộ doanh nghiệp nhỏ lẻ không tác động đến thị trường chung.

Cấu trúc JSON bắt buộc:
{
    "label": "positive" | "negative" | "neutral" | "irrelevant",
    "score": <số thập phân 0.0 đến 1.0>,
    "reason": "<Giải thích ngắn gọn dưới 30 từ>"
}"""

    for idx, doc in enumerate(unprocessed_docs):
        # Đo thời gian xử lý từng bài báo
        doc_start_time = time.time()
        
        doc_id = doc['_id']
        combined_text = f"Tiêu đề: {doc['title']}\nTóm tắt: {doc['summary']}"[:1500] 
        
        logger.info(f"[{idx + 1}/{total_docs}] Đang phân tích ID: {doc_id}")
        
        # Thử nhiều lần để có thời gian chuyển đổi Provider và Model
        max_retries = 6 
        for attempt in range(max_retries):
            try:
                # 1. BẮT ĐẦU ĐO GIỜ GỌI API
                api_start_time = time.time()
                sentiment_data = None
                
                if current_provider == "groq":
                    response = groq_client.chat.completions.create(
                        model=current_groq_model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": f"Hãy phân tích bản tin sau:\n{combined_text}"}
                        ],
                        temperature=0.1,
                        max_tokens=150,
                        response_format={"type": "json_object"}
                    )
                    api_latency = time.time() - api_start_time
                    logger.info(f"   [API Latency] Groq ({current_groq_model}) phản hồi trong: {api_latency:.2f} giây")

                    raw_output = response.choices[0].message.content
                    sentiment_data = json.loads(raw_output)
                    model_used = f"groq/{current_groq_model}"
                    
                else:
                    # Chạy trên HuggingFace
                    hf_client.model = current_hf_model
                    messages = [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Hãy phân tích bản tin sau:\n{combined_text}"}
                    ]
                    response = hf_client.chat_completion(
                        messages=messages,
                        max_tokens=150,
                        temperature=0.1,
                    )
                    api_latency = time.time() - api_start_time
                    logger.info(f"   [API Latency] HuggingFace ({current_hf_model}) phản hồi trong: {api_latency:.2f} giây")

                    raw_output = response.choices[0].message.content
                    clean_json_str = extract_json_from_text(raw_output)
                    sentiment_data = json.loads(clean_json_str)
                    model_used = f"hf/{current_hf_model}"

                # Cập nhật kết quả vào MongoDB
                label = sentiment_data.get('label', 'neutral')
                sentiment_data['score'] = map_score(label)
                
                sentiment_data["analyzed_at"] = datetime.utcnow().isoformat() + "Z"
                sentiment_data["model"] = model_used
                
                collection.update_one(
                    {"_id": doc_id},
                    {"$set": {"sentiment": sentiment_data}}
                )
                success_count += 1
                doc_duration = time.time() - doc_start_time
                logger.info(f"-> {label.upper()} ({sentiment_data['score']}) - {sentiment_data.get('reason', '')} (Tốn: {doc_duration:.2f}s)")
                
                break # Thành công thì thoát loop retry
                
            except json.JSONDecodeError:
                logger.error(f"-> Lỗi Parse JSON ({current_provider}). LLM trả về định dạng sai.")
                time.sleep(1)
            except Exception as e:
                error_msg = str(e)
                logger.error(f"-> Thất bại với {current_provider} (Lần {attempt + 1}). Lỗi: {error_msg}")
                
                # CƠ CHẾ XOAY VÒNG VÀ FALLBACK PROVIDER
                if "429" in error_msg or "rate limit" in error_msg.lower() or "too many requests" in error_msg.lower():
                    if current_provider == "groq":
                        logger.warning(f"🔄 Mô hình Groq {current_groq_model} nghẽn! Nghỉ 10s rồi xoay sang mô hình dự phòng...")
                        time.sleep(10)
                        current_groq_model = next(groq_model_pool)
                        
                        # Nếu xoay liên tục 3 lần (cỡ pool) mà vẫn tịt => Hết quota cấp tài khoản Groq!
                        if attempt >= 2:
                            logger.warning("🚨 Groq dường như đã hết quota cấp độ tài khoản! Nhảy sang xoay vòng HuggingFace.")
                            current_provider = "hf"
                            time.sleep(1)
                    else:
                        # Vẫn rate limit bên HF -> tiến hành xoay vòng trên HF
                        logger.warning(f"🔄 Mô hình HF {current_hf_model} nghẽn! Nghỉ 10s rồi xoay sang mô hình dự phòng...")
                        time.sleep(10)
                        current_hf_model = next(hf_model_pool)
                elif "loading" in error_msg.lower():
                    logger.warning("Mô hình đang khởi động. Đợi 10 giây...")
                    time.sleep(10)
                else:
                    time.sleep(1)
        
        # Nhịp nghỉ 1 giây sau mỗi bài báo (Tránh spam API)
        time.sleep(2)

    # 2. TỔNG KẾT HIỆU SUẤT
    total_duration = time.time() - start_time
    minutes = int(total_duration // 60)
    seconds = int(total_duration % 60)
    
    logger.info("="*50)
    logger.info(f"KẾT THÚC CẤU PHẦN AI MODELING!")
    logger.info(f"Tổng số bài phân tích thành công: {success_count}/{total_docs}")
    logger.info(f"Tổng thời gian chạy: {minutes} phút {seconds} giây.")
    if success_count > 0:
        logger.info(f"Tốc độ trung bình: {total_duration/success_count:.2f} giây/bài báo.")
    logger.info("="*50)

if __name__ == "__main__":
    process_sentiment()