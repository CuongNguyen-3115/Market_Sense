# Scrapers Module

Thu thập dữ liệu tin tức tài chính từ nhiều nguồn và đẩy vào Kafka topic raw.

## Files
- `cafef_scraper.py`: crawl tin thị trường từ CafeF.
- `sbv_scraper.py`: crawl tin chính sách vĩ mô từ SBV.

## Output Contract
Mỗi bản tin sau khi scrape sẽ được publish lên Kafka với các trường chính:
- `id`, `source`, `category`, `title`, `summary`, `url`, `published_at`, `scraped_at`

## Run
```bash
python scrapers/sbv_scraper.py
python scrapers/cafef_scraper.py
```

## Lưu ý vận hành
- Cần Kafka broker đang chạy (`localhost:9092` mặc định).
- Có cơ chế sleep giữa các trang để giảm nguy cơ bị chặn IP.
- Chạy lặp lại vẫn an toàn vì downstream consumer upsert theo `id`.
