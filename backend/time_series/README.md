# Time Series Module

Module phân tích chỉ số sentiment theo thời gian và xuất dữ liệu cho dashboard.

## Files
- `data_fetcher.py`: trích xuất + căn chỉnh dữ liệu từ Mongo.
- `index_calculator.py`: tính chỉ số sentiment tổng hợp theo trọng số.
- `trend_analyzer.py`: tính SMA/momentum và gán nhãn xu hướng.
- `pipeline.py`: ghép toàn bộ các bước và export JSON.

## Run (example)
```python
from time_series.pipeline import TimeSeriesPipeline

pipeline = TimeSeriesPipeline(
    mongo_uri="mongodb://localhost:27017/",
    db_name="sentiment",
    collection_name="clean_news"
)
pipeline.run_and_export(days_back=30, export_path="output/sentiment_dashboard.json")
```

## Output
- `output/sentiment_dashboard.json`

## Lưu ý vận hành
- Chỉ số có ý nghĩa khi dữ liệu sentiment đã được cập nhật đầy đủ.
