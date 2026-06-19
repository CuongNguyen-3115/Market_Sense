import os
import chromadb
from chromadb.utils import embedding_functions
from groq import Groq
from dotenv import load_dotenv
import json

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
RAG_MODEL = "llama-3.1-8b-instant" 

# Kết nối ChromaDB
CHROMA_DB_DIR = r"C:\1. Project\2_Cuộc_thi\2026\3. HACK CX TOGETHER 2026\market_sense\backend\chroma_data"
chroma_client = chromadb.PersistentClient(path=CHROMA_DB_DIR)

# Sử dụng chung mô hình SBERT tiếng Việt đã dùng ở Ngày 3 để đối chiếu Vector
emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="keepitreal/vietnamese-sbert")
vector_collection = chroma_client.get_or_create_collection(
    name="market_knowledge", 
    embedding_function=emb_fn
)

def classify_intent(user_query):
    """
    Sử dụng LLM để phân loại nhanh ý định của người dùng.
    Trả về 'small_talk' hoặc 'market_query'.
    """
    router_prompt = """Bạn là một hệ thống phân loại ý định (Intent Classifier).
Nhiệm vụ của bạn là đọc câu hỏi của người dùng và phân loại nó vào đúng 1 trong 2 nhóm:
- "small_talk": Các câu chào hỏi, giao tiếp thông thường, hoặc câu hỏi không liên quan đến tài chính, chứng khoán, tin tức thị trường (Ví dụ: "Chào bạn", "Bạn tên gì", "Thời tiết hôm nay", "Cảm ơn").
- "market_query": Các câu hỏi tìm kiếm thông tin về tài chính, chứng khoán, công ty, xu hướng thị trường, hoặc yêu cầu phân tích (Ví dụ: "Giá vàng thế nào", "FPT hôm nay ra sao", "Nhận định VNIndex").

Bạn PHẢI trả về đúng định dạng JSON, không giải thích gì thêm: {"intent": "small_talk" hoặc "market_query"}"""

    try:
        response = groq_client.chat.completions.create(
            model=RAG_MODEL, # Bạn có thể dùng một model nhỏ hơn (như llama3-8b-8192) cho bước này để tiết kiệm/nhanh hơn
            messages=[
                {"role": "system", "content": router_prompt},
                {"role": "user", "content": user_query}
            ],
            response_format={"type": "json_object"}, # Ép trả về JSON
            temperature=0
        )
        result = json.loads(response.choices[0].message.content)
        return result.get("intent", "market_query") # Mặc định fallback về market_query
    except:
        return "market_query" # Nếu lỗi, cứ coi như hỏi thị trường


def ask_market_assistant(user_query, top_k=3):
    print(f"\n🔍 Đang phân tích ý định câu hỏi: '{user_query}'...")
    
    # BƯỚC 0: ROUTING (Định tuyến)
    intent = classify_intent(user_query)
    
    if intent == "small_talk":
        print("➡️ Ý định: Giao tiếp thông thường. Bỏ qua ChromaDB.")
        # Nếu là small talk, gọi thẳng LLM trả lời giao tiếp, KHÔNG dùng Context
        system_prompt = """Bạn là Trợ lý AI Market Sense. Hãy chào hỏi hoặc phản hồi lại khách hàng một cách lịch sự, thân thiện và ngắn gọn. Xưng hô: "Tôi" và "Quý khách"."""
        try:
             response = groq_client.chat.completions.create(
                model=RAG_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_query}
                ],
                temperature=0.7
            )
             # Trả về câu trả lời và context rỗng
             return response.choices[0].message.content, ""
        except Exception as e:
             return f"❌ Lỗi khi phản hồi: {str(e)}", ""

    # ---------------------------------------------------------
    # NẾU LÀ MARKET_QUERY -> CHẠY LUỒNG RAG CŨ CỦA BẠN
    # ---------------------------------------------------------
    print("➡️ Ý định: Hỏi thị trường. Bắt đầu luồng RAG...")
    
    # BƯỚC 1: RETRIEVAL (Truy xuất ChromaDB)
    results = vector_collection.query(
        query_texts=[user_query],
        n_results=top_k
    )
    
    if not results['documents'][0]:
        return "Xin lỗi, hiện tại tôi không tìm thấy tin tức nào trên thị trường liên quan đến danh mục của quý khách.", ""

    # BƯỚC 2: XÂY DỰNG CONTEXT
    context_str = ""
    for i in range(len(results['documents'][0])):
        doc_text = results['documents'][0][i]
        meta = results['metadatas'][0][i]
        
        sentiment_tag = "⚠️ TIÊU CỰC" if meta['label'] == 'negative' else ("✅ TÍCH CỰC" if meta['label'] == 'positive' else "ℹ️ TRUNG LẬP")
        
        context_str += f"- Bản tin {i+1} [{sentiment_tag}]: {doc_text}\n"
        context_str += f"  (Nguồn: {meta['source']} - URL: {meta.get('url', 'Không có link')} - Cập nhật: {meta['published_at'][:10]})\n\n"

    print("🧠 Đang tổng hợp và phân tích bằng AI (Groq LPU)...\n")

    # BƯỚC 3: GENERATION (Sinh câu trả lời RAG)
    system_prompt = """Bạn là Cố vấn Quản trị Rủi ro Đầu tư cấp cao tại ngân hàng.
Nhiệm vụ của bạn là tư vấn cho Khách hàng VIP dựa BẮT BUỘC vào các bản tin thị trường (Context) được cung cấp.

Quy tắc nghiêm ngặt:
1. Xưng hô: "Tôi" (đại diện ngân hàng) và "Quý khách".
2. KHÔNG bịa đặt thông tin ngoài Context. Nếu Context không đủ, hãy nói "Dựa trên dữ liệu hiện tại, chưa có tín hiệu rõ ràng..."
3. Trình bày theo cấu trúc 3 phần:
   - Tổng quan thị trường (Dựa trên Context).
   - Tác động đến danh mục của khách hàng (Phân tích rủi ro/cơ hội).
   - Hành động khuyến nghị (Gợi ý Mua/Bán/Giữ hoặc Theo dõi thêm).
4. Phải giữ giọng điệu chuyên nghiệp, điềm tĩnh và khách quan."""

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
            temperature=0.2,
            max_tokens=1024
        )
        answer = response.choices[0].message.content
        
        return answer, context_str
    
    except Exception as e:
        return f"❌ Lỗi khi gọi API Sinh văn bản: {str(e)}", ""

# ==========================================
# 3. GIAO DIỆN CHATBOT CLI TEST
# ==========================================
if __name__ == "__main__":
    print("="*60)
    print("🤖 CHÀO MỪNG ĐẾN VỚI TRỢ LÝ ẢO MARKET-SENSE")
    print("Gõ 'exit' hoặc 'quit' để thoát.")
    print("="*60)
    
    while True:
        query = input("\n👤 Khách hàng VIP: ")
        if query.lower() in ['exit', 'quit']:
            break
            
        answer = ask_market_assistant(query)
        
        print("\n💼 MARKET Assistant:")
        print("-" * 40)
        print(answer)
        print("-" * 40)