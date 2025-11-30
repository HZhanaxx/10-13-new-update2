<template>
  <div class="dashboard-container">
    <Sidebar />
    
    <div class="main-content">
      <header class="dashboard-header">
        <button class="btn btn-secondary" @click="$router.go(-1)">
          ← 返回
        </button>
        <h1>案件详情</h1>
      </header>

      <!-- Loading state -->
      <div v-if="isLoading" class="loading-container">
        <div class="loading"></div>
        <p>加载中...</p>
      </div>

      <!-- Case Detail Content -->
      <div v-else-if="caseData" class="case-detail-content">
        <!-- Case Header -->
        <div class="case-header-card">
          <div class="case-title-row">
            <h2>{{ caseData.title }}</h2>
            <span :class="['status-badge', `status-${caseData.case_status}`]">
              {{ getStatusText(caseData.case_status) }}
            </span>
          </div>
          <div class="case-meta">
            <span>📁 {{ caseData.case_category }}</span>
            <span class="budget">💰 ¥{{ caseData.budget_cny }}</span>
            <span>📅 创建于 {{ formatDate(caseData.created_at) }}</span>
            <span v-if="caseData.location">📍 {{ caseData.location }}</span>
          </div>
        </div>

        <!-- Main Info -->
        <div class="detail-section">
          <h3>案件描述</h3>
          <p class="case-description">{{ caseData.description }}</p>
        </div>

        <!-- Additional Details -->
        <div v-if="caseData.requirements" class="detail-section">
          <h3>案件要求</h3>
          <p>{{ caseData.requirements }}</p>
        </div>

        <!-- Client Info (for professionals) -->
        <div v-if="authStore.userRole === 'professional' && caseData.client_info" class="detail-section">
          <h3>客户信息</h3>
          <div class="info-grid">
            <div class="info-item">
              <span class="label">客户姓名:</span>
              <span class="value">{{ caseData.client_info.name }}</span>
            </div>
            <div class="info-item">
              <span class="label">联系电话:</span>
              <span class="value">{{ caseData.client_info.phone }}</span>
            </div>
            <div v-if="caseData.client_info.email" class="info-item">
              <span class="label">邮箱:</span>
              <span class="value">{{ caseData.client_info.email }}</span>
            </div>
          </div>
        </div>

        <!-- Professional Info (for clients) -->
        <div v-if="authStore.userRole === 'user' && caseData.professional_info" class="detail-section">
          <h3>负责专业人员</h3>
          <div class="professional-card">
            <div class="professional-header">
              <h4>{{ caseData.professional_info.name }}</h4>
              <span class="badge">{{ caseData.professional_info.specialization }}</span>
            </div>
            <p v-if="caseData.professional_info.organization">
              🏢 {{ caseData.professional_info.organization }}
            </p>
            <p v-if="caseData.professional_info.years_experience">
              📊 从业 {{ caseData.professional_info.years_experience }} 年
            </p>
          </div>
        </div>

        <!-- Timeline -->
        <div v-if="timeline.length > 0" class="detail-section">
          <h3>案件进度</h3>
          <div class="timeline">
            <div 
              v-for="(item, index) in timeline" 
              :key="index" 
              class="timeline-item"
            >
              <div class="timeline-marker"></div>
              <div class="timeline-content">
                <div class="timeline-time">{{ formatDateTime(item.timestamp) }}</div>
                <div class="timeline-title">{{ item.title }}</div>
                <div v-if="item.description" class="timeline-desc">{{ item.description }}</div>
              </div>
            </div>
          </div>
        </div>

        <!-- Actions -->
        <div class="action-section">
          <!-- Client Actions -->
          <template v-if="authStore.userRole === 'user'">
            <button 
              v-if="caseData.case_status === 'pending'"
              class="btn btn-danger" 
              @click="cancelCase"
            >
              取消案件
            </button>
            <button 
              v-if="caseData.case_status === 'completed'"
              class="btn btn-primary" 
              @click="showRatingModal = true"
            >
              评价服务
            </button>
          </template>

          <!-- Professional Actions -->
          <template v-if="authStore.userRole === 'professional'">
            <button 
              v-if="caseData.case_status === 'pending'"
              class="btn btn-primary" 
              @click="acceptCase"
            >
              接受案件
            </button>
            <button 
              v-if="caseData.case_status === 'in_progress'"
              class="btn btn-success" 
              @click="completeCase"
            >
              标记完成
            </button>
          </template>
        </div>
      </div>

      <!-- Error state -->
      <div v-else class="error-state">
        <h3>无法加载案件详情</h3>
        <p>该案件可能不存在或您没有权限查看</p>
        <button class="btn btn-primary" @click="$router.go(-1)">
          返回
        </button>
      </div>
    </div>

    <!-- Rating Modal -->
    <Modal v-if="showRatingModal" @close="showRatingModal = false">
      <template #header>
        <h2>评价服务</h2>
      </template>
      <template #body>
        <form @submit.prevent="submitRating" class="rating-form">
          <div class="form-group">
            <label>服务评分*</label>
            <div class="star-rating">
              <span 
                v-for="star in 5" 
                :key="star"
                class="star"
                :class="{ active: star <= rating }"
                @click="rating = star"
              >
                ★
              </span>
            </div>
          </div>
          <div class="form-group">
            <label>评价内容</label>
            <textarea
              v-model="ratingComment"
              class="input"
              rows="4"
              placeholder="请分享您的服务体验..."
            ></textarea>
          </div>
          <div class="modal-actions">
            <button type="button" class="btn btn-secondary" @click="showRatingModal = false">
              取消
            </button>
            <button type="submit" class="btn btn-primary" :disabled="rating === 0">
              提交评价
            </button>
          </div>
        </form>
      </template>
    </Modal>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import Sidebar from '@/components/Sidebar.vue'
