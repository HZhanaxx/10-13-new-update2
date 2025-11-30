<template>
  <div class="page-container">
    <Sidebar />
    
    <div class="main-content">
      <header class="page-header">
        <div>
          <h1>👋 欢迎回来, {{ authStore.userName }}</h1>
          <p class="subtitle">这里是您的案件概览</p>
        </div>
        <div class="header-actions">
          <button class="btn btn-secondary" @click="startQuestionnaire" :disabled="isStartingQuestionnaire">
            <span class="icon">📋</span> 
            {{ isStartingQuestionnaire ? '启动中...' : '智能问卷咨询' }}
          </button>
          <button class="btn btn-primary" @click="$router.push('/cases/new')">
            <span class="icon">＋</span> 新建案件
          </button>
        </div>
      </header>
      
      <!-- Questionnaire Modal -->
      <div v-if="showQuestionnaireModal" class="modal-overlay" @click.self="closeQuestionnaireModal">
        <div class="modal-content questionnaire-modal">
          <div class="modal-header">
            <h2>🚗 交通事故法律咨询</h2>
            <button class="close-btn" @click="closeQuestionnaireModal">×</button>
          </div>
          <div class="modal-body">
            <p>本问卷将帮助您：</p>
            <ul class="feature-list">
              <li>📝 系统化收集事故信息</li>
              <li>🤖 AI智能分析您的案件</li>
              <li>📄 自动生成案件档案</li>
              <li>⚖️ 匹配专业律师（可选）</li>
            </ul>
            <div class="time-estimate">
              <span class="icon">⏱️</span>
              预计用时：10-15分钟
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-outline" @click="closeQuestionnaireModal">取消</button>
            <button class="btn btn-primary" @click="launchQuestionnaire" :disabled="isLaunching">
              {{ isLaunching ? '正在准备...' : '开始问卷' }}
            </button>
          </div>
        </div>
      </div>

      <div v-if="isLoading" class="loading-container">
        <div class="spinner"></div>
      </div>

      <div v-else-if="cases.length > 0" class="cases-grid">
        <transition-group name="list">
          <div 
            v-for="c in cases" 
            :key="c.case_uuid" 
            class="glass-card case-card"
            @click="$router.push(`/case/${c.case_uuid}`)"
          >
            <div class="card-header">
              <span class="category-badge">{{ c.case_category }}</span>
              <span :class="['status-dot', c.case_status]"></span>
            </div>
            <h3>{{ c.title }}</h3>
            <p class="description">{{ c.description }}</p>
            
            <div class="card-footer">
              <div class="meta">
                <span>💰 ¥{{ c.budget_cny || '面议' }}</span>
                <span>📅 {{ formatDate(c.created_at) }}</span>
              </div>
            </div>
          </div>
        </transition-group>
      </div>

      <div v-else class="empty-state glass-card">
        <div class="empty-icon">📭</div>
        <h3>暂无案件</h3>
        <p>您还没有发布任何法律咨询或案件。</p>
        <button class="btn btn-primary" @click="$router.push('/cases/new')">立即发布</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import apiClient from '@/utils/api'
import Sidebar from '@/components/Sidebar.vue'

const router = useRouter()
const authStore = useAuthStore()
const cases = ref([])
const isLoading = ref(true)

// Questionnaire state
const showQuestionnaireModal = ref(false)
const isStartingQuestionnaire = ref(false)
const isLaunching = ref(false)

const loadCases = async () => {
  try {
    const res = await apiClient.get('/cases/my-cases')
    cases.value = res.data.cases || []
  } catch (e) {
    console.error(e)
  } finally {
    isLoading.value = false
  }
}

const formatDate = (d) => new Date(d).toLocaleDateString('zh-CN')

// Questionnaire functions
const startQuestionnaire = () => {
  showQuestionnaireModal.value = true
}

const closeQuestionnaireModal = () => {
  showQuestionnaireModal.value = false
}

