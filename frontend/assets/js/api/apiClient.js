/* =========================================
   API CLIENT - Quản lý giao tiếp với Backend
   ========================================= */

   const BASE_URL = 'http://localhost:8000';

   /**
    * Hàm gọi API chung, tự động bắt lỗi và parse JSON
    */
   async function fetchAPI(endpoint, options = {}) {
     try {
       const response = await fetch(`${BASE_URL}${endpoint}`, {
         headers: {
           'Content-Type': 'application/json',
         },
         ...options,
       });
   
       if (!response.ok) {
         throw new Error(`HTTP error! status: ${response.status}`);
       }
   
       return await response.json();
     } catch (error) {
       console.error(`[API Call Failed] ${endpoint}`, error);
       throw error; // Ném lỗi ra để các hàm gọi xử lý
     }
   }
   
   /* =========================================
      CÁC HÀM GỌI API THEO CONTRACT ĐÃ CHỐT
      ========================================= */
   
   export const apiClient = {
     /**
      * GET /api/health
      * Trả về trạng thái các core services (Kafka, Mongo, Chroma, LLM)
      */
     async getHealth() {
       try {
         return await fetchAPI('/api/health');
       } catch (e) {
         // Trả về trạng thái lỗi nếu Backend sập
         return {
           kafka: 'error',
           mongodb: 'error',
           chromadb: 'error',
           llm_api: 'error'
         };
       }
     },
   
     /**
      * GET /api/timeseries?start_date={...}&end_date={...}
      * Lấy dữ liệu biểu đồ sentiment
      */
     async getTimeSeries(startDate, endDate) {
       try {
         return await fetchAPI(`/api/timeseries?start_date=${startDate}&end_date=${endDate}`);
       } catch (e) {
         return []; // Trả về mảng rỗng để Chart không bị crash
       }
     },
   
     /**
      * GET /api/sentiment/summary?start_date={...}&end_date={...}
      * Lấy dữ liệu 5 thẻ KPI
      */
     async getSentimentSummary(startDate, endDate) {
       try {
         return await fetchAPI(`/api/sentiment/summary?start_date=${startDate}&end_date=${endDate}`);
       } catch (e) {
         // Trả về object rỗng mặc định để UI render trạng thái "Chưa có dữ liệu"
         return {
           total_news: 0,
           positive_ratio: 0,
           negative_ratio: 0,
           neutral_ratio: 0,
           irrelevant_ratio: 0, // Đã bổ sung trường này để đồng bộ với UI mới
           momentum: "Lỗi kết nối",
           trend_label: "Lỗi kết nối"
         };
       }
     },
   
     /**
      * GET /api/news/recent?limit={limit}
      * Lấy danh sách tin tức mới nhất đã qua xử lý sentiment
      */
     async getRecentNews(limit = 20) {
       try {
         return await fetchAPI(`/api/news/recent?limit=${limit}`);
       } catch (e) {
         return []; // Không có kết nối thì danh sách tin tức trống
       }
     },
   
     /**
      * POST /api/rag/query
      * Gửi câu hỏi cho Trợ lý AI và nhận câu trả lời kèm nguồn
      */
     async queryRAG(query, top_k) {
       // Không dùng try-catch ở đây để ném thẳng lỗi ra cho file assistant.js 
       // Từ đó UI mới hiển thị được câu "Xin lỗi, có lỗi xảy ra..."
       return await fetchAPI('/api/rag/query', {
         method: 'POST',
         body: JSON.stringify({ message: query, top_k: top_k }),
       });
     }
   };