# Pipeline Module

Module trung gian xử lý dữ liệu streaming từ Kafka sang MongoDB theo data contract.

## Files
- `kafka_consumer.py`: consumer chính, validate schema và phân luồng lưu trữ.

## Luồng xử lý
1. Đọc message từ topic `raw_news`.
2. Validate các trường bắt buộc.
3. Dữ liệu hợp lệ -> `clean_news` (MongoDB, upsert theo `id`).
4. Dữ liệu lỗi -> `dead_letter_queue`.

## Run
```bash
python pipeline/kafka_consumer.py
```

## Lưu ý vận hành
- Cần Kafka và MongoDB chạy ổn định trước khi start consumer.
- Consumer đang chạy vòng lặp liên tục, nên chạy ở terminal riêng.
