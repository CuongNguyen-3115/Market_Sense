# TÀI LIỆU ĐẶC TẢ KỸ THUẬT: SBV SCRAPER (MACRO-ECONOMIC DATA INGESTION)

## 1. Thông tin chung
- **Đường dẫn file:** `shb_market_sense/scrapers/sbv_scraper.py`
- **Vai trò trong hệ thống:** Data Ingestion (Thu thập dữ liệu Vĩ mô & Chính sách tiền tệ).
- **Phân loại:** Kafka Producer.
- **Nguồn dữ liệu:** Cổng thông tin điện tử Ngân hàng Nhà nước Việt Nam (SBV).

## 2. Vai trò Chiến lược & Phân tích Định lượng
Trong kiến trúc của hệ thống SHB Market-Sense, file `sbv_scraper.py` không chỉ là một kịch bản cào web thông thường, mà nó đảm nhiệm việc xây dựng **"Đường cơ sở Vĩ mô" (Macro Baseline)**:
- **Trọng số ảnh hưởng (High Impact):** Dữ liệu từ SBV mang tính định hướng hệ thống, do đó được gán trọng số phân tích cao hơn ($W=5$) so với tin tức thị trường đại chúng.
- **Chuỗi thời gian bất đối xứng (Asymmetric Time-Series):** Khác với báo chí thị trường (cào 30 bài chỉ tương đương 1-2 ngày), việc cào 30 bài từ SBV giúp hệ thống nhìn xuyên thấu lịch sử chính sách trong vòng **1 tháng qua**. Điều này giúp AI FinBERT tránh bị "thiển cận" (short-sighted), cân bằng giữa biến động ngắn hạn của thị trường và tầm nhìn dài hạn của cơ quan quản lý.

## 3. Quy trình Kỹ thuật Cốt lõi (ETL - Extract & Transform)
Script được thiết kế để tương thích với hệ thống lõi Liferay Portal của Chính phủ, thông qua các bước:
1. **Dynamic Pagination (Phân trang động):** Vượt qua cơ chế tải trang tĩnh bằng cách truyền trực tiếp các tham số HTTP (`p_p_id`, `_cur`, `_delta`) để điều hướng tự động qua các trang dữ liệu.
2. **Data Transformation (Chuẩn hóa dữ liệu):** 
   - **Xử lý Thời gian:** Tự động "dịch" định dạng thời gian nội địa (`dd/mm/yyyy | HH:MM:SS`) sang chuẩn Quốc tế `ISO 8601` để đồng nhất với các nguồn dữ liệu khác.
   - **Gắn Tag Category:** Tự động gán nhãn "Chính sách Vĩ mô & Tiền tệ" làm cơ sở cho luồng phân tích trọng số sau này.
3. **Data Streaming:** Đẩy luồng dữ liệu liên tục dạng JSON vào Kafka Topic `shb-raw-news`.

## 4. Hợp đồng Dữ liệu (Data Contract)
Dữ liệu đầu ra tuân thủ nghiêm ngặt cấu trúc chung của toàn bộ Pipeline, đảm bảo trạm Consumer có thể xử lý mượt mà:

```json
{
  "id": "sbv_a1b2c3d4e5f6g7h8... (Mã MD5 duy nhất)",
  "source": "SBV",
  "category": "Chính sách Vĩ mô & Tiền tệ",
  "title": "Hội đồng quản trị Ngân hàng Chính sách xã hội Việt Nam họp...",
  "summary": "Ngày 14/5/2026, tại Hà Nội, Hội đồng quản trị...",
  "url": "[https://www.sbv.gov.vn/](https://www.sbv.gov.vn/)...",
  "published_at": "2026-05-14T11:55:00",
  "scraped_at": "2026-05-17T21:00:00"
}
```

## 5. Cơ chế Đảm bảo Toàn vẹn Dữ liệu (Data Integrity & Idempotency)
- **Tính Lũy đẳng (Idempotency) qua MD5 Hashing:** Khắc phục triệt để lỗi trùng lặp dữ liệu trong hệ thống phân tán. Mỗi bài báo được băm (hash) URL bằng thuật toán `MD5` để tạo ra một ID bất biến. Khi kết hợp với lệnh `upsert` tại MongoDB, hệ thống đảm bảo **không bao giờ sinh ra dữ liệu rác/trùng lặp** dù script có được chạy lại (trigger) hàng trăm lần.
- **Fallback Logic:** Cơ chế tự động lấy thời điểm cào (Scraped Time) làm thời gian đăng bài (Published Time) nếu cấu trúc HTML của SBV đột ngột thay đổi, giúp Pipeline không bị "đứt gãy".
- **Polite Scraping:** Áp dụng `time.sleep(3)` để tôn trọng tài nguyên máy chủ của Cơ quan Nhà nước.