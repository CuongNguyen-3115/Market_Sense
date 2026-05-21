import requests

print("--- TEST ĐIỂM TRUNG LẬP ---")
try:
    # Gửi tới một dịch vụ test HTTP độc lập công cộng
    res = requests.post("https://httpbin.org/post", json={"test": "data"}, timeout=5)
    print(f"Httpbin Status: {res.status_code}")
    if "Cannot POST" in res.text:
        print("-> KẾT LUẬN: Mạng của bạn đang bị một Proxy Express chặn TẤT CẢ request ra ngoài!")
    else:
        print("-> Kết nối tới Httpbin bình thường.")
except Exception as e:
    print(f"Lỗi kết nối Httpbin: {e}")