import pandas as pd
import json
import os
import logging
from datetime import datetime

# Import các module đã viết
from data_fetcher import TimeSeriesDataFetcher
from index_calculator import SentimentIndexCalculator
from trend_analyzer import TrendAnalyzer

logger = logging.getLogger(__name__)

class TimeSeriesPipeline:
    def __init__(self, mongo_uri: str, db_name: str, collection_name: str):
        self.fetcher = TimeSeriesDataFetcher(mongo_uri, db_name, collection_name)
        self.calculator = SentimentIndexCalculator(w_sbv=0.7, w_cafef=0.3)
        self.analyzer = TrendAnalyzer(short_window=3, long_window=7)

    def run_and_export(self, days_back: int, export_path: str = "output/sentiment_dashboard.json"):
        """
        Chạy toàn bộ luồng Time-Series và xuất ra file JSON cho Frontend.
        """
        logger.info("=== BẮT ĐẦU CHẠY PIPELINE TIME-SERIES ===")
        
        # 1. Trích xuất & Căn chỉnh
        df_raw = self.fetcher.fetch_and_align_data(days_back=days_back)
        
        # 2. Tính toán Trọng số
        df_index = self.calculator.calculate_daily_index(df_raw)
        
        # 3. Phân tích Xu hướng
        df_final = self.analyzer.analyze_trend(df_index)
        
        # 4. Định dạng Data cho Frontend (Chuẩn hóa JSON)
        # Frontend thường thích nhận format: { "dates": [...], "daily_index": [...], "trend": [...] }
        export_data = {
            "metadata": {
                "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "days_analyzed": days_back,
                "current_trend": df_final['Trend_Label'].iloc[-1] # Lấy trend của ngày gần nhất
            },
            "data": {
                # Format ngày thành chuỗi YYYY-MM-DD
                "dates": df_final.index.strftime('%Y-%m-%d').tolist(), 
                # Làm tròn điểm index 3 chữ số thập phân cho nhẹ file
                "daily_index": df_final['Daily_Index'].round(3).tolist(),
                "sma_short": df_final['SMA_Short'].round(3).tolist(),
                "sma_long": df_final['SMA_Long'].round(3).tolist(),
                "momentum": df_final['Momentum'].round(3).tolist(),
                "trend_labels": df_final['Trend_Label'].tolist()
            }
        }

        # 5. Lưu file JSON
        os.makedirs(os.path.dirname(export_path), exist_ok=True)
        with open(export_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=4)
            
        logger.info(f"=== PIPELINE HOÀN TẤT! Đã lưu JSON tại: {export_path} ===")
        return export_data

if __name__ == "__main__":
    # Cấu hình kết nối
    MONGO_URI = "mongodb://localhost:27017/" # Hoặc lấy từ os.getenv
    DB_NAME = "sentiment"
    COLLECTION_NAME = "clean_news"

    # Khởi tạo pipeline
    pipeline = TimeSeriesPipeline(MONGO_URI, DB_NAME, COLLECTION_NAME)
    
    # Chạy và xuất file
    try:
        pipeline.run_and_export(days_back=60, export_path="output/sentiment_dashboard.json")
    except Exception as e:
        logger.error(f"Lỗi khi chạy pipeline: {e}")