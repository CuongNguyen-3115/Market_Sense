import { apiClient } from '../api/apiClient.js';

document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('rag-query-form');
  const chatContainer = document.getElementById('chat-container');
  
  // 1. LOGIC ĐÓNG MỞ SIDEBAR
  const toggleBtn = document.getElementById('toggle-sidebar-btn');
  const sidebar = document.querySelector('.chat-sidebar');
  if (toggleBtn && sidebar) {
    toggleBtn.addEventListener('click', () => {
      sidebar.classList.toggle('collapsed');
    });
  }

  if (form) {
    form.addEventListener('submit', async (e) => {
      e.preventDefault(); 
      
      const queryInput = document.getElementById('user-query');
      const topKInput = document.getElementById('top-k');
      const top_k = parseInt(topKInput.value, 10) || 3; 
      
      const submitBtn = document.getElementById('send-btn');
      const iconSend = document.getElementById('icon-send');
      const iconStop = document.getElementById('icon-stop');
      
      const query = queryInput.value.trim();
      if (!query) return;

      // Xóa câu chào mặc định nếu đây là câu hỏi đầu tiên
      const welcomeMsg = document.getElementById('welcome-message');
      if (welcomeMsg) welcomeMsg.remove();

      // Hiển thị câu hỏi của User
      appendMessage('user', query);
      queryInput.value = ''; 
      
      // CHUYỂN TRẠNG THÁI NÚT GỬI -> ĐANG LOAD
      submitBtn.disabled = true;
      submitBtn.classList.add('loading');
      iconSend.style.display = 'none';
      iconStop.style.display = 'block';
      
      const loadingId = appendMessage('ai', '<span class="typing-indicator" style="color: var(--text-secondary); font-style: italic;">Đang suy nghĩ...</span>');
      
      try {
        const response = await apiClient.queryRAG(query, top_k);
        removeMessage(loadingId);
        appendMessage('ai', response.answer, response.sources);
      } catch (error) {
        removeMessage(loadingId);
        appendMessage('ai', 'Xin lỗi, có lỗi xảy ra khi kết nối tới LLM API. Vui lòng thử lại sau.');
      } finally {
        // TRẢ LẠI TRẠNG THÁI NÚT GỬI BÌNH THƯỜNG
        submitBtn.disabled = false;
        submitBtn.classList.remove('loading');
        iconSend.style.display = 'block';
        iconStop.style.display = 'none';
        queryInput.focus();
      }
    });
  }
});

// --- Hàm tạo bong bóng Chat chuẩn CSS Minimalist ---
function appendMessage(senderType, content, sources = null) {
  const chatContainer = document.getElementById('chat-container');
  if (!chatContainer) return null;

  const messageDiv = document.createElement('div');
  const messageId = 'msg-' + Date.now();
  messageDiv.id = messageId;
  
  // Chuyển \n thành <br> để giữ định dạng văn bản
  const formattedContent = content.replace(/\n/g, '<br>');

  if (senderType === 'user') {
    messageDiv.className = 'chat-message user-message';
    messageDiv.innerHTML = `
      <div class="message-bubble">
        <p style="margin: 0; font-size: 0.95rem;">${formattedContent}</p>
      </div>
    `;
  } else {
    messageDiv.className = 'chat-message ai-message';
    
    // Render nguồn (Sources) dạng thẻ Pill
    let sourcesHtml = '';
    if (sources && Array.isArray(sources) && sources.length > 0) {
      const pillsHtml = sources.map((s, index) => `
        <a href="${s.url}" class="source-pill" target="_blank" rel="noopener noreferrer">
          <span class="source-index">${index + 1}</span> ${s.title}
        </a>
      `).join('');
      sourcesHtml = `<div class="message-sources" style="margin-top: 16px;"><span class="source-label">Nguồn:</span><div class="source-list">${pillsHtml}</div></div>`;
    }

    // Avatar có thể đổi thành SVG icon cho giống Gemini
    messageDiv.innerHTML = `
      <div class="message-avatar" style="background: transparent; border: 1px solid var(--border-color); color: var(--text-primary);">
         <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
      </div>
      <div class="message-bubble">
        <p style="margin: 0; font-size: 0.95rem; line-height: 1.6;">${formattedContent}</p>
        ${sourcesHtml}
      </div>
    `;
  }

  chatContainer.appendChild(messageDiv);
  chatContainer.scrollTo({ top: chatContainer.scrollHeight, behavior: 'smooth' });
  return messageId;
}

function removeMessage(id) {
  const el = document.getElementById(id);
  if (el) el.remove();
}