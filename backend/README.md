# Market Sense - AI Pipeline for Financial Sentiment Intelligence

Market Sense là hệ thống phân tích tâm lý thị trường tài chính theo kiến trúc pipeline:

`Scraper -> Kafka -> MongoDB -> AI Sentiment -> Vector DB (Chroma) -> RAG Assistant + Evaluation + Time-series Dashboard`

Mục tiêu dự án:
- Thu thập dữ liệu tin tức tài chính từ nhiều nguồn.
- Phân tích sentiment bằng LLM theo ngữ cảnh tài chính.
- Xây dựng kho tri thức vector để phục vụ RAG.
- Đánh giá chất lượng RAG bằng LLM-as-a-Judge.
- Xuất chỉ số time-series để hiển thị dashboard/BI.

---

## 1) Tech Stack chính

- **Language:** Python
- **Streaming:** Kafka (`kafka-python-ng`)
- **Storage:** MongoDB (`pymongo`)
- **AI/LLM:** Groq API, HuggingFace Inference
- **Vector DB:** ChromaDB + SentenceTransformer embeddings
- **Data processing:** Pandas, NumPy
- **Scraping:** Requests + BeautifulSoup
- **Container infra:** Docker Compose (Kafka, Zookeeper, MongoDB, mongo-express)

---

## 2) Cấu trúc thư mục

```text
market_sense/
├── ai_engine/          # Sentiment analyzer + RAG assistant
├── database/           # Sync Mongo -> ChromaDB
├── evaluation/         # LLM-as-a-Judge + báo cáo benchmark
├── pipeline/           # Kafka consumer + data contract gate
├── scrapers/           # Thu thập dữ liệu từ CafeF / SBV
├── time_series/        # Chỉ số sentiment + trend analytics
├── tests/              # Script test API/model connectivity
├── output/             # Dashboard export (JSON)
├── docker-compose.yml  # Hạ tầng local
├── requirements.txt
└── .env.example
```

---

## 3) Data Pipeline chi tiết
**Tổng quan**: 

- Online ingestion & enrichment (scrape → Kafka → Mongo → sentiment → embed → Chroma) là “nạp dữ liệu nền”.

- Online serving (user query → retrieve Chroma → LLM generate answer) là “phục vụ truy vấn”.

**Cụ thể**:
1. **Ingestion**
   - `scrapers/cafef_scraper.py`
   - `scrapers/sbv_scraper.py`
   - Thu thập và publish bản tin vào Kafka topic `raw_news`.

2. **Data Contract + Storage**
   - `pipeline/kafka_consumer.py`
   - Validate schema (id/title/summary/url/published_at), ghi dữ liệu sạch vào Mongo `clean_news`, lỗi vào `dead_letter_queue`.

3. **AI Sentiment**
   - `ai_engine/sentiment_analyzer.py`
   - Phân tích sentiment cho bản tin chưa xử lý bằng Groq/HF (fallback + retry).

4. **Vectorization**
   - `database/vector_store.py`
   - Embed và upsert dữ liệu hợp lệ vào Chroma collection `market_knowledge`.

5. **RAG Assistant**
   - `ai_engine/rag_assistant.py`
   - Retrieval từ Chroma + generation từ Groq để trả lời theo ngữ cảnh.

6. **Evaluation**
   - `evaluation/run_evaluation.py`
   - Chạy benchmark dựa trên `evaluation/ground_truth.json`, xuất CSV vào `evaluation/eval_results/`.

7. **Time-Series Export**
   - `time_series/pipeline.py`
   - Tính chỉ số daily sentiment + trend labels, export JSON ở `output/sentiment_dashboard.json`.

---

## 4) Yêu cầu môi trường

- Python 3.10+
- Docker Desktop (hoặc Docker Engine + Compose)
- Internet access cho:
  - Crawl data sources
  - Groq API / HuggingFace inference
  - Download embedding model lần đầu

---

## 5) Cài đặt nhanh

### Bước 1: Clone và cài thư viện Python

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### Bước 2: Tạo file môi trường

```bash
copy .env.example .env
```

Điền các biến cần thiết trong `.env`:
- `GROQ_API_KEY` (bắt buộc cho sentiment + RAG + evaluator)
- `HF_TOKEN` (khuyến nghị, dùng fallback)
- `MONGO_URI`, `MONGO_DB_NAME`
- `KAFKA_BOOTSTRAP_SERVERS`, `KAFKA_TOPIC_RAW_NEWS`

### Bước 3: Khởi động hạ tầng

```bash
docker compose up -d
```

Kiểm tra nhanh:
- Kafka: `localhost:9092`
- MongoDB: `localhost:27017`
- mongo-express: `http://localhost:8081`

---

## 6) Cách chạy end-to-end

- **Ingest dữ liệu**

```bash
python scrapers/sbv_scraper.py
python scrapers/cafef_scraper.py
```

- **Consumer dữ liệu từ Kafka vào Mongo**

```bash
python pipeline/kafka_consumer.py
```

- **Chạy sentiment analysis**

```bash
python ai_engine/sentiment_analyzer.py
```

- **Đồng bộ Mongo sang Chroma (vector DB)**

```bash
python database/vector_store.py
```

- **Test trợ lý RAG (CLI)**

```bash
python ai_engine/rag_assistant.py
```

- **Chạy đánh giá RAG**

```bash
python evaluation/run_evaluation.py
```

- **Xuất dữ liệu time-series cho dashboard**

