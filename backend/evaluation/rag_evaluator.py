import os
import json
import logging
from dotenv import load_dotenv
from groq import Groq

# Cấu hình log
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    logger.error("❌ Không tìm thấy GROQ_API_KEY.")
    exit(1)

# Sử dụng model thông minh nhất (70B) để làm giám khảo
JUDGE_MODEL = "llama-3.3-70b-versatile"
client = Groq(api_key=GROQ_API_KEY)

def evaluate_rag_turn(query, context, generated_answer):
    """
    Hàm LLM-as-a-Judge: Đánh giá câu trả lời RAG dựa trên 3 tiêu chí cốt lõi.
    """
    logger.info(f"⚖️ Đang chấm điểm câu hỏi: '{query}'...")

    system_prompt = """Bạn là một Chuyên gia Kiểm định AI (AI Evaluator).
Nhiệm vụ của bạn là chấm điểm một hệ thống Trợ lý Tài chính (RAG System).
Bạn sẽ được cung cấp: [CÂU HỎI], [CONTEXT - Dữ liệu tìm được], và [CÂU TRẢ LỜI CỦA AI].

Hãy chấm 3 chỉ số sau trên thang điểm từ 0.0 đến 1.0 (1.0 là hoàn hảo):
1. context_relevance_score: Context tìm được có liên quan và chứa thông tin để trả lời Câu hỏi không? (0.0 nếu Context hoàn toàn lạc đề).
2. groundedness_score: Câu trả lời có bám sát 100% vào Context không? (0.0 nếu AI bịa đặt thông tin không có trong Context).
3. answer_relevance_score: Câu trả lời có giải quyết trực tiếp và trọn vẹn Câu hỏi không? (0.0 nếu trả lời vòng vo, né tránh không hợp lý).

BẮT BUỘC TRẢ VỀ ĐỊNH DẠNG JSON.
{
    "context_relevance_score": <float>,
    "groundedness_score": <float>,
    "answer_relevance_score": <float>,
    "evaluation_reason": "<Giải thích ngắn gọn tại sao cho điểm số này>"
}"""

    user_prompt = f"""
[CÂU HỎI CỦA KHÁCH HÀNG]
{query}

[CONTEXT - DỮ LIỆU CHUẨN BỊ CHO AI]
{context}

[CÂU TRẢ LỜI CỦA AI]
{generated_answer}
"""

    try:
        response = client.chat.completions.create(
            model=JUDGE_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.0, # Điểm số cần sự ổn định tuyệt đối
            max_tokens=200,
            response_format={"type": "json_object"}
        )
        
        result_json = json.loads(response.choices[0].message.content)
        return result_json
    
    except Exception as e:
        logger.error(f"❌ Lỗi khi chấm điểm: {str(e)}")
        return None

# ==========================================
# TEST THỬ HỆ THỐNG GIÁM KHẢO
# ==========================================
if __name__ == "__main__":
    # Giả lập một trường hợp tồi tệ (Ảo giác + Lấy sai Context)
    test_query = "FED vừa tăng lãi suất, tôi có nên bán chứng khoán không?"
    
    # ChromaDB lấy nhầm tin về heo hơi (Context Relevance = 0)
    fake_context = "- Bản tin 1: Giá heo hơi hôm nay giảm mạnh tại miền Bắc. \n- Bản tin 2: Mưa lớn gây ngập lụt tại Hà Nội."
    
    # AI Trợ lý tự bịa ra câu trả lời thay vì nói "Không biết" (Groundedness = 0)
    bad_answer = "Chào Quý khách, FED vừa tăng lãi suất lên 5.5% đêm qua. Đây là tin rất xấu, Quý khách nên bán sạch danh mục chứng khoán ngay lập tức để bảo toàn vốn."

    print("="*50)
    print("ĐANG CHẠY MÔ PHỎNG ĐÁNH GIÁ (MẪU LỖI)...")
    eval_result = evaluate_rag_turn(test_query, fake_context, bad_answer)
    
    if eval_result:
        print(json.dumps(eval_result, indent=4, ensure_ascii=False))