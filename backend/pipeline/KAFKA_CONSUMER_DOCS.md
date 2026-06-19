# TÀI LIỆU ĐẶC TẢ KỸ THUẬT: KAFKA CONSUMER (DATA SINK & GATEWAY)

## 1. Thông tin chung
- **Đường dẫn file:** `market_sense/pipeline/kafka_consumer.py`
- **Vai trò trong hệ thống:** Data Sink / Trạm thu nhận và Kiểm duyệt dữ liệu.
- **Phân loại:** Apache Kafka Consumer.
- **Nguồn nhận (Source):** Kafka Topic `raw_news`.
- **Đích đến (Sink):** Cơ sở dữ liệu NoSQL MongoDB (`sentiment`).

## 2. Vai trò Chiến lược trong Kiến trúc Hệ thống
Nếu các file Scraper đóng vai trò là "Thợ mỏ" đi đào dữ liệu thô, thì `kafka_consumer.py` chính là **"Trạm kiểm duyệt Hải quan" (Gatekeeper)**. File này đảm bảo tuyệt đối rằng: Mô hình AI FinBERT ở chặng sau (Ngày 3) sẽ chỉ nhận được những dữ liệu sạch, đúng chuẩn và không bị trùng lặp. 

Sự tách biệt giữa Producer (Scraper) và Consumer thông qua Kafka tạo ra một **Kiến trúc Bất đồng bộ (Asynchronous Architecture)**, cho phép hệ thống cào web và hệ thống lưu trữ hoạt động độc lập, không bị sụp đổ dây chuyền (Cascading Failure) nếu một bên gặp sự cố.

## 3. Quy trình Xử lý Cốt lõi (Data Ingestion Flow)
1. **Continuous Listening (Lắng nghe liên tục):** Đăng ký vào Consumer Group `sentiment-consumer-group`, liên tục lắng nghe các thông điệp (messages) mới được đẩy lên Topic Kafka theo thời gian thực (Real-time Streaming).
2. **Deserialization (Giải mã):** Chuyển đổi dữ liệu chuỗi byte từ Kafka trở lại định dạng JSON nguyên bản.
3. **Routing & Storage (Phân luồng và Lưu trữ):** Dựa trên kết quả kiểm duyệt, phân bổ dữ liệu vào đúng Collection trong MongoDB.

## 4. Tiêu chuẩn Kiểm soát Chất lượng (Data Quality Control)
Hệ thống áp dụng 2 Pattern kinh điển trong Data Engineering:
- **Data Contract Validation (Kiểm chứng Hợp đồng Dữ liệu):** Mọi bản tin trước khi vào Database đều phải vượt qua hàm `validate_article()`. Hàm này kiểm tra sự tồn tại của 5 trường dữ liệu sống còn: `id`, `title`, `summary`, `url`, và `published_at`.
- **Dead Letter Queue - DLQ (Hàng đợi Dữ liệu Lỗi):** 
  - Nếu bản tin ĐẠT chuẩn $\rightarrow$ Lưu vào bảng `clean_news` (Dữ liệu sạch cho AI).
  - Nếu bản tin LỖI (thiếu trường, sai định dạng) $\rightarrow$ Cách ly ngay lập tức vào bảng `dead_letter_queue` (Thùng rác). Điều này giúp hệ thống không bị crash và lưu lại dấu vết (log) để Kỹ sư Data phân tích sau.

## 5. Cơ chế Đảm bảo Toàn vẹn Dữ liệu (Fault Tolerance & Idempotency)
- **Idempotency (Tính Lũy đẳng chống trùng lặp):** Kết hợp mã băm `MD5` từ Scraper và lệnh `upsert=True` (Update/Insert) của MongoDB. Cho dù thông điệp bị Kafka gửi lại nhiều lần (do lỗi mạng) hoặc Scraper chạy đi chạy lại, dữ liệu trong Database vẫn duy trì tính duy nhất tuyệt đối.
- **Auto-Offset Reset:** Khai báo cấu hình `auto_offset_reset='earliest'`. Nếu Consumer bị sập (mất điện, bảo trì server), khi khởi động lại, nó sẽ tự động đọc tiếp các bản tin chưa được xử lý trong Kafka mà không làm thất thoát bất kỳ dòng dữ liệu nào (Zero Data Loss).
- **Graceful Exception Handling:** Mọi tương tác với Database đều bọc trong `try...except`, đảm bảo Consumer luôn sống sót (Keep-alive) 24/7 để hứng luồng dữ liệu.