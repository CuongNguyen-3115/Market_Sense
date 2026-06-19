import os
import chromadb

# Trỏ đúng vào thư mục chroma_data của dự án
CHROMA_DB_DIR = r"C:\1. Project\2_Cuộc_thi\2026\3. HACK CX TOGETHER 2026\market_sense\backend\chroma_data"

def inspect_all_collections():
    print(f"🔍 Đang rà soát toàn bộ ChromaDB tại: {CHROMA_DB_DIR}")
    client = chromadb.PersistentClient(path=CHROMA_DB_DIR)
    
    # Lấy danh sách TẤT CẢ các collection đang tồn tại trong file 2MB này
    collections = client.list_collections()
    
    if not collections:
        print("⚠️ Cảnh báo: Database này hoàn toàn KHÔNG CÓ collection nào. File 2MB có thể là rác của SQLite.")
        return

    print(f"📂 BINGO! Tìm thấy {len(collections)} collection(s). Đang kiểm tra chi tiết...\n")
    print("=" * 60)

    for coll in collections:
        # Xử lý tương thích đa phiên bản của ChromaDB
        coll_name = coll.name if hasattr(coll, 'name') else coll
        
        # Lấy object collection để đếm
        collection_obj = client.get_collection(name=coll_name)
        count = collection_obj.count()
        
        print(f"👉 Tên Collection: '{coll_name}'")
        print(f"📊 Số lượng Vector: {count} bản ghi")
        
        if count > 0:
            print("   --- Trích xuất thử 1 bản ghi ---")
            sample = collection_obj.peek(1)
            
            # Kiểm tra xem lúc embed bạn có lưu lại đoạn text gốc không
            if sample.get('documents') and sample['documents'][0]:
                text_preview = str(sample['documents'][0][0])[:150] # Lấy 150 ký tự đầu
                print(f"   📝 Nội dung: {text_preview}...")
            else:
                print("   ⚠️ Bản ghi này chỉ chứa Vector số học/Metadata, không chứa text gốc.")
        
        print("=" * 60)

if __name__ == "__main__":
    inspect_all_collections()