const launchQuestionnaire = async () => {
  isLaunching.value = true
  
  try {
    // Call the new LangGraph workflow API (no more n8n)
    const res = await apiClient.post('/workflow/questionnaire/start', {
      template_type: 1  // Traffic accident template
    })
    
    if (res.data.success) {
      // Store session info - simplified, no JWT token needed
      const sessionData = {
        sessionId: res.data.session_id,
        status: res.data.status,
        // Store initial question data if available
        question: res.data.question,
        partInfo: res.data.part_info,
        progress: res.data.progress
      }
      
      // Store in sessionStorage for the questionnaire page
      sessionStorage.setItem('questionnaire_session', JSON.stringify(sessionData))
      
      // Navigate to questionnaire page
      closeQuestionnaireModal()
      router.push(`/questionnaire/${res.data.session_id}`)
    }
  } catch (error) {
    console.error('Failed to start questionnaire:', error)
    alert('启动问卷失败，请稍后重试')
  } finally {
    isLaunching.value = false
  }
}

onMounted(loadCases)
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 40px; }
.page-header h1 { font-size: 28px; color: #2d3748; margin-bottom: 4px; }
.subtitle { color: #718096; font-size: 14px; }

.header-actions { display: flex; gap: 12px; }

.btn-secondary { 
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  padding: 12px 20px;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
  display: flex;
  align-items: center;
  gap: 8px;
}
.btn-secondary:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4); }
.btn-secondary:disabled { opacity: 0.6; cursor: not-allowed; transform: none; }

.cases-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 24px; }

.case-card { padding: 24px; display: flex; flex-direction: column; cursor: pointer; transition: all 0.3s; height: 100%; }
.case-card:hover { transform: translateY(-5px); box-shadow: 0 12px 24px rgba(0,0,0,0.1); }

.card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.category-badge { background: #ebf4ff; color: #4299e1; font-size: 11px; padding: 4px 10px; border-radius: 20px; font-weight: 600; }
.status-dot { width: 10px; height: 10px; border-radius: 50%; background: #cbd5e0; }
.status-dot.pending { background: #ecc94b; }
.status-dot.in_progress { background: #4299e1; box-shadow: 0 0 0 3px rgba(66, 153, 225, 0.2); }
.status-dot.completed { background: #48bb78; }

h3 { font-size: 18px; font-weight: 700; color: #2d3748; margin-bottom: 12px; line-height: 1.4; }
.description { font-size: 14px; color: #718096; line-height: 1.6; flex: 1; margin-bottom: 20px; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }

.card-footer { border-top: 1px solid rgba(0,0,0,0.05); padding-top: 16px; font-size: 13px; color: #a0aec0; }
.meta { display: flex; justify-content: space-between; }

.empty-state { text-align: center; padding: 60px; }
.empty-icon { font-size: 48px; margin-bottom: 16px; }
.empty-state p { margin-bottom: 24px; color: #718096; }

.spinner { border: 3px solid #f3f3f3; border-top: 3px solid #667eea; border-radius: 50%; width: 30px; height: 30px; animation: spin 1s linear infinite; margin: 0 auto; }
@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }

/* Modal Styles */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(4px);
}

.modal-content {
  background: white;
  border-radius: 16px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.2);
  max-width: 500px;
  width: 90%;
  overflow: hidden;
  animation: modalSlideIn 0.3s ease;
}

@keyframes modalSlideIn {
  from { transform: translateY(-20px); opacity: 0; }
  to { transform: translateY(0); opacity: 1; }
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid #e2e8f0;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.modal-header h2 {
  margin: 0;
  font-size: 20px;
  color: white;
}

.close-btn {
  background: rgba(255,255,255,0.2);
  border: none;
  color: white;
  font-size: 24px;
  cursor: pointer;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s;
}
.close-btn:hover { background: rgba(255,255,255,0.3); }

.modal-body {
  padding: 24px;
}

.modal-body p {
  margin: 0 0 16px;
  color: #4a5568;
  font-size: 16px;
}

.feature-list {
  list-style: none;
  padding: 0;
  margin: 0 0 20px;
}

.feature-list li {
  padding: 10px 0;
  color: #4a5568;
  border-bottom: 1px solid #f0f0f0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.feature-list li:last-child {
  border-bottom: none;
}

.time-estimate {
  background: #f7fafc;
  padding: 12px 16px;
  border-radius: 8px;
  color: #718096;
  display: flex;
  align-items: center;
  gap: 8px;
}

.modal-footer {
  padding: 16px 24px;
  border-top: 1px solid #e2e8f0;
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  background: #f9fafb;
}

.btn-outline {
  background: white;
  border: 1px solid #e2e8f0;
  color: #4a5568;
  padding: 10px 20px;
  border-radius: 8px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}
.btn-outline:hover { background: #f7fafc; border-color: #cbd5e0; }
</style>
