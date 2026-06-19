# Evaluation Module

Module kiểm định chất lượng RAG theo hướng LLM-as-a-Judge.

## Files
- `ground_truth.json`: tập câu hỏi kiểm thử.
- `rag_evaluator.py`: chấm điểm theo 3 metric.
- `run_evaluation.py`: orchestrator chạy toàn bộ vòng đánh giá và xuất báo cáo.

## Metrics
- `context_relevance`
- `groundedness`
- `answer_relevance`

## Run
```bash
python evaluation/run_evaluation.py
```

## Output
- File CSV báo cáo tại `evaluation/eval_results/`.

## Lưu ý vận hành
- Cần vector DB đã được build và `GROQ_API_KEY` hợp lệ.
