import os
import chromadb
from chromadb.utils import embedding_functions
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# ==========================================
# 1. CẤU HÌNH HỆ THỐNG
# ==========================================
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    print("❌ Lỗi: Không tìm thấy GROQ_API_KEY.")
    exit(1)

# Khởi tạo Groq Client (Sử dụng model Llama 3.1 70B siêu thông minh cho RAG)
groq_client = Groq(api_key=GROQ_API_KEY)
RAG_MODEL = "llama-3.3-70b-versatile" 

# Kết nối ChromaDB
CHROMA_DB_DIR = os.path.join(os.path.dirname(__file__), '..', 'chroma_data')
chroma_client = chromadb.PersistentClient(path=CHROMA_DB_DIR)

# Sử dụng chung mô hình SBERT tiếng Việt đã dùng ở Ngày 3 để đối chiếu Vector
emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="keepitreal/vietnamese-sbert")
vector_collection = chroma_client.get_collection(name="shb_market_knowledge", embedding_function=emb_fn)

# ==========================================
# 2. HÀM RAG CỐT LÕI
# ==========================================
def ask_shb_assistant(user_query, top_k=3):
    print(f"\n🔍 Đang tìm kiếm thông tin liên quan đến: '{user_query}'...")
    
    # BƯỚC 1: RETRIEVAL (Truy xuất ChromaDB)
    # Tìm top_k bài báo có vector ngữ nghĩa gần nhất với câu hỏi
    results = vector_collection.query(
        query_texts=[user_query],
        n_results=top_k
    )
    
    if not results['documents'][0]:
        return "Xin lỗi, hiện tại tôi không tìm thấy tin tức nào trên thị trường liên quan đến danh mục của quý khách."

    # BƯỚC 2: XÂY DỰNG CONTEXT (Tăng cường) - ĐÃ BỔ SUNG URL
    context_str = ""
    for i in range(len(results['documents'][0])):
        doc_text = results['documents'][0][i]
        meta = results['metadatas'][0][i]
        
        sentiment_tag = "⚠️ TIÊU CỰC" if meta['label'] == 'negative' else ("✅ TÍCH CỰC" if meta['label'] == 'positive' else "ℹ️ TRUNG LẬP")
        
        context_str += f"- Bản tin {i+1} [{sentiment_tag}]: {doc_text}\n"
        context_str += f"  (Nguồn: {meta['source']} - URL: {meta.get('url', 'Không có link')} - Cập nhật: {meta['published_at'][:10]})\n\n"

    print("🧠 Đang tổng hợp và phân tích bằng AI (Groq LPU)...\n")

    # BƯỚC 3: GENERATION (Sinh câu trả lời bằng LLM)
    system_prompt = """Bạn là Cố vấn Quản trị Rủi ro Đầu tư cấp cao tại ngân hàng SHB.
Nhiệm vụ của bạn là tư vấn cho Khách hàng VIP dựa BẮT BUỘC vào các bản tin thị trường (Context) được cung cấp.

Quy tắc nghiêm ngặt:
1. Xưng hô: "Tôi" (đại diện SHB) và "Quý khách".
2. KHÔNG bịa đặt thông tin ngoài Context. Nếu Context không đủ, hãy nói "Dựa trên dữ liệu hiện tại, chưa có tín hiệu rõ ràng..."
3. Trình bày theo cấu trúc 3 phần:
   - Tổng quan thị trường (Dựa trên Context).
   - Tác động đến danh mục của khách hàng (Phân tích rủi ro/cơ hội).
   - Hành động khuyến nghị (Gợi ý Mua/Bán/Giữ hoặc Theo dõi thêm).
4. Phải giữ giọng điệu chuyên nghiệp, điềm tĩnh và khách quan.
5. BẮT BUỘC TRÍCH DẪN NGUỒN: Ở cuối câu trả lời, tạo một mục "Nguồn tham khảo" và liệt kê chính xác URL của các bản tin đã dùng."""

    user_prompt = f"""Câu hỏi của khách hàng: "{user_query}"

Đây là các thông tin thị trường mới nhất (Context):
{context_str}

Hãy phân tích và đưa ra lời khuyên."""

    try:
        response = groq_client.chat.completions.create(
            model=RAG_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3, # Giữ temperature thấp để AI không "ảo giác", bám sát tin tức
            max_tokens=800
        )
        answer = response.choices[0].message.content
        
        # SỬA Ở ĐÂY: Trả về CẢ câu trả lời VÀ Context
        return answer, context_str
    
    except Exception as e:
        return f"❌ Lỗi khi gọi API Sinh văn bản: {str(e)}"

# ==========================================
# 3. GIAO DIỆN CHATBOT CLI TEST
# ==========================================
if __name__ == "__main__":
    print("="*60)
    print("🤖 CHÀO MỪNG ĐẾN VỚI TRỢ LÝ ẢO SHB MARKET-SENSE")
    print("Gõ 'exit' hoặc 'quit' để thoát.")
    print("="*60)
    
    while True:
        query = input("\n👤 Khách hàng VIP: ")
        if query.lower() in ['exit', 'quit']:
            break
            
        answer = ask_shb_assistant(query)
        
        print("\n💼 SHB Assistant:")
        print("-" * 40)
        print(answer)
        print("-" * 40)