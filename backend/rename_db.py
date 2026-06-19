from pymongo import MongoClient

def rename_database():
    # 1. Kết nối vào MongoDB local
    client = MongoClient("mongodb://localhost:27017/")
    
    old_db_name = "shb_sentiment"
    new_db_name = "sentiment"
    
    old_db = client[old_db_name]
    new_db = client[new_db_name]
    
    # 2. Lấy danh sách các collection trong DB cũ
    collections = old_db.list_collection_names()
    
    if not collections:
        print(f"⚠️ Không tìm thấy dữ liệu nào trong database '{old_db_name}'.")
        return

    print(f"🚀 Bắt đầu chuyển dữ liệu từ '{old_db_name}' sang '{new_db_name}'...\n")
    
    # 3. Duyệt qua từng collection và dùng lệnh Aggregate $out để copy
    for coll_name in collections:
        print(f"⏳ Đang xử lý collection: [{coll_name}]...")
        old_db[coll_name].aggregate([
            {"$match": {}}, 
            {"$out": {"db": new_db_name, "coll": coll_name}}
        ])
        print(f"✅ Đã copy xong [{coll_name}]!")

    # 4. Kiểm tra thành quả
    print("\n🎉 HOÀN TẤT SAO CHÉP!")
    print(f"Các collection hiện có trong DB mới '{new_db_name}': {new_db.list_collection_names()}")
    print(f"\n💡 Lời khuyên: Hãy lên Mongo Express kiểm tra lại. Nếu dữ liệu đã chuẩn, bạn có thể xóa DB '{old_db_name}' cũ đi.")

if __name__ == "__main__":
    rename_database()