import Modal from '@/components/Modal.vue'
import api from '@/utils/api'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

// State
const isLoading = ref(false)
const caseData = ref(null)
const timeline = ref([])
const showRatingModal = ref(false)
const rating = ref(0)
const ratingComment = ref('')

// Methods
const loadCaseDetail = async () => {
  isLoading.value = true
  try {
    const caseId = route.params.id
    const response = await api.get(`/cases/${caseId}`)
    caseData.value = response.data
    
    // Build timeline
    timeline.value = buildTimeline(caseData.value)
  } catch (error) {
    console.error('Failed to load case detail:', error)
    caseData.value = null
  } finally {
    isLoading.value = false
  }
}

const buildTimeline = (caseItem) => {
  const events = []
  
  events.push({
    timestamp: caseItem.created_at,
    title: '案件创建',
    description: '案件已创建并发布到案件池'
  })
  
  if (caseItem.accepted_at) {
    events.push({
      timestamp: caseItem.accepted_at,
      title: '专业人员接受',
      description: `${caseItem.professional_info?.name} 已接受此案件`
    })
  }
  
  if (caseItem.completed_at) {
    events.push({
      timestamp: caseItem.completed_at,
      title: '案件完成',
      description: '案件已标记为完成'
    })
  }
  
  return events.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
}

const acceptCase = async () => {
  if (!confirm('确认接受此案件?')) return
  
  try {
    await api.post(`/professional/cases/${route.params.id}/accept`)
    await loadCaseDetail()
    alert('案件接受成功')
  } catch (error) {
    console.error('Failed to accept case:', error)
    alert('接受失败: ' + (error.response?.data?.detail || error.message))
  }
}

const completeCase = async () => {
  if (!confirm('确认标记此案件为已完成?')) return
  
  try {
    await api.post(`/professional/cases/${route.params.id}/complete`)
    await loadCaseDetail()
    alert('案件已标记为完成')
  } catch (error) {
    console.error('Failed to complete case:', error)
    alert('操作失败: ' + (error.response?.data?.detail || error.message))
  }
}

const cancelCase = async () => {
  if (!confirm('确认取消此案件? 此操作不可撤销。')) return
  
  try {
    await api.post(`/cases/${route.params.id}/cancel`)
    router.push('/dashboard')
  } catch (error) {
    console.error('Failed to cancel case:', error)
    alert('取消失败: ' + (error.response?.data?.detail || error.message))
  }
}

const submitRating = async () => {
  try {
    await api.post(`/cases/${route.params.id}/rate`, {
      rating: rating.value,
      comment: ratingComment.value
    })
    showRatingModal.value = false
    alert('评价提交成功')
    await loadCaseDetail()
  } catch (error) {
    console.error('Failed to submit rating:', error)
    alert('评价失败: ' + (error.response?.data?.detail || error.message))
  }
}

const getStatusText = (status) => {
  const statusMap = {
    pending: '待处理',
    in_progress: '进行中',
    completed: '已完成',
    cancelled: '已取消'
  }
  return statusMap[status] || status
}

const formatDate = (dateString) => {
  return new Date(dateString).toLocaleDateString('zh-CN')
}

const formatDateTime = (dateString) => {
  return new Date(dateString).toLocaleString('zh-CN')
}

