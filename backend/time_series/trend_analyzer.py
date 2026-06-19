# Worker 3: Tính toán Moving Average (SMA, EMA), đo lường gia tốc (Momentum) để gán nhãn Trend (Uptrend, Downtrend, Sideway).
import pandas as pd
import numpy as np

class TrendAnalyzer:
    def __init__(self, short_window: int = 3, long_window: int = 7):
        self.short_window = short_window
        self.long_window = long_window

    def analyze_trend(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Tính toán Moving Average và gán nhãn Xu hướng dựa trên Momentum.
        """
        df_trend = df.copy()

        # 1. Tính toán Đường trung bình động (Simple Moving Average)
        # min_periods=1 giúp ngày 1, ngày 2 không bị biến thành NaN
        df_trend['SMA_Short'] = df_trend['Daily_Index'].rolling(window=self.short_window, min_periods=1).mean()
        df_trend['SMA_Long'] = df_trend['Daily_Index'].rolling(window=self.long_window, min_periods=1).mean()

        # 2. Tính toán Gia tốc (Momentum) - Độ lệch giữa ngắn hạn và dài hạn
        df_trend['Momentum'] = df_trend['SMA_Short'] - df_trend['SMA_Long']

        # 3. Gán nhãn Xu hướng (Trend Labeling) dựa trên sự giao cắt
        def determine_trend(momentum):
            # Ngưỡng (Threshold) 0.05 giúp loại bỏ các tín hiệu nhiễu khi 2 đường đi quá sát nhau
            threshold = 0.05 
            if momentum > threshold:
                return 'Uptrend (Tích cực)'
            elif momentum < -threshold:
                return 'Downtrend (Tiêu cực)'
            else:
                return 'Sideway (Đi ngang)'

        df_trend['Trend_Label'] = df_trend['Momentum'].apply(determine_trend)

        return df_trend