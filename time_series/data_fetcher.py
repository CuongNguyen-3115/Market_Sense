# Query raw sentiment từ MongoDB theo khung thời gian (từ ngày A đến ngày B).
import pandas as pd
from pymongo import MongoClient
from datetime import datetime, timedelta
import pytz

class TimeSeriesDataFetcher:
    def __init__(self, mongo_uri: str, db_name: str, collection_name: str):
        self.client = MongoClient(mongo_uri)
        self.collection = self.client[db_name][collection_name]
        self.tz = pytz.timezone('Asia/Ho_Chi_Minh')

    def fetch_and_align_data(self, days_back: int = 30) -> pd.DataFrame:
        """
        Trích xuất dữ liệu, căn chỉnh Timezone và tạo Pivot Table chuỗi thời gian.
        """
        # 1. Xác định mốc thời gian an toàn
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        # Vì 'published_at' trong DB của bạn đang lưu dạng chuỗi ISO (VD: '2026-05-22T14:30:00')
        start_date_str = start_date.strftime('%Y-%m-%dT%H:%M:%S')

        # 2. Truy vấn MongoDB với Projection (Best Practice để tiết kiệm RAM)
        # Giả định cột điểm sentiment được lưu với tên 'sentiment_score'
        query = {"published_at": {"$gte": start_date_str}}
        projection = {
            "_id": 0, 
            "published_at": 1, 
            "source": 1, 
            "sentiment_score": 1  # Bắt buộc phải có cột này từ kết quả của Llama-3
        } 
        
        cursor = self.collection.find(query, projection)
        df = pd.DataFrame(list(cursor))
        
        if df.empty:
            raise ValueError(f"Không tìm thấy dữ liệu trong {days_back} ngày qua!")

        # 3. Chuẩn hóa Thời gian (Time Alignment)
        df['published_at'] = pd.to_datetime(df['published_at'])
        # Localize về múi giờ VN (GMT+7)
        df['published_at'] = df['published_at'].dt.tz_localize(self.tz, ambiguous='NaT', nonexistent='shift_forward')
        
        # 4. Resampling & Pivoting (Gom nhóm theo ngày và tách cột theo Nguồn)
        df.set_index('published_at', inplace=True)
        # Tính điểm trung bình theo từng ngày (freq='D') cho từng nguồn
        daily_df = df.groupby([pd.Grouper(freq='D'), 'source'])['sentiment_score'].mean().unstack(fill_value=None)
        
        # 5. Xử lý Missing Data (Imputation Strategy)
        # Tạo index chuẩn bao phủ mọi ngày, tránh việc mất dòng nếu cả 2 nguồn đều không có tin
        full_date_range = pd.date_range(start=start_date.date(), end=end_date.date(), freq='D', tz=self.tz)
        daily_df = daily_df.reindex(full_date_range)
        
        # Chiến lược: ffill(limit=2) cho cuối tuần, fillna(0) cho ngày lễ dài
        daily_df = daily_df.ffill(limit=2).fillna(0)
        
        # Đảm bảo Dataset luôn có đủ 2 cột dù 1 nguồn có thể bị thiếu hoàn toàn
        for col in ['SBV', 'CafeF']:
            if col not in daily_df.columns:
                daily_df[col] = 0.0
                
        daily_df.index.name = 'Date'
        
        # Trả về DataFrame với 2 cột chuẩn hóa: ['SBV', 'CafeF']
        return daily_df[['SBV', 'CafeF']]