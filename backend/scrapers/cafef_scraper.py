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
TOPIC_NAME = os.getenv("KAFKA_TOPIC_RAW_NEWS", "raw_news")

# CHIẾN LƯỢC MỚI: Quét theo thời gian thay vì số lượng
DAYS_TO_SCRAPE = 30
# Lọc từ khóa nghiêm ngặt để tiết kiệm token và đảm bảo giá trị định lượng
# TARGET_KEYWORDS = [
#     "tỷ giá", "lãi suất", "nhnn", "ngân hàng nhà nước", 
#     "tín phiếu", "shb", "trái phiếu", "tín dụng", "vĩ mô", "lạm phát", "fed"
# ]

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
# 2. HÀM TRÍCH XUẤT THÔ
# ==========================================
def extract_raw_article(article_html):
    """Trích xuất thô thông tin từ HTML, chưa qua màng lọc"""
    try:
        a_tag = article_html.find('h3').find('a')
        title = a_tag.text.strip()
        url = "https://cafef.vn" + a_tag['href']
        
        time_tag = article_html.find('span', class_='time time-ago')
        raw_date_str = time_tag['title'] if time_tag and time_tag.has_attr('title') else None
        
        sapo_tag = article_html.find('p', class_='sapo box-category-sapo')
        summary = sapo_tag.text.strip() if sapo_tag else ""
        
        if not title or not url or len(summary) < 10 or not raw_date_str:
            return None
            
        # Parse datetime từ chuỗi ISO của CafeF (thường có dạng YYYY-MM-DDTHH:MM:SS)
        # Lấy 19 ký tự đầu để tránh lỗi múi giờ nếu có
        pub_dt = datetime.fromisoformat(raw_date_str[:19])
        
        return {
            "title": title,
            "summary": summary,
            "url": url,
            "pub_dt": pub_dt,
            "published_at": raw_date_str
        }
    except Exception:
        return None # Bỏ qua lỗi do cấu trúc HTML dị biệt

# ==========================================
# 3. THUẬT TOÁN SCRAPING VỚI CỬA SỔ TRƯỢT 7 NGÀY
# ==========================================
def run_scraper():
    # Tính toán mốc thời gian chặn dưới
    cutoff_date = datetime.now() - timedelta(days=DAYS_TO_SCRAPE)
    print(f"🚀 Bắt đầu cào dữ liệu CafeF. Mục tiêu: Lùi về quá khứ tới {cutoff_date.strftime('%d/%m/%Y')}.")
    # print(f"🔍 Bộ lọc Keyword: {', '.join(TARGET_KEYWORDS)}")
    
    collected_count = 0
    scanned_count = 0
    page = 1
    max_pages = 50 # Tăng số trang tối đa vì 7 ngày có thể trải dài 20-30 trang
    stop_scraping = False
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
    }

    while not stop_scraping and page <= max_pages:
        url = "https://cafef.vn/thi-truong-chung-khoan.chn" if page == 1 else f"https://cafef.vn/timelinelist/18831/{page}.chn"
            
        print(f"⏳ Đang quét Trang {page}...")
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            print(f"⚠️ Cảnh báo: CafeF từ chối truy cập (Status: {response.status_code}). Dừng cào.")
            break
            
        soup = BeautifulSoup(response.text, 'html.parser')
        articles = soup.find_all('div', class_='tlitem')
        
        if not articles:
            break # Trang trống, hết dữ liệu
            
        for art in articles:
            raw_data = extract_raw_article(art)
            if not raw_data:
                continue
                
            scanned_count += 1
            
            # 1. Kiểm tra ranh giới thời gian (Time Window Boundary)
            if raw_data['pub_dt'] < cutoff_date:
                print(f"\n🛑 Đã chạm mốc thời gian {DAYS_TO_SCRAPE} ngày trước ({raw_data['pub_dt'].strftime('%d/%m/%Y')}). Dừng thuật toán.")
                stop_scraping = True
                break
                
            # # 2. Màng lọc từ khóa (Keyword Filtering)
            # content_lower = f"{raw_data['title']} {raw_data['summary']}".lower()
            # is_relevant = any(kw in content_lower for kw in TARGET_KEYWORDS)
            
            # if is_relevant:
            #     # Đóng gói theo chuẩn Data Contract
            #     final_data = {
            #         "id": f"cafef_{hashlib.md5(raw_data['url'].encode('utf-8')).hexdigest()}",
            #         "source": "CafeF",
            #         "category": "Thị trường chứng khoán",
            #         "title": raw_data['title'],
            #         "summary": raw_data['summary'],
            #         "url": raw_data['url'],
            #         "published_at": raw_data['published_at'],
            #         "scraped_at": datetime.now().isoformat()
            #     }
                
            #     # Cơ chế Idempotency ở consumer sẽ tự loại bỏ bài cũ nếu chạy lại
            #     producer.send(TOPIC_NAME, final_data)
            #     collected_count += 1
            #     print(f"[Lọc thành công {collected_count}] {final_data['title'][:60]}...")
            
            # 2. Đẩy thẳng mọi bài báo vào Kafka (Giữ nguyên phần Data Contract)
            final_data = {
                "id": f"cafef_{hashlib.md5(raw_data['url'].encode('utf-8')).hexdigest()}",
                "source": "CafeF",
                "category": "Thị trường chứng khoán",
                "title": raw_data['title'],
                "summary": raw_data['summary'],
                "url": raw_data['url'],
                "published_at": raw_data['published_at'],
                "scraped_at": datetime.now().isoformat()
            }
            
            producer.send(TOPIC_NAME, final_data)
            collected_count += 1
            print(f"[{collected_count}] Đã đẩy: {final_data['title'][:60]}...")

        page += 1
        time.sleep(2) # Nghỉ ngơi giữa các trang chống Ban IP

    producer.flush() # Chốt gửi toàn bộ hàng đợi
    print(f"\n✅ KẾT THÚC CÀO! Đã quét qua {scanned_count} bài báo.")
    print(f"✅ Đã chọn lọc & lưu thành công {collected_count} bản tin 'tinh hoa' vào Kafka.")

if __name__ == "__main__":
    run_scraper()