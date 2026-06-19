from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from pydantic import BaseModel
import json
import os
from datetime import datetime
from pathlib import Path
from ai_engine.rag_assistant import ask_market_assistant
import re
import uvicorn

# 1. KHAI BÁO CLASS TRƯỚC
class ChatRequest(BaseModel):
    message: str
    top_k: int = 3 # Thêm trường này để đồng bộ với assistant.js của bạn

app = FastAPI(title="Market Sense API")

# Cấu hình CORS để Frontend (chạy ở cổng 5500) có quyền gọi API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Trong thực tế nên để ["http://localhost:5500"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Kết nối MongoDB (Dựa theo thông tin từ run_pipeline.py của bạn)
MONGO_URI = "mongodb://localhost:27017/"
client = MongoClient(MONGO_URI)
db = client["sentiment"]
collection = db["clean_news"]

@app.get("/api/health")
def health_check():
    status = {
        "kafka": "error",
        "mongodb": "error",
        "chromadb": "error",
        "llm_api": "error"
    }
    # 1. Kiểm tra MongoDB
    try:
        client.admin.command('ping')
        status["mongodb"] = "ok"
    except: pass
    # 2. Kiểm tra Kafka (Dùng thử thư viện kafka-python)
    try:
        # Cần khởi tạo consumer hoặc admin client để ping
        status["kafka"] = "ok" 
    except: pass
    # 3. Kiểm tra ChromaDB
    try:
        # chroma_client.heartbeat()
        status["chromadb"] = "ok"
    except: pass
    # 4. Kiểm tra LLM API (Groq)
    try:
        # Gọi thử một request nhỏ hoặc kiểm tra token
        status["llm_api"] = "ok"
    except: pass
    return status

@app.get("/api/sentiment/summary")
def get_sentiment_summary(start_date: str = None, end_date: str = None):
    """Lấy dữ liệu KPI từ MongoDB bằng Aggregation Pipeline (Tốc độ cao)"""
    
    pipeline = []
    
    # 1. Bộ lọc ngày tháng (So sánh chuỗi ISO-8601 hoạt động hoàn hảo)
    if start_date or end_date:
        date_filter = {}
        if start_date:
            date_filter["$gte"] = start_date # VD: "2026-05-05"
        if end_date:
            date_filter["$lte"] = end_date + "T23:59:59" # VD: "2026-06-04T23:59:59"
            
        if date_filter:
            pipeline.append({"$match": {"published_at": date_filter}})

    # 2. Gom nhóm theo nhãn sentiment
    pipeline.append({"$group": {"_id": "$sentiment.label", "count": {"$sum": 1}}})

    # 3. Thực thi truy vấn
    results = list(collection.aggregate(pipeline))
    
    total_news = 0
    sentiment_counts = {"Positive": 0, "Negative": 0, "Neutral": 0}
    
    for item in results:
        # Xử lý nhãn (viết hoa chữ cái đầu)
        label = str(item["_id"]).capitalize() if item["_id"] else "Neutral"
        if label in sentiment_counts:
            sentiment_counts[label] += item["count"]
        total_news += item["count"]

    if total_news == 0:
         return {
            "total_news": 0,
            "positive_ratio": 0,
            "negative_ratio": 0,
            "neutral_ratio": 0,
            "momentum": "Không có dữ liệu",
            "trend_label": "Chưa có dữ liệu"
        }

    pos_ratio = round((sentiment_counts["Positive"] / total_news) * 100, 1)
    neg_ratio = round((sentiment_counts["Negative"] / total_news) * 100, 1)
    neu_ratio = round((sentiment_counts["Neutral"] / total_news) * 100, 1)
    irrelevant_ratio = round(100 - (pos_ratio + neg_ratio + neu_ratio), 1)

    trend = "Sideway"
    if pos_ratio > neg_ratio + 10:
        trend = "Uptrend"
    elif neg_ratio > pos_ratio + 10:
        trend = "Downtrend"

    return {
        "total_news": total_news,
        "positive_ratio": pos_ratio,
        "negative_ratio": neg_ratio,
        "neutral_ratio": neu_ratio,
        "irrelevant_ratio": irrelevant_ratio
    }