// Lifecycle
onMounted(() => {
  loadCaseDetail()
})
</script>

<style scoped>
.dashboard-container {
  display: flex;
  min-height: 100vh;
  background: #f5f5f5;
}

.main-content {
  flex: 1;
  padding: 24px;
  overflow-y: auto;
}

.dashboard-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
}

.dashboard-header h1 {
  font-size: 28px;
}

.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
}

.loading {
  width: 48px;
  height: 48px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.case-detail-content {
  max-width: 900px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.case-header-card {
  background: white;
  padding: 24px;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.case-title-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
  gap: 16px;
}

.case-title-row h2 {
  font-size: 24px;
  margin: 0;
  flex: 1;
}

.status-badge {
  padding: 6px 16px;
  border-radius: 12px;
  font-size: 13px;
  font-weight: 600;
  white-space: nowrap;
}

.status-pending { background: #fff3cd; color: #856404; }
.status-in_progress { background: #cfe2ff; color: #084298; }
.status-completed { background: #d1e7dd; color: #0f5132; }
.status-cancelled { background: #f8d7da; color: #842029; }

.case-meta {
  display: flex;
  gap: 20px;
  flex-wrap: wrap;
  font-size: 14px;
  color: #6c757d;
}

.case-meta .budget {
  color: #11998e;
  font-weight: 600;
}

.detail-section {
  background: white;
  padding: 24px;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.detail-section h3 {
  font-size: 18px;
  margin-bottom: 16px;
}

.case-description {
  color: #2d2d2d;
  line-height: 1.8;
  white-space: pre-wrap;
}

.info-grid {
  display: grid;
  gap: 16px;
}

.info-item {
  display: flex;
  gap: 12px;
}

.info-item .label {
  font-weight: 600;
  color: #6c757d;
  min-width: 100px;
}

.info-item .value {
  color: #2d2d2d;
}

.professional-card {
  padding: 16px;
  background: #f8f9fa;
  border-radius: 8px;
}

.professional-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.professional-header h4 {
  margin: 0;
}

.badge {
  padding: 4px 12px;
  background: #667eea;
  color: white;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
}

.timeline {
  position: relative;
  padding-left: 32px;
}

.timeline-item {
  position: relative;
  padding-bottom: 24px;
}

.timeline-item:last-child {
  padding-bottom: 0;
}

.timeline-item::before {
  content: '';
  position: absolute;
  left: -25px;
  top: 8px;
  bottom: -8px;
  width: 2px;
  background: #e5e5e5;
}

.timeline-item:last-child::before {
  display: none;
}

.timeline-marker {
  position: absolute;
  left: -30px;
  top: 4px;
  width: 12px;
  height: 12px;
  background: #667eea;
  border-radius: 50%;
  border: 3px solid white;
  box-shadow: 0 0 0 2px #667eea;
}

.timeline-time {
  color: #6c757d;
  font-size: 13px;
  margin-bottom: 4px;
}

.timeline-title {
  font-weight: 600;
  margin-bottom: 4px;
}

.timeline-desc {
  color: #6c757d;
  font-size: 14px;
}

.action-section {
  display: flex;
  gap: 12px;
  justify-content: center;
  padding: 20px;
}

.error-state {
  text-align: center;
  padding: 80px 20px;
}

.error-state h3 {
  font-size: 24px;
  margin-bottom: 12px;
}

.error-state p {
  color: #6c757d;
  margin-bottom: 24px;
}

.btn {
  padding: 12px 24px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.btn-primary:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

.btn-secondary {
  background: #f8f9fa;
  color: #495057;
  border: 1px solid #dee2e6;
}

.btn-secondary:hover {
  background: #e9ecef;
}

.btn-success {
  background: #28a745;
  color: white;
}

.btn-success:hover {
  background: #218838;
}

.btn-danger {
  background: #dc3545;
  color: white;
}

.btn-danger:hover {
  background: #c82333;
}

.rating-form {
  padding: 20px;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  font-weight: 600;
  margin-bottom: 8px;
}

.star-rating {
  font-size: 32px;
  display: flex;
  gap: 8px;
}

.star {
  color: #dee2e6;
  cursor: pointer;
  transition: color 0.2s;
}

.star:hover,
.star.active {
  color: #ffc107;
}

.input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #dee2e6;
  border-radius: 8px;
  font-size: 14px;
  font-family: inherit;
  resize: vertical;
}

.input:focus {
  outline: none;
  border-color: #667eea;
}

.modal-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  margin-top: 20px;
}
</style>
