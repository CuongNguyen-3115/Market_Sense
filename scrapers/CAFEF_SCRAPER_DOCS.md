# TÀI LIỆU ĐẶC TẢ KỸ THUẬT: CAFEF SCRAPER (KAFKA PRODUCER)

## 1. Thông tin chung
- **Đường dẫn file:** `shb_market_sense/scrapers/cafef_scraper.py`
- **Vai trò trong hệ thống:** Data Ingestion (Thu thập dữ liệu thô).
- **Phân loại:** Kafka Producer.
- **Nguồn dữ liệu:** Chuyên mục "Tài chính - Ngân hàng" trên báo điện tử CafeF.

## 2. Mục tiêu kinh doanh & Toán học
File này chịu trách nhiệm cung cấp "nguyên liệu đầu vào" (dữ liệu văn bản) cho mô hình AI phân tích tâm lý thị trường (Market Sentiment). 

Để đảm bảo Chỉ số Tâm lý Thị trường (Market Sentiment Index) có độ tin cậy về mặt thống kê và tuân thủ **Định lý Giới hạn Trung tâm (CLT)**, script được thiết kế với **Thuật toán Cửa sổ trượt (Rolling Window)** kết hợp với mốc chặn **$N \ge 30$**:
- Hệ thống không cào theo ngày lịch cố định, mà cào ngược từ thời điểm hiện tại về quá khứ.
- Vòng lặp chỉ dừng lại khi gom đủ tối thiểu 30 bài báo HỢP LỆ (đủ để vẽ biểu đồ phân phối chuẩn), đảm bảo hệ thống luôn có dữ liệu để chạy kể cả trong những ngày cuối tuần (ít tin tức).

## 3. Quy trình xử lý cốt lõi (ETL - Extract & Transform)
Script thực hiện quy trình tự động hóa với 4 bước nghiêm ngặt:
1. **Request & Pagination:** Tự động gửi HTTP Request kèm `User-Agent` (giả lập trình duyệt) để vượt tường lửa. Tự động chuyển trang (Pagination) để tìm kiếm dữ liệu.
2. **DOM Parsing:** Sử dụng `BeautifulSoup` để bóc tách cấu trúc HTML render từ Server.
3. **Data Quality Control (Làm sạch & Lọc nhiễu):**
   - Loại bỏ các bài báo thiếu tiêu đề, thiếu URL.
   - Loại bỏ các bài báo chỉ có ảnh/video (độ dài Sapo < 10 ký tự) để tránh làm nghẽn mô hình NLP.
   - Tối ưu hóa Token LLM: Chỉ trích xuất Tiêu đề (Title) và Tóm tắt (Sapo) thay vì toàn bộ nội dung bài báo, giúp cô đọng ngữ cảnh cảm xúc.
4. **Data Streaming:** Đóng gói dữ liệu thành chuẩn JSON và bắn trực tiếp (Streaming) vào Kafka Topic `shb-raw-news` thông qua cổng `9092`.

## 4. Hợp đồng Dữ liệu (Data Contract / Output Schema)
Mỗi bản tin hợp lệ được đẩy lên Kafka sẽ tuân thủ nghiêm ngặt Schema định dạng JSON sau:

```json
{
  "id": "cafef_123456789 (Mã hash duy nhất từ URL)",
  "source": "CafeF",
  "category": "Tài chính - Ngân hàng",
  "title": "Tiêu đề bài viết",
  "summary": "Nội dung đoạn Sapo tóm tắt",
  "url": "[https://cafef.vn/](https://cafef.vn/)...",
  "published_at": "2026-05-17T11:17:00 (Chuẩn ISO 8601)",
  "scraped_at": "2026-05-17T15:30:00 (Chuẩn ISO 8601)"
}
```

## 5. Cơ chế Quản trị Rủi ro (Fault Tolerance)
- **Chống chặn IP (Anti-ban):** Áp dụng độ trễ `time.sleep(2)` giữa các lần chuyển trang để giảm tải cho server đối tác.
- **Bảo mật:** Toàn bộ thông tin kết nối (IP Kafka, Tên Topic) được cô lập trong file `.env`.
- **Exception Handling:** Sử dụng khối `try...except` để đảm bảo hệ thống không bị crash (văng lỗi) khi gặp một cấu trúc HTML quảng cáo dị biệt.