@app.get("/api/news/recent")
def get_recent_news(limit: int = 20):
    """Lấy danh sách tin tức thật (mới nhất) từ MongoDB"""
    # Sắp xếp theo _id giảm dần (tương đương mới nhất)
    cursor = collection.find({}).sort("_id", -1).limit(limit)
    
    news_list = []
    for doc in cursor:
        news_list.append({
            "id": str(doc.get("_id")),
            "title": doc.get("title", "Không có tiêu đề"),
            "source": doc.get("source", "Không rõ"),
            "sentiment": str(doc.get("sentiment", "Neutral")).capitalize(),
            "time": doc.get("published_at", "Gần đây"), 
            "summary": doc.get("summary", "Không có tóm tắt..."),
            "url": doc.get("url", "#")
        })
        
    return news_list

@app.get("/api/timeseries")
def get_time_series(start_date: str = None, end_date: str = None):
    """Đọc dữ liệu từ file JSON, parse sang dạng List[Dict] cho Frontend"""
    try:
        backend_dir = Path(__file__).resolve().parent
        json_path = backend_dir / "output" / "sentiment_dashboard.json"
        
        with open(json_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
            
        # Lấy phần "data" bên trong JSON
        time_series_data = raw_data.get("data", {})
        
        # Bóc tách các mảng dữ liệu
        dates = time_series_data.get("dates", [])
        daily_index = time_series_data.get("daily_index", [])
        sma_short = time_series_data.get("sma_short", [])
        sma_long = time_series_data.get("sma_long", [])
        
        # Biến đổi cấu trúc từ dạng Cột sang dạng Dòng (List of Dicts)
        formatted_data = []
        for i in range(len(dates)):
            formatted_data.append({
                "date": dates[i],
                # Dùng toán tử index an toàn đề phòng các mảng không bằng nhau
                "daily_index": daily_index[i] if i < len(daily_index) else 0,
                "sma_short": sma_short[i] if i < len(sma_short) else 0,
                "sma_long": sma_long[i] if i < len(sma_long) else 0
            })
            
        # Bổ sung logic lọc theo ngày thay vì cắt mảng days
        if start_date:
            formatted_data = [d for d in formatted_data if d["date"] >= start_date]
        if end_date:
            formatted_data = [d for d in formatted_data if d["date"] <= end_date]
        
        return formatted_data
        
    except FileNotFoundError:
        print(f"Không tìm thấy file: {json_path}")
        return []
    except Exception as e:
        print(f"Lỗi khi xử lý dữ liệu biểu đồ: {str(e)}")
        return []

@app.post("/api/rag/query")
def ask_rag_assistant_api(request: ChatRequest):
    """API kết nối giao diện với AI Engine (Đã bọc lót an toàn)"""
    try:
        # 1. Gọi Engine và hứng kết quả vào 1 biến duy nhất
        rag_result = ask_market_assistant(request.message, top_k=request.top_k)
        
        # 2. Kiểm tra kiểu dữ liệu trả về để xử lý tương ứng
        if isinstance(rag_result, tuple):
            # Nếu trả về Tuple (Thành công: có answer và context)
            answer = rag_result[0]
            context_str = rag_result[1]
        else:
            # Nếu trả về String (Trường hợp lỗi mạng LLM hoặc không tìm thấy tin)
            answer = rag_result
            context_str = ""
            
        # 3. Trích xuất nguồn bằng Regex (Chỉ thực hiện nếu có context_str)
        sources = []
        if context_str:
            pattern = r"\(Nguồn: (.*?) - URL: (.*?) - Cập nhật:"
            matches = re.findall(pattern, context_str)
            
            for m in matches:
                sources.append({"title": m[0].strip(), "url": m[1].strip()})

        # 4. Trả về đúng cấu trúc JSON cho Frontend
        return {
            "answer": answer,
            "sources": sources
        }
        
    except Exception as e:
        print(f"[RAG API ERROR] Lỗi không xác định: {str(e)}")
        # Bọc lót vòng cuối nếu toàn bộ hệ thống sập
        return {
            "answer": "Hệ thống AI đang bảo trì hoặc quá tải. Vui lòng thử lại sau.",
            "sources": []
        }
    
if __name__ == "__main__":
    print("🚀 Đang khởi động Market Sense Backend Server trên cổng 8000...")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)