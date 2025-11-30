<template>
  <div class="dashboard-container">
    <Sidebar />
    
    <!-- Verification Check Loading -->
    <div v-if="checkingVerification" class="main-content">
      <div class="loading-container">
        <div class="loading"></div>
        <p>验证身份中...</p>
      </div>
    </div>

    <!-- Main Content - Only show if verified -->
    <div v-else-if="isVerified" class="main-content">
      <header class="dashboard-header">
        <div>
          <h1>📋 案件池</h1>
          <p class="subtitle">Case Pool - 查找可接受的案件</p>
        </div>
        <div class="header-actions">
          <button class="btn btn-secondary" @click="$router.push('/professional')">
            ← 返回工作台
          </button>
          <div class="user-menu">
            <button class="btn btn-secondary" @click="toggleUserMenu">
              {{ authStore.userName }}
            </button>
            <div v-if="showUserMenu" class="dropdown-menu">
              <router-link to="/profile" class="menu-item">个人资料</router-link>
              <button @click="handleLogout" class="menu-item">退出登录</button>
            </div>
          </div>
        </div>
      </header>

      <!-- Filters -->
      <div class="filters-section">
        <div class="filter-group">
          <label>案件类别:</label>
          <select v-model="filters.category" class="input" @change="loadCases">
            <option value="">全部类别</option>
            <option value="劳动纠纷">劳动纠纷</option>
            <option value="合同纠纷">合同纠纷</option>
            <option value="债务纠纷">债务纠纷</option>
            <option value="交通事故">交通事故</option>
            <option value="医疗纠纷">医疗纠纷</option>
            <option value="房产纠纷">房产纠纷</option>
            <option value="知识产权">知识产权</option>
            <option value="婚姻家庭">婚姻家庭</option>
            <option value="其他">其他</option>
          </select>
        </div>
        <div class="filter-group">
          <label>预算范围:</label>
          <select v-model="filters.budget" class="input" @change="loadCases">
            <option value="">全部预算</option>
            <option value="0-5000">¥0 - ¥5,000</option>
            <option value="5000-10000">¥5,000 - ¥10,000</option>
            <option value="10000-20000">¥10,000 - ¥20,000</option>
            <option value="20000+">¥20,000+</option>
          </select>
        </div>
        <div class="filter-group">
          <label>排序方式:</label>
          <select v-model="filters.sort" class="input" @change="loadCases">
            <option value="newest">最新发布</option>
            <option value="highest_budget">预算最高</option>
            <option value="urgent">紧急案件</option>
          </select>
        </div>
        <button class="btn btn-secondary" @click="resetFilters">重置筛选</button>
      </div>

      <!-- Statistics -->
      <div class="stats-banner">
        <div class="stat-item">
          <span class="stat-number">{{ cases.length }}</span>
          <span class="stat-text">可接案件</span>
        </div>
        <div class="stat-divider"></div>
        <div class="stat-item">
          <span class="stat-number">{{ filterStats.todayCases }}</span>
          <span class="stat-text">今日新增</span>
        </div>
        <div class="stat-divider"></div>
        <div class="stat-item">
          <span class="stat-number">¥{{ filterStats.avgBudget }}</span>
          <span class="stat-text">平均预算</span>
        </div>
      </div>

      <!-- Loading state -->
      <div v-if="isLoading" class="loading-container">
        <div class="loading"></div>
        <p>加载案件中...</p>
      </div>

      <!-- Cases list -->
      <div v-else-if="cases.length > 0" class="cases-grid">
        <div
          v-for="caseItem in cases"
          :key="caseItem.case_uuid"
          class="case-card pool-case"
        >
          <div class="case-header">
            <h3>{{ caseItem.title }}</h3>
            <span v-if="isUrgent(caseItem)" class="urgent-badge">
              🔥 紧急
            </span>
          </div>
          <p class="case-description">{{ caseItem.description }}</p>
          <div class="case-meta">
            <span>📁 {{ caseItem.case_category }}</span>
            <span class="budget-highlight">💰 ¥{{ caseItem.budget_cny }}</span>
            <span>📅 {{ formatDate(caseItem.created_at) }}</span>
            <span v-if="caseItem.location">📍 {{ caseItem.location }}</span>
          </div>
          <div v-if="caseItem.requirements" class="case-requirements">
            <strong>要求:</strong> {{ caseItem.requirements }}
          </div>
          <div class="case-actions">
            <button 
              class="btn btn-primary btn-block" 
              @click="acceptCase(caseItem.case_uuid)"
            >
              接受案件
            </button>
            <button 
              class="btn btn-secondary btn-sm" 
              @click="viewCaseDetail(caseItem.case_uuid)"
            >
              查看详情
            </button>
          </div>
        </div>
      </div>

      <!-- Empty state -->
      <div v-else class="empty-state">
        <div class="empty-icon">🔍</div>
        <h3>暂无可接案件</h3>
        <p>当前筛选条件下没有找到合适的案件</p>
        <button class="btn btn-secondary" @click="resetFilters">
          重置筛选条件
        </button>
      </div>
    </div>

    <!-- Not Verified (fallback, shouldn't show due to redirect) -->
    <div v-else class="main-content">
      <div class="loading-container">
        <p>正在跳转...</p>
      </div>
    </div>

    <!-- Accept Case Confirmation Modal -->
    <Modal v-if="showAcceptModal" @close="showAcceptModal = false">
      <template #header>
        <h2>确认接受案件</h2>
      </template>
      <template #body>
        <div class="modal-content">
          <p>您确定要接受此案件吗?</p>
          <div class="case-info">
            <h4>{{ selectedCase?.title }}</h4>
            <p>{{ selectedCase?.description }}</p>
            <div class="case-details">
              <div>类别: {{ selectedCase?.case_category }}</div>
              <div>预算: ¥{{ selectedCase?.budget_cny }}</div>
            </div>
          </div>
          <div class="modal-actions">
            <button class="btn btn-secondary" @click="showAcceptModal = false">
              取消
            </button>
            <button class="btn btn-primary" @click="confirmAcceptCase">
              确认接受
            </button>
          </div>
        </div>
      </template>
    </Modal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import Sidebar from '@/components/Sidebar.vue'
import Modal from '@/components/Modal.vue'
import api from '@/utils/api'

const router = useRouter()
const authStore = useAuthStore()

// State
const isLoading = ref(false)
const cases = ref([])
const showUserMenu = ref(false)
const showAcceptModal = ref(false)
const selectedCase = ref(null)
const checkingVerification = ref(true)  // NEW: Verification check state
const isVerified = ref(false)           // NEW: Verification status

const filters = ref({
  category: '',
  budget: '',
  sort: 'newest'
})

// Computed
const filterStats = computed(() => {
  const today = new Date().toDateString()
  const todayCases = cases.value.filter(c => 
    new Date(c.created_at).toDateString() === today
  ).length
  
  const avgBudget = cases.value.length > 0
    ? Math.round(cases.value.reduce((sum, c) => sum + c.budget_cny, 0) / cases.value.length)
    : 0
  
  return {
    todayCases,
    avgBudget
  }
})

// NEW: Check verification status
const checkVerification = async () => {
  checkingVerification.value = true
  try {
    const response = await api.get('/professional/verification-status')
    
    // FIX: Extract data from axios response
    const data = response.data
    isVerified.value = data.is_verified
    
    // If not verified, show alert and redirect
    if (!data.is_verified) {
      if (data.status === 'pending') {
        alert('您的认证申请正在审核中,审核通过后即可访问案件池')
      } else if (data.status === 'not_verified') {
        alert('您需要完成专业认证后才能访问案件池\n\n请前往专业工作台完成认证申请')
      } else {
        alert('您需要完成专业认证后才能访问案件池')
      }
      router.push('/professional')
      return false
    }
    return true
  } catch (error) {
    console.error('Failed to check verification:', error)
    // If verification check fails, assume not verified for safety
    alert('无法验证您的专业身份,请稍后重试')
    router.push('/professional')
    return false
  } finally {
    checkingVerification.value = false
  }
}

// Methods
const loadCases = async () => {
  isLoading.value = true
  try {
    const params = {}
    if (filters.value.category) params.category = filters.value.category
    if (filters.value.budget) {
      const [min, max] = filters.value.budget.split('-')
      params.min_budget = min
      if (max !== '+') params.max_budget = max
    }
    if (filters.value.sort) params.sort = filters.value.sort
    
    const response = await api.get('/cases/pool', { params })
    cases.value = response.data.cases || []
  } catch (error) {
    console.error('Failed to load cases:', error)
    cases.value = []
  } finally {
    isLoading.value = false
  }
}

const resetFilters = () => {
  filters.value = {
    category: '',
    budget: '',
    sort: 'newest'
  }
  loadCases()
}

const acceptCase = (caseUuid) => {
  selectedCase.value = cases.value.find(c => c.case_uuid === caseUuid)
  showAcceptModal.value = true
}

const confirmAcceptCase = async () => {
  try {
    await api.post(`/professional/cases/${selectedCase.value.case_uuid}/accept`)
    showAcceptModal.value = false
    // Redirect to professional dashboard
    router.push('/professional')
  } catch (error) {
    console.error('Failed to accept case:', error)
    alert('接受案件失败: ' + (error.response?.data?.detail || error.message))
  }
}

const viewCaseDetail = (caseUuid) => {
  router.push(`/case/${caseUuid}`)
}

const isUrgent = (caseItem) => {
  // A case is urgent if created within the last 24 hours and has high budget
  const createdDate = new Date(caseItem.created_at)
  const now = new Date()
  const hoursDiff = (now - createdDate) / (1000 * 60 * 60)
  return hoursDiff < 24 && caseItem.budget_cny > 10000
}

const formatDate = (dateString) => {
  const date = new Date(dateString)
  const now = new Date()
  const diffHours = Math.floor((now - date) / (1000 * 60 * 60))
  
  if (diffHours < 1) return '刚刚'
  if (diffHours < 24) return `${diffHours}小时前`
  if (diffHours < 48) return '昨天'
  return date.toLocaleDateString('zh-CN')
}

const toggleUserMenu = () => {
  showUserMenu.value = !showUserMenu.value
}

const handleLogout = async () => {
  await authStore.logout()
  router.push('/login')
}

// Lifecycle - UPDATED with verification check
onMounted(async () => {
  // Check if user is professional
  if (authStore.userRole !== 'professional') {
    alert('只有专业人士可以访问案件池')
    router.push('/dashboard')
    return
  }

  // Check verification status BEFORE loading cases
  const verified = await checkVerification()
  if (!verified) {
    // Already redirected in checkVerification
    return
  }

  // Only load cases if verified
  await loadCases()
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
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.dashboard-header h1 {
  font-size: 28px;
  margin-bottom: 4px;
  color: #2d2d2d;
}

.subtitle {
  color: #888;
  font-size: 14px;
}

.header-actions {
  display: flex;
  gap: 16px;
  align-items: center;
}

.user-menu {
  position: relative;
}

.dropdown-menu {
  position: absolute;
  top: 100%;
  right: 0;
  margin-top: 8px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  min-width: 150px;
  z-index: 100;
}

.menu-item {
  display: block;
  width: 100%;
  padding: 12px 16px;
  text-align: left;
  border: none;
  background: none;
  cursor: pointer;
  color: #2d2d2d;
  text-decoration: none;
  transition: background 0.2s;
}

.menu-item:hover {
  background: #f5f5f5;
}

.filters-section {
  display: flex;
  gap: 16px;
  margin-bottom: 24px;
  flex-wrap: wrap;
}

.filter-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex: 1;
  min-width: 200px;
}

.filter-group label {
  font-size: 13px;
  font-weight: 600;
  color: #555;
}

.input {
  padding: 10px 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
  background: white;
}

.input:focus {
  outline: none;
  border-color: #11998e;
}

.stats-banner {
  background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
  color: white;
  padding: 24px;
  border-radius: 12px;
  margin-bottom: 24px;
  display: flex;
  justify-content: space-around;
  align-items: center;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.stat-number {
  font-size: 32px;
  font-weight: 700;
}

.stat-text {
  font-size: 14px;
  opacity: 0.9;
}

.stat-divider {
  width: 1px;
  height: 40px;
  background: rgba(255, 255, 255, 0.3);
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
  border-top: 4px solid #11998e;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.cases-grid {
  display: grid;
  gap: 16px;
}

.case-card {
  background: white;
  padding: 20px;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  transition: all 0.2s;
}

.case-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
}

.case-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
  gap: 12px;
}

.case-header h3 {
  font-size: 18px;
  margin: 0;
  flex: 1;
}

.urgent-badge {
  padding: 4px 12px;
  background: linear-gradient(135deg, #ff6b6b 0%, #feca57 100%);
  color: white;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
}

.case-description {
  color: #666;
  font-size: 14px;
  line-height: 1.6;
  margin-bottom: 16px;
}

.case-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 12px;
  font-size: 13px;
  color: #888;
}

.budget-highlight {
  color: #11998e;
  font-weight: 600;
}

.case-requirements {
  background: #f8f9fa;
  padding: 12px;
  border-radius: 6px;
  font-size: 13px;
  margin-bottom: 16px;
}

.case-actions {
  display: flex;
  gap: 12px;
}

.btn {
  padding: 10px 20px;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-primary {
  background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
  color: white;
}

.btn-primary:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(17, 153, 142, 0.3);
}

.btn-secondary {
  background: white;
  color: #2d2d2d;
  border: 1px solid #ddd;
}

.btn-secondary:hover {
  background: #f5f5f5;
}

.btn-block {
  flex: 1;
}

.btn-sm {
  padding: 8px 16px;
  font-size: 13px;
}

.empty-state {
  text-align: center;
  padding: 80px 20px;
}

.empty-icon {
  font-size: 64px;
  margin-bottom: 20px;
}

.empty-state h3 {
  font-size: 24px;
  color: #2d2d2d;
  margin-bottom: 12px;
}

.empty-state p {
  color: #888;
  margin-bottom: 24px;
}

.modal-content {
  padding: 20px;
}

.case-info {
  background: #f8f9fa;
  padding: 20px;
  border-radius: 8px;
  margin: 20px 0;
}

.case-info h4 {
  margin: 0 0 12px 0;
  font-size: 18px;
}

.case-info p {
  color: #666;
  margin-bottom: 16px;
}

.case-details {
  display: flex;
  gap: 20px;
  font-size: 14px;
}

.modal-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  margin-top: 20px;
}

@media (max-width: 768px) {
  .filters-section {
    flex-direction: column;
  }
  
  .stats-banner {
    flex-direction: column;
    gap: 16px;
  }
  
  .stat-divider {
    width: 60px;
    height: 1px;
  }
}
</style>
