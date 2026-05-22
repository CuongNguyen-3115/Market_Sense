import os
import json
import time
import requests
from bs4 import BeautifulSoup
from kafka import KafkaProducer
from dotenv import load_dotenv
from datetime import datetime, timedelta
import hashlib

# ==========================================
# 1. CẤU HÌNH HỆ THỐNG & KAFKA
# ==========================================
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

KAFKA_SERVER = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC_NAME = os.getenv("KAFKA_TOPIC_RAW_NEWS", "shb-raw-news")

# CHIẾN LƯỢC VĨ MÔ: Cửa sổ 30 ngày để bắt trọn 1 chu kỳ chính sách
DAYS_TO_SCRAPE = 30

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
            return None

        a_tag = col8.find('a', class_='title-news-link')
        title = a_tag.text.strip()
        url = a_tag['href']
        if url.startswith('/'):
            url = "https://www.sbv.gov.vn" + url

        time_tag = col8.find('span', class_='date-about')
        raw_time = time_tag.text.strip() 
        
        try:
            # Ép kiểu chuỗi người Việt sang đối tượng Datetime
            pub_dt = datetime.strptime(raw_time, "%d/%m/%Y | %H:%M:%S")
            published_date = pub_dt.isoformat()
        except ValueError:
            pub_dt = datetime.now()
            published_date = pub_dt.isoformat()

        summary_tag = col8.find('span', class_='top-news-detail')
        summary = summary_tag.text.strip() if summary_tag else ""

        if not title or not url:
            return None

        # Trả về cả Datetime object để phục vụ thuật toán trượt thời gian
        return {
            "pub_dt": pub_dt,  # Dùng nội bộ trong script
            "payload": {       # Payload thực tế đẩy lên Kafka
                "id": f"sbv_{hashlib.md5(url.encode('utf-8')).hexdigest()}",
                "source": "SBV",
                "category": "Chính sách Vĩ mô & Tiền tệ",
                "title": title,
                "summary": summary,
                "url": url,
                "published_at": published_date,
                "scraped_at": datetime.now().isoformat()
            }
        }
    except AttributeError:
        return None

# ==========================================
# 3. THUẬT TOÁN SCRAPING (TIME-WINDOW BOUNDARY)
# ==========================================
def run_sbv_scraper():
    cutoff_date = datetime.now() - timedelta(days=DAYS_TO_SCRAPE)
    print(f"🚀 Bắt đầu cào dữ liệu SBV. Lùi về quá khứ tới mốc: {cutoff_date.strftime('%d/%m/%Y')} (Cửa sổ 30 ngày).")
    
    base_url = "https://www.sbv.gov.vn/vi/web/sbv_portal/tin-tuc-su-kien"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    collected_count = 0
    scanned_count = 0
    page = 1
    max_pages = 15 # Tăng an toàn để quét đủ 1 tháng
    stop_scraping = False
    
    while not stop_scraping and page <= max_pages:
        print(f"⏳ Đang quét Trang {page} SBV...")
        
        params = {
            "p_p_id": "com_liferay_asset_publisher_web_portlet_AssetPublisherPortlet_INSTANCE_jaxi",
            "p_p_lifecycle": "0",
            "p_p_state": "normal",
            "p_p_mode": "view",
            "_com_liferay_asset_publisher_web_portlet_AssetPublisherPortlet_INSTANCE_jaxi_delta": "12",
            "p_r_p_resetCur": "false",
            "_com_liferay_asset_publisher_web_portlet_AssetPublisherPortlet_INSTANCE_jaxi_cur": str(page)
        }
        
        response = requests.get(base_url, headers=headers, params=params)
        
        if response.status_code != 200:
            print(f"⚠️ SBV từ chối truy cập (Status: {response.status_code}). Dừng cào.")
            break
            
        soup = BeautifulSoup(response.text, 'html.parser')
        rows = soup.find_all('div', class_='row')
        
        if not rows:
            break 
            
        for row in rows:
            data = extract_sbv_article(row)
            if not data:
                continue
                
            scanned_count += 1
            
            # Kiểm tra mốc thời gian chặn dưới
            if data['pub_dt'] < cutoff_date:
                print(f"\n🛑 Đã chạm mốc thời gian {DAYS_TO_SCRAPE} ngày trước ({data['pub_dt'].strftime('%d/%m/%Y')}). Dừng thuật toán.")
                stop_scraping = True
                break
                
            # Đẩy payload sạch vào Kafka
            producer.send(TOPIC_NAME, data['payload'])
            collected_count += 1
            print(f"[{collected_count}] Đã đẩy tin SBV: {data['payload']['title'][:60]}...")
        
        page += 1
        time.sleep(3) 

    producer.flush()
    print(f"\n✅ KẾT THÚC CÀO! Đã quét qua {scanned_count} bài báo.")
    print(f"✅ Đã lưu thành công {collected_count} bản tin Vĩ mô (1 tháng qua) vào Kafka.")

if __name__ == "__main__":
    run_sbv_scraper()