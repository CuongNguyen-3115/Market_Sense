# 📈 MARKET-SENSE

**Hệ thống AI Assistant: Phân tích Tâm lý Thị trường & Quản trị Rủi ro**

---

## Giới thiệu
MARKET-SENSE là giải pháp tự động hóa luồng tin tức vĩ mô, giúp nhà đầu tư khắc phục "hiệu ứng tê liệt phân tích". Hệ thống sử dụng kiến trúc **Dual-Engine AI** kết hợp giữa Phân tích định lượng (Time-Series Sentiment) và Định tính (RAG Engine) để nhận diện sớm rủi ro và điểm đảo chiều của thị trường.

## Tính năng cốt lõi
* **Sentiment Index:** Số hóa tin tức thành chỉ số tâm lý, kết hợp đường trung bình động (SMA) để xác nhận xu hướng (Uptrend/Downtrend/Sideway).
* **RAG Assistant:** Trợ lý ảo đàm thoại, tự động truy xuất và tóm tắt tin tức kinh tế với độ trễ thấp.
* **Độ tin cậy cao:** Áp dụng framework RAG Triad và cơ chế chuyên gia kiểm duyệt HITL (Human-in-the-Loop) để triệt tiêu Ảo giác AI (Hallucination).

## Giao diện Hệ thống

*(Ảnh Dashboard Tổng quan)*
![Market Sense Dashboard](./docs/dashboard.png)

*(Ảnh Trợ lý AI RAG Assistant)*
![RAG Assistant](./docs/assistant.png)

## Công nghệ sử dụng
* **AI/LLM Core:** Llama-3-8B / Llama-3.3-70B (Groq), Vietnamese-sBERT.
* **Database:** MongoDB (Raw Data), ChromaDB (Vector Database).
* **Backend:** Python (FastAPI, Uvicorn).
* **Frontend:** HTML, CSS, Vanilla JS.

## Hướng dẫn Khởi chạy

### 1. Khởi động Backend
```bash
cd backend
# Kích hoạt môi trường ảo
venv\Scripts\activate 
# Cài đặt thư viện (nếu chưa có)
pip install -r requirements.txt
# Chạy server FastAPI trên cổng 8000
uvicorn main:app --reload --host 0.0.0.0 --port 8000