Luồng chính để xuất time-series nằm trong module `time_series/pipeline.py` (không phải notebook test). Chạy bằng cách gọi trực tiếp class `TimeSeriesPipeline`:

```python
from time_series.pipeline import TimeSeriesPipeline

pipeline = TimeSeriesPipeline(
    mongo_uri="mongodb://localhost:27017/",
    db_name="sentiment",
    collection_name="clean_news"
)
pipeline.run_and_export(days_back=30, export_path="output/sentiment_dashboard.json")
```

### 6.8 One-click pipeline

Chạy toàn bộ pipeline bằng 1 lệnh:

```bash
python scripts/run_pipeline.py
```

Một số tùy chọn thường dùng:

```bash
python scripts/run_pipeline.py --skip-eval
python scripts/run_pipeline.py --skip-docker --consumer-drain-seconds 30
```

Nếu môi trường có `make`, bạn cũng có thể dùng:

```bash
make run-all
make run-fast
```

---

## 7) Quy ước push GitHub (chuẩn team/enterprise)

### Nên push
- Source code (`ai_engine`, `pipeline`, `scrapers`, `database`, `time_series`, `evaluation`, `tests`)
- `docker-compose.yml`
- `requirements.txt`
- `README.md`, docs
- `.env.example`

### Không nên push
- Secrets (`.env`, API keys)
- Runtime artifacts (`chroma_data`, `output/*.json`, `evaluation/eval_results/*.csv`, logs)
- Python/cache/editor files (`__pycache__`, `.venv`, `.idea`, `.vscode`, checkpoints)

> Các mục này đã được đưa vào `.gitignore`.

---

## 8) Docker và `requirements.txt`: push gì, quản lý dependencies thế nào?

- Với cấu trúc hiện tại (compose cho infra, app chạy local Python), **bắt buộc push `docker-compose.yml`**.
- Chưa có `Dockerfile` cho app Python. Nếu muốn chạy app hoàn toàn bằng container trên CI/CD, nên thêm `Dockerfile` + `compose` service cho app sau.
- **Có, nên khai báo đầy đủ thư viện ứng dụng trong `requirements.txt`** để môi trường tái lập ổn định.
- Luồng khuyến nghị:
  1. Dùng file phụ thuộc nguồn (`requirements.in` hoặc `pyproject.toml`) cho thư viện top-level.
  2. Lock file (ví dụ `requirements.txt`) cho deploy/CI.
  3. Định kỳ cập nhật dependency theo chu kỳ.

---

## 9) Hướng dẫn thêm ảnh vào README

Bạn nên chụp 4 nhóm ảnh sau để README trực quan và thuyết phục:

1. **Architecture Diagram**
   - Ảnh luồng tổng thể từ scraper đến dashboard/RAG.
   - Đặt ở phần đầu README (sau phần giới thiệu).

2. **Pipeline Runtime**
   - Ảnh terminal khi chạy `scrapers`, `kafka_consumer`, `sentiment_analyzer`.
   - Mục đích: chứng minh luồng chạy thực.

3. **RAG Demo**
   - Ảnh phiên CLI hỏi đáp và câu trả lời có phần nguồn tham khảo.

4. **Dashboard/Output**
   - Ảnh biểu đồ trend từ `output/sentiment_dashboard.json` (nếu đã có UI/notebook render).

### Cách thêm ảnh

Tạo thư mục:
- `docs/images/`

Đặt tên file rõ nghĩa:
- `docs/images/architecture.png`
- `docs/images/pipeline-runtime.png`
- `docs/images/rag-demo.png`
- `docs/images/dashboard.png`

Chèn vào README:

```markdown
![System Architecture](docs/images/architecture.png)
```

---

## 10) README theo module (đã bổ sung)

Đã bổ sung README ngắn cho các module chính:

- `scrapers/README.md`
- `pipeline/README.md`
- `ai_engine/README.md`
- `database/README.md`
- `evaluation/README.md`
- `time_series/README.md`

---

## 11) Có nên làm giao diện basic để mô tả chức năng?

**Có** - rất nên làm bản basic nếu mục tiêu là demo, pitching, hoặc handover.

Mức tối thiểu đề xuất:
- 1 trang dashboard:
  - Daily index line chart
  - Trend label hiện tại
  - Top tin tích cực/tiêu cực gần nhất
- 1 khung RAG chat:
  - Nhập câu hỏi
  - Hiển thị câu trả lời + nguồn

Bạn có thể bắt đầu bằng Streamlit để nhanh:
- Dùng `output/sentiment_dashboard.json` cho chart.
- Gọi `ask_market_assistant()` cho phần chat.

---

## 12) Troubleshooting nhanh

- Không kết nối Kafka/Mongo:
  - Kiểm tra `docker compose ps`
  - Kiểm tra port `9092`, `27017`
- Lỗi API Groq/HF:
  - Kiểm tra key/token trong `.env`
  - Giảm tần suất request hoặc chạy lại do rate-limit
- Chroma chưa có dữ liệu:
  - Chạy lại `database/vector_store.py` sau khi đã có `sentiment`

---

## 13) Roadmap khuyến nghị (production-minded)

- Chuẩn hóa logging (JSON logs) + centralized monitoring.
- Thêm unit tests/integration tests thực thụ (ngoài connectivity scripts).
- Đóng gói app service bằng `Dockerfile`.
- Thiết lập CI (lint/test/security scan).
- Tách config theo môi trường (`dev/staging/prod`).

