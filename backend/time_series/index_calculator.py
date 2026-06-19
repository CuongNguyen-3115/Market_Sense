# Worker 2: Core logic Pandas: Groupby theo ngày/giờ, áp dụng trọng số (Weight: SBV > CafeF) để ra điểm Index tổng.
import pandas as pd

class SentimentIndexCalculator:
    def __init__(self, w_sbv: float = 0.7, w_cafef: float = 0.3):
        self.w_sbv = w_sbv
        self.w_cafef = w_cafef

    def calculate_daily_index(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Tính toán Chỉ số Tâm lý Tổng hợp áp dụng Trọng số Động.
        """
        df_calc = df.copy()

        def compute_dynamic_index(row):
            # Nếu điểm SBV = 0 (tức là không có tin vĩ mô mới), thị trường chạy theo tin tức vi mô
            if row['SBV'] == 0:
                return row['CafeF']
            # Nếu có tin vĩ mô, trọng số SBV sẽ áp đảo
            else:
                return (row['SBV'] * self.w_sbv) + (row['CafeF'] * self.w_cafef)

        # Apply công thức tính điểm tổng
        df_calc['Daily_Index'] = df_calc.apply(compute_dynamic_index, axis=1)

        # Gán nhãn text thô để tiện hiển thị trên Dashboard (nếu cần)
        def categorize_sentiment(score):
            if score >= 0.25:
                return 'Tích cực'
            elif score <= -0.25:
                return 'Tiêu cực'
            else:
                return 'Trung lập'

        df_calc['Daily_State'] = df_calc['Daily_Index'].apply(categorize_sentiment)

        return df_calc