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
MIN_ARTICLES_THRESHOLD = 30  # Ngưỡng kích thước mẫu tối thiểu (CLT: N >= 30)

try:
    producer = KafkaProducer(
        bootstrap_servers=[KAFKA_SERVER],
        value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode('utf-8'),
        retries=3 # Tự động thử lại nếu Kafka bị nghẽn
    )
    print(f"✅ Đã kết nối Kafka Broker: {KAFKA_SERVER}")
except Exception as e:
    print(f"❌ LỖI NGHIÊM TRỌNG: Không thể kết nối Kafka. Chi tiết: {e}")
    exit(1)

# ==========================================
# 2. HÀM LÀM SẠCH VÀ TRÍCH XUẤT DỮ LIỆU
# ==========================================
def extract_article_data(article_html):
    """Trích xuất và chuẩn hóa 4 trường dữ liệu từ 1 khối HTML"""
    try:
        # Lấy Tiêu đề & Link
        a_tag = article_html.find('h3').find('a')
        title = a_tag.text.strip()
        url = "https://cafef.vn" + a_tag['href']
        
        # Lấy Thời gian chuẩn ISO 8601
        time_tag = article_html.find('span', class_='time time-ago')
        published_date = time_tag['title'] if time_tag and time_tag.has_attr('title') else datetime.now().isoformat()
        
        # Lấy Tóm tắt (Sapo)
        sapo_tag = article_html.find('p', class_='sapo box-category-sapo')
        summary = sapo_tag.text.strip() if sapo_tag else ""
        
        # Kiểm định chất lượng (Data Quality Check)
        if not title or not url or len(summary) < 10:
            return None # Loại bỏ tin rác, tin ảnh/video không có chữ
            
        return {
            "id": f"cafef_{hashlib.md5(url.encode('utf-8')).hexdigest()}",
            "source": "CafeF",
            "category": "Tài chính - Ngân hàng",
            "title": title,
            "summary": summary,
            "url": url,
            "published_at": published_date,
            "scraped_at": datetime.now().isoformat()
        }
    except AttributeError:
        return None # Bỏ qua lỗi do cấu trúc HTML dị biệt (quảng cáo)

# ==========================================
# 3. THUẬT TOÁN SCRAPING VỚI CỬA SỔ TRƯỢT
# ==========================================
def run_scraper():
    print(f"🚀 Bắt đầu cào dữ liệu CafeF. Mục tiêu: Thu thập >= {MIN_ARTICLES_THRESHOLD} tin hợp lệ.")
    
    collected_count = 0
    page = 1
    max_pages = 5 # Giới hạn chống lặp vô hạn (chống tràn RAM)
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    while collected_count < MIN_ARTICLES_THRESHOLD and page <= max_pages:
        # Tích hợp API ẩn do bạn vừa khám phá ra!
        if page == 1:
            url = "https://cafef.vn/tai-chinh-ngan-hang.chn"
        else:
            url = f"https://cafef.vn/timelinelist/18834/{page}.chn"
            
        print(f"⏳ Đang quét Trang {page}: {url}")
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            print(f"⚠️ Cảnh báo: CafeF từ chối truy cập (Status: {response.status_code}). Dừng cào.")
            break
            
        soup = BeautifulSoup(response.text, 'html.parser')
        articles = soup.find_all('div', class_='tlitem')
        
        for art in articles:
            if collected_count >= MIN_ARTICLES_THRESHOLD:
                break # Đã gom đủ số lượng tối thiểu, dừng vòng lặp
                
            data = extract_article_data(art)
            if data:
                # Đẩy luồng trực tiếp vào Kafka Topic
                producer.send(TOPIC_NAME, data)
                collected_count += 1
                print(f"[{collected_count}/{MIN_ARTICLES_THRESHOLD}] Đã đẩy: {data['title'][:60]}...")
                
        # Nghỉ ngơi giữa các trang để chống Ban IP
        page += 1
        time.sleep(2) 

    producer.flush() # Chốt gửi toàn bộ hàng đợi trong bộ nhớ
    print(f"✅ KẾT THÚC! Đã thu thập và lưu thành công {collected_count} bản tin vào Kafka.")

if __name__ == "__main__":
    run_scraper()