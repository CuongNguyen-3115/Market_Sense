# Database Module

Module đồng bộ dữ liệu đã qua AI sentiment từ MongoDB sang ChromaDB.

## Files
- `vector_store.py`: tạo embedding và upsert vào collection vector.

## Luồng xử lý
1. Lấy tin đã có sentiment và không phải `irrelevant`.
2. Tạo `rich_text` từ title + summary + reason.
3. Upsert theo batch vào Chroma collection `market_knowledge`.

## Run
```bash
python database/vector_store.py
```

## Lưu ý vận hành
- Lần đầu sẽ tải model embedding `keepitreal/vietnamese-sbert`.
- Dữ liệu Chroma local lưu trong thư mục `chroma_data/`.
