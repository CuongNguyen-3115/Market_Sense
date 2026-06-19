# Worker 1: Trích xuất & Căn chỉnh Thời gian (ETL & Time Alignment)
import pandas as pd
from pymongo import MongoClient
from datetime import datetime, timedelta
import pytz
import logging

# Cấu hình logging cơ bản để in ra console
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TimeSeriesDataFetcher:
    def __init__(self, mongo_uri: str, db_name: str, collection_name: str):
        logger.info(f"Khởi tạo kết nối MongoDB: URI={mongo_uri}, DB={db_name}, Collection={collection_name}")
        self.client = MongoClient(mongo_uri)
        self.db = self.client[db_name]
        self.collection = self.db[collection_name]
        self.tz = pytz.timezone('Asia/Ho_Chi_Minh')

        # Ping thử DB để xem kết nối có ổn không
        try:
            self.client.admin.command('ping')
            logger.info("Kết nối MongoDB thành công.")
        except Exception as e:
            logger.error(f"Không thể kết nối tới MongoDB: {e}")

    def fetch_and_align_data(self, days_back: int = 30) -> pd.DataFrame:
        """
        Trích xuất dữ liệu, căn chỉnh Timezone và tạo Pivot Table chuỗi thời gian.
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        # Chú ý: Dữ liệu mẫu của bạn có dạng '2026-05-21T00:05:00'
        start_date_str = start_date.strftime('%Y-%m-%dT%H:%M:%S')

        # 1. Thực thi Query
        query = {"published_at": {"$gte": start_date_str}}
        projection = {
            "_id": 0, 
            "published_at": 1, 
            "source": 1, 
            "sentiment.score": 1
        } 
        
        logger.info(f"Đang thực thi truy vấn MongoDB...")
        logger.info(f"Query: {query}")
        logger.info(f"Projection: {projection}")

        # In thử 1 document mẫu từ DB để kiểm tra format ngày tháng (bỏ qua điều kiện lọc)
        sample_doc = self.collection.find_one({}, {"published_at": 1, "source": 1})
        if sample_doc:
             logger.info(f"Mẫu dữ liệu thực tế trong DB (để check format date): {sample_doc}")
        else:
             logger.warning("Collection hiện tại đang hoàn toàn trống!")

        cursor = self.collection.find(query, projection)
        raw_data = list(cursor)
        
        logger.info(f"Đã kéo về {len(raw_data)} bản ghi từ MongoDB.")
        
        if not raw_data:
            raise ValueError(f"Không tìm thấy dữ liệu từ ngày {start_date_str} đến nay.")

        # 2. Xử lý Nested Object
        logger.info("Đang Flatten dữ liệu (trích xuất sentiment.score)...")
        flattened_data = []
        for doc in raw_data:
            flattened_data.append({
                'published_at': doc.get('published_at'),
                'source': doc.get('source'),
                'score': doc.get('sentiment', {}).get('score', 0) 
            })
            
        df = pd.DataFrame(flattened_data)
        logger.info(f"Tạo DataFrame thành công. Kích thước: {df.shape}")

        # 3. Chuẩn hóa Thời gian 
        logger.info("Đang chuẩn hóa thời gian và chuyển đổi Timezone...")
        try:
             df['published_at'] = pd.to_datetime(df['published_at'])
             df['published_at'] = df['published_at'].dt.tz_localize(self.tz, ambiguous='NaT', nonexistent='shift_forward')
        except Exception as e:
             logger.error(f"Lỗi khi parse cột 'published_at'. Dữ liệu cột này có thể bị lỗi định dạng: {e}")
             raise e
        
        # 4. Resampling & Pivoting 
        logger.info("Đang Resampling (gom nhóm theo ngày) và Pivoting (tách cột SBV, CafeF)...")
        df.set_index('published_at', inplace=True)
        daily_df = df.groupby([pd.Grouper(freq='D'), 'source'])['score'].mean().unstack(fill_value=None)
        
        # 5. Xử lý Missing Data 
        logger.info("Đang xử lý Missing Data (Forward Fill và Fillna)...")
        full_date_range = pd.date_range(start=start_date.date(), end=end_date.date(), freq='D', tz=self.tz)
        daily_df = daily_df.reindex(full_date_range)
        
        daily_df = daily_df.ffill(limit=2).fillna(0)
        
        # Đảm bảo Dataset luôn có đủ 2 cột
        for col in ['SBV', 'CafeF']:
            if col not in daily_df.columns:
                logger.warning(f"Không có bất kỳ dữ liệu nào cho nguồn {col} trong khoảng thời gian này. Điền toàn bộ bằng 0.")
                daily_df[col] = 0.0
                
        daily_df.index.name = 'Date'
        
        logger.info("Xử lý dữ liệu hoàn tất!")
        return daily_df[['SBV', 'CafeF']]