import { apiClient } from '../api/apiClient.js';

let chartInstance = null;

document.addEventListener('DOMContentLoaded', () => {
    const endDateInput = document.getElementById('end-date');
    const startDateInput = document.getElementById('start-date');
    
    const today = new Date();
    const thirtyDaysAgo = new Date();
    thirtyDaysAgo.setDate(today.getDate() - 30);
    
    if (endDateInput && startDateInput) {
      endDateInput.value = today.toISOString().split('T')[0];
      startDateInput.value = thirtyDaysAgo.toISOString().split('T')[0];
    }
  
    initDashboard();
    setupEventListeners();
});

async function initDashboard() {
    const startDateInput = document.getElementById('start-date');
    const endDateInput = document.getElementById('end-date');
    const startDate = startDateInput ? startDateInput.value : '';
    const endDate = endDateInput ? endDateInput.value : '';
  
    const [healthStatus, summaryData, recentNews, timeSeriesData] = await Promise.all([
      apiClient.getHealth(),
      apiClient.getSentimentSummary(startDate, endDate),
      apiClient.getRecentNews(5),
      apiClient.getTimeSeries(startDate, endDate)
    ]);
  
    renderHealthStatus(healthStatus);
    renderKPIs(summaryData);
    renderNews(recentNews);
    
    if (timeSeriesData && timeSeriesData.length > 0) {
      renderChart(timeSeriesData);
    }
}

function setupEventListeners() {
    const refreshBtn = document.querySelector('.btn-primary'); // Trỏ đúng class nút mới
  
    if (refreshBtn) {
      refreshBtn.addEventListener('click', async () => {
        const originalText = refreshBtn.textContent;
        refreshBtn.textContent = 'Đang tải...';
        refreshBtn.disabled = true;
        
        const startDate = document.getElementById('start-date').value;
        const endDate = document.getElementById('end-date').value;
        
        const [summaryData, timeSeriesData] = await Promise.all([
          apiClient.getSentimentSummary(startDate, endDate),
          apiClient.getTimeSeries(startDate, endDate)
        ]);
        
        renderKPIs(summaryData);
        
        if (timeSeriesData && timeSeriesData.length > 0) {
          renderChart(timeSeriesData);
        } else {
          if (chartInstance) chartInstance.destroy(); 
        }
        
        refreshBtn.textContent = originalText;
        refreshBtn.disabled = false;
      });
    }
}

// --- CÁC HÀM RENDER GIAO DIỆN MỚI ---

function renderHealthStatus(status) {
  const lis = document.querySelectorAll('.status-list li');
  if (!lis || lis.length < 4) return;

  // Hàm hỗ trợ set trạng thái
  const updateLi = (li, name, val) => {
    li.className = ''; // Xóa class cũ
    if (val === 'ok') li.classList.add('active'); // Hiện chấm xanh
    else li.classList.add('error'); // Hiện chấm đỏ
    li.innerHTML = `${name}: <strong>${val}</strong>`;
  };

  updateLi(lis[0], 'Kafka', status.kafka);
  updateLi(lis[1], 'MongoDB', status.mongodb);
  updateLi(lis[2], 'ChromaDB', status.chromadb);
  updateLi(lis[3], 'LLM', status.llm_api);
}

function renderKPIs(data) {
    const kpiValues = document.querySelectorAll('.kpi-card .kpi-value');
  
    if (!data || data.total_news === 0) {
      if (kpiValues.length >= 4) {
          kpiValues[0].textContent = '0';
          kpiValues[1].textContent = '--%';
          kpiValues[2].textContent = '--%';
          kpiValues[3].textContent = '--%';
      }
      return;
    }
  
    // Thay đoạn cũ bằng đoạn này
    if (kpiValues.length >= 4) {
    kpiValues[0].textContent = data.total_news.toLocaleString();
    kpiValues[1].textContent = `${data.positive_ratio}%`;
    kpiValues[2].textContent = `${data.negative_ratio}%`;
    kpiValues[3].textContent = `${data.neutral_ratio}%`;
    
    // Thêm dòng này để cập nhật thẻ mới
    const irrValue = document.getElementById('kpi-irrelevant');
    if (irrValue) irrValue.textContent = `${data.irrelevant_ratio}%`;
    }
}

