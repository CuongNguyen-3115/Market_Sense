import os
import json
import time
import pandas as pd
from datetime import datetime
import logging

# Import hệ thống RAG và Giám khảo (Đảm bảo chạy lệnh từ thư mục gốc của dự án)
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ai_engine.rag_assistant import ask_shb_assistant
from evaluation.rag_evaluator import evaluate_rag_turn

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def load_ground_truth():
    filepath = os.path.join(os.path.dirname(__file__), 'ground_truth.json')
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def run_eval_loop():
    logger.info("🚀 BẮT ĐẦU CHẠY KIỂM ĐỊNH RAG TOÀN DIỆN (LLM-as-a-Judge)...")
    dataset = load_ground_truth()
    
    results = []
    
    for idx, item in enumerate(dataset):
        logger.info("-" * 50)
        logger.info(f"Đang test [{idx+1}/{len(dataset)}]: {item['id']} - {item['category']}")
        
        query = item['query']
        
        # 1. Gọi RAG sinh câu trả lời
        logger.info("-> Gọi RAG truy xuất và trả lời...")
        answer, context = ask_shb_assistant(query, top_k=3)
        
        if not context:
            logger.warning("-> Không lấy được Context. Bỏ qua chấm điểm.")
            continue
            
        # 2. Gọi Giám khảo chấm điểm
        logger.info("-> Đưa cho AI Evaluator chấm điểm...")
        eval_scores = evaluate_rag_turn(query, context, answer)
        
        if eval_scores:
            results.append({
                "id": item['id'],
                "category": item['category'],
                "query": query,
                "context_relevance": eval_scores.get("context_relevance_score", 0.0),
                "groundedness": eval_scores.get("groundedness_score", 0.0),
                "answer_relevance": eval_scores.get("answer_relevance_score", 0.0),
                "eval_reason": eval_scores.get("evaluation_reason", ""),
                "expected_behavior": item["expected_behavior"],
                "actual_answer": answer
            })
            logger.info(f"✅ Điểm số: Context={eval_scores.get('context_relevance_score')} | Groundedness={eval_scores.get('groundedness_score')} | Answer={eval_scores.get('answer_relevance_score')}")
        else:
            logger.error("-> Lỗi chấm điểm, trả về null.")
        
        # Nhịp nghỉ để bảo vệ Rate Limit của Groq (rất quan trọng khi gọi API liên tục)
        time.sleep(4)

    # 3. Tổng hợp và xuất Báo cáo
    logger.info("\n" + "="*50)
    logger.info("📊 TỔNG KẾT BÁO CÁO KIỂM ĐỊNH")
    
    df = pd.DataFrame(results)
    
    # Tính điểm trung bình toàn hệ thống
    avg_context = df['context_relevance'].mean()
    avg_groundedness = df['groundedness'].mean()
    avg_answer = df['answer_relevance'].mean()
    
    logger.info(f"Điểm Trung Bình (Toàn hệ thống):")
    logger.info(f"- Context Relevance (Độ chuẩn vectorDB): {avg_context:.2f}/1.0")
    logger.info(f"- Groundedness (Chống ảo giác): {avg_groundedness:.2f}/1.0")
    logger.info(f"- Answer Relevance (Độ thỏa mãn): {avg_answer:.2f}/1.0")
    
    # Lưu ra file CSV
    out_dir = os.path.join(os.path.dirname(__file__), 'eval_results')
    os.makedirs(out_dir, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    out_file = os.path.join(out_dir, f'rag_report_{timestamp}.csv')
    
    df.to_csv(out_file, index=False, encoding='utf-8-sig')
    logger.info(f"📁 Đã lưu file báo cáo chi tiết tại: {out_file}")
    logger.info("="*50)

if __name__ == "__main__":
    run_eval_loop()