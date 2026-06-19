# AI Engine Module

Module AI gồm phân tích sentiment và trợ lý RAG theo ngữ cảnh thị trường.

## Files
- `sentiment_analyzer.py`: gán nhãn sentiment cho bản tin trong MongoDB.
- `rag_assistant.py`: truy vấn vector DB + sinh câu trả lời tư vấn có nguồn.

## Input/Output
- Input chính: dữ liệu từ Mongo collection `clean_news`.
- Output:
  - Sentiment được ghi vào field `sentiment` trong Mongo.
  - Trả lời RAG theo truy vấn người dùng (CLI hoặc tích hợp UI).

## Run
```bash
python ai_engine/sentiment_analyzer.py
python ai_engine/rag_assistant.py
```

## Lưu ý vận hành
- Bắt buộc có `GROQ_API_KEY` trong `.env`.
- `HF_TOKEN` dùng làm fallback khi provider chính bị rate-limit.