function renderNews(newsList) {
  const ul = document.querySelector('.news-list');
  if (!ul) return;

  ul.innerHTML = ''; // Xóa tin tức mẫu
  
  newsList.forEach(news => {
    const li = document.createElement('li');
    li.className = 'news-item';
    
    // Map sentiment ra đúng class badge trong file CSS mới
    let badgeClass = 'badge-neutral';
    if (news.sentiment === 'Positive') badgeClass = 'badge-positive';
    if (news.sentiment === 'Negative') badgeClass = 'badge-negative';

    li.innerHTML = `
      <article>
          <div class="news-meta">
              <span class="news-source">${news.source}</span>
              <span class="news-time">${news.time}</span>
          </div>
          <h4>${news.title}</h4>
          <div class="news-footer">
              <span class="badge ${badgeClass}">${news.sentiment}</span>
              <a href="${news.url}" target="_blank" rel="noopener noreferrer" class="news-link">Đọc tiếp &rarr;</a>
          </div>
      </article>
    `;
    ul.appendChild(li);
  });
}

function renderChart(data) {
    const ctx = document.getElementById('sentimentChart');
    if (!ctx) return;
    if (chartInstance) chartInstance.destroy();

    const startDate = document.getElementById('start-date').value;
    const endDate = document.getElementById('end-date').value;
  
    const fullDateRange = generateDateRange(startDate, endDate);

    const dailyIndex = fullDateRange.map(date => {
      const found = data.find(item => item.date === date);
      return found ? found.daily_index : null;
    });
    const smaShort = fullDateRange.map(date => {
      const found = data.find(item => item.date === date);
      return found ? found.sma_short : null;
    });
    const smaLong = fullDateRange.map(date => {
      const found = data.find(item => item.date === date);
      return found ? found.sma_long : null;
    });
  
    chartInstance = new Chart(ctx, {
      type: 'line',
      data: {
        labels: fullDateRange,
        datasets: [
          {
            label: 'Daily Index',
            data: dailyIndex,
            borderColor: '#6366f1', // Đổi sang màu Tím Indigo
            backgroundColor: 'rgba(99, 102, 241, 0.1)',
            borderWidth: 2,
            pointRadius: 4,
            pointBackgroundColor: '#ffffff', // Lõi điểm màu trắng
            fill: true,
            tension: 0.4 // Tăng độ cong cho mềm mại hơn
          },
          {
            label: 'SMA Short',
            data: smaShort,
            borderColor: '#10b981', // Xanh lục
            borderWidth: 2,
            borderDash: [5, 5],
            pointRadius: 0,
            fill: false,
            tension: 0.4
          },
          {
            label: 'SMA Long',
            data: smaLong,
            borderColor: '#f59e0b', // Đổi sang màu cam cho đỡ gắt hơn màu đỏ cũ
            borderWidth: 2,
            borderDash: [2, 2],
            pointRadius: 0,
            fill: false,
            tension: 0.4
          }
        ]
      },
      // Thay thế cụm options hiện tại trong dashboard.js bằng đoạn này
      options: {
        responsive: true,
        maintainAspectRatio: false, // Rất quan trọng để biểu đồ tuân theo CSS flexbox
        interaction: {
          mode: 'index',
          intersect: false,
        },
        plugins: {
          legend: {
            position: 'top',
            align: 'end', // Đẩy chú giải sang góc phải cho thoáng
            labels: {
              usePointStyle: true, // Biến hình chữ nhật thành chấm tròn
              boxWidth: 8,
              padding: 20,
              color: '#475569', 
              font: { family: "'Inter', sans-serif", size: 12 }
            }
          }
        },
        scales: {
          x: {
            grid: { display: false }, 
            ticks: { 
              color: '#64748b',
              maxRotation: 0, // Bắt buộc nhãn phải nằm ngang, không được nghiêng
              autoSkip: true, // Tự động ẩn bớt ngày nếu màn hình quá chật
              maxTicksLimit: 12, // Chỉ hiện tối đa 12 mốc thời gian cho đỡ rối
              callback: function(value, index, values) {
                // Cắt chuỗi '2026-05-15' thành '15/05'
                const dateStr = this.getLabelForValue(value);
                if (dateStr) {
                  const parts = dateStr.split('-');
                  if(parts.length === 3) return `${parts[2]}/${parts[1]}`;
                }
                return dateStr;
              }
            }
          },
          y: {
            border: { display: false }, 
            grid: { 
              color: '#f1f5f9', 
              drawTicks: false 
            },
            ticks: { 
              color: '#64748b',
              padding: 10 // Đẩy nhẹ số liệu trục Y ra xa biểu đồ một chút
            }
          }
        }
      }
    });
} 

function generateDateRange(startDateStr, endDateStr) {
    const start = new Date(startDateStr);
    const end = new Date(endDateStr);
    const dateArray = [];
    let currentDate = new Date(start);
    
    while (currentDate <= end) {
      dateArray.push(currentDate.toISOString().split('T')[0]);
      currentDate.setDate(currentDate.getDate() + 1);
    }
    return dateArray;
}