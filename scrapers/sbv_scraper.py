import os
import json
import time
import requests
from bs4 import BeautifulSoup
from kafka import KafkaProducer
from dotenv import load_dotenv
from datetime import datetime
import hashlib

# ==========================================
# 1. CẤU HÌNH HỆ THỐNG & KAFKA
# ==========================================
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

KAFKA_SERVER = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC_NAME = os.getenv("KAFKA_TOPIC_RAW_NEWS", "shb-raw-news")

try:
    producer = KafkaProducer(
        bootstrap_servers=[KAFKA_SERVER],
        value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode('utf-8'),
        retries=3
    )
    print(f"✅ Đã kết nối Kafka Broker: {KAFKA_SERVER}")
except Exception as e:
    print(f"❌ LỖI KAFKA: {e}")
    exit(1)

# ==========================================
# 2. HÀM TRÍCH XUẤT VÀ CHUẨN HÓA DỮ LIỆU
# ==========================================
def extract_sbv_article(row_html):
    """Trích xuất dữ liệu từ thẻ <div class="row"> của SBV"""
    try:
        col8 = row_html.find('div', class_='col-sm-8')
        if not col8:
            return None # Bỏ qua nếu không đúng cấu trúc bài báo

        # 1. Lấy Tiêu đề & URL
        a_tag = col8.find('a', class_='title-news-link')
        title = a_tag.text.strip()
        url = a_tag['href']
        if url.startswith('/'):
            url = "https://www.sbv.gov.vn" + url

        # 2. Xử lý Thời gian sang chuẩn ISO 8601
        time_tag = col8.find('span', class_='date-about')
        raw_time = time_tag.text.strip() # VD: "14/05/2026 | 11:55:00"
        try:
            # Ép kiểu chuỗi người Việt sang đối tượng Datetime
            dt_obj = datetime.strptime(raw_time, "%d/%m/%Y | %H:%M:%S")
            published_date = dt_obj.isoformat()
        except ValueError:
            published_date = datetime.now().isoformat() # Fallback nếu SBV đổi format

        # 3. Lấy Tóm tắt (Sapo)
        summary_tag = col8.find('span', class_='top-news-detail')
        summary = summary_tag.text.strip() if summary_tag else ""

        # Kiểm định chất lượng
        if not title or not url:
            return None

        # Data Contract: Đảm bảo Schema giống hệt CafeF
        return {
            "id": f"sbv_{hashlib.md5(url.encode('utf-8')).hexdigest()}",
            "source": "SBV",
            "category": "Chính sách Vĩ mô & Tiền tệ", # Đánh trọng số cao cho Category này
            "title": title,
            "summary": summary,
            "url": url,
            "published_at": published_date,
            "scraped_at": datetime.now().isoformat()
        }
    except AttributeError:
        return None

# ==========================================
# 3. THUẬT TOÁN SCRAPING
# ==========================================
def run_sbv_scraper():
    target_count = 30 # Nâng ngưỡng lên 30 bài để đủ dữ liệu cho 1 tháng
    print(f"🚀 Bắt đầu cào dữ liệu Ngân hàng Nhà nước (SBV). Mục tiêu: {target_count} tin...")
    
    base_url = "https://www.sbv.gov.vn/vi/web/sbv_portal/tin-tuc-su-kien"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    collected_count = 0
    page = 1
    max_pages = 10 # Giới hạn an toàn chống lặp vô hạn
    
    while collected_count < target_count and page <= max_pages:
        print(f"⏳ Đang quét Trang {page} SBV...")
        
        # Khai báo bộ tham số của hệ thống Liferay Portal (từ link bạn cung cấp)
        params = {
            "p_p_id": "com_liferay_asset_publisher_web_portlet_AssetPublisherPortlet_INSTANCE_jaxi",
            "p_p_lifecycle": "0",
            "p_p_state": "normal",
            "p_p_mode": "view",
            "_com_liferay_asset_publisher_web_portlet_AssetPublisherPortlet_INSTANCE_jaxi_delta": "12",
            "p_r_p_resetCur": "false",
            "_com_liferay_asset_publisher_web_portlet_AssetPublisherPortlet_INSTANCE_jaxi_cur": str(page)
        }
        
        # Gửi Request kèm params tự động ghép vào URL
        response = requests.get(base_url, headers=headers, params=params)
        
        if response.status_code != 200:
            print(f"⚠️ SBV từ chối truy cập (Status: {response.status_code}). Dừng cào.")
            break
            
        soup = BeautifulSoup(response.text, 'html.parser')
        rows = soup.find_all('div', class_='row')
        
        if not rows:
            break # Thoát nếu trang không còn bài viết nào
            
        for row in rows:
            if collected_count >= target_count:
                break # Gom đủ số lượng thì dừng
                
            data = extract_sbv_article(row)
            if data:
                producer.send(TOPIC_NAME, data)
                collected_count += 1
                print(f"[{collected_count}/{target_count}] Đã đẩy tin SBV: {data['title'][:60]}...")
        
        page += 1
        time.sleep(3) # Nghỉ ngơi 3 giây để tôn trọng máy chủ của cơ quan Nhà nước

    producer.flush()
    print(f"✅ KẾT THÚC! Đã thu thập {collected_count} bản tin chính thức từ SBV.")

    producer.flush()
    print(f"✅ KẾT THÚC! Đã thu thập {collected_count} bản tin chính thức từ SBV.")

if __name__ == "__main__":
    run_sbv_scraper()