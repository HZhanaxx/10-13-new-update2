<template>
  <div class="page-container">
    <Sidebar />
    
    <div class="main-content">
      <!-- Loading -->
      <div v-if="loading" class="loading-container">
        <div class="loading"></div>
        <p>加载中...</p>
      </div>

      <!-- Main Dashboard Content -->
      <div v-else>
        <!-- Header -->
        <header class="page-header">
          <div>
            <h1>👨‍💼 专业工作台</h1>
            <p class="subtitle">Professional Dashboard - 高效处理您的法律案件</p>
          </div>
          <div class="header-actions">
            <!-- Verification Status Badge -->
            <div v-if="isVerified" class="verified-badge">
              ✓ 已认证专业人士
            </div>
            <div v-else-if="verificationStatus === 'pending'" class="pending-badge">
              ⏳ 认证审核中
            </div>
          </div>
        </header>

        <!-- Verification Alert (if not verified) -->
        <div v-if="!isVerified" class="verification-alert">
          <div v-if="verificationStatus === 'pending'" class="alert-pending">
            <div class="alert-icon">⏳</div>
            <div class="alert-content">
              <h3>您的认证申请正在审核中</h3>
              <p>管理员正在审核您的专业资质，通常需要1-3个工作日。审核通过后即可查看并接受案件。</p>
            </div>
          </div>
          <div v-else class="alert-not-verified">
            <div class="alert-icon">🎓</div>
            <div class="alert-content">
              <h3>需要完成专业认证</h3>
              <p>完成认证后即可访问完整案件池、接收法律咨询订单</p>
              <button class="btn btn-primary" @click="showVerificationModal = true">
                ✅ 立即申请认证
              </button>
            </div>
          </div>
        </div>

        <!-- Dashboard Stats (for verified professionals) -->
        <div v-if="isVerified" class="dashboard-grid">
          <div class="glass-card welcome-card">
            <h2>欢迎回来, {{ authStore.userName }}</h2>
            <p>您当前有 <strong>{{ stats.in_progress_cases || 0 }}</strong> 个正在进行的案件。</p>
            <div class="btn-group">
              <button class="btn btn-primary" @click="$router.push('/case-pool')">
                去接单
              </button>
              <button class="btn btn-secondary" @click="$router.push('/professional/my-cases')">
                管理我的案件
              </button>
            </div>
          </div>

          <div class="glass-card stats-panel">
            <div class="mini-stat">
              <span class="label">进行中</span>
              <span class="val">{{ stats.in_progress_cases || 0 }}</span>
            </div>
            <div class="divider"></div>
            <div class="mini-stat">
              <span class="label">已完成</span>
              <span class="val">{{ stats.completed_cases || 0 }}</span>
            </div>
            <div class="divider"></div>
            <div class="mini-stat">
              <span class="label">总收入</span>
              <span class="val">¥{{ formatCurrency(stats.total_earnings) }}</span>
            </div>
          </div>
        </div>

        <!-- Recent Cases (for verified professionals) -->
        <div v-if="isVerified" class="section">
          <h2 class="section-title">最近案件</h2>
          <div v-if="recentCases.length > 0" class="cases-list">
            <div
              v-for="caseItem in recentCases"
              :key="caseItem.case_uuid"
              class="case-card"
              @click="viewCase(caseItem.case_uuid)"
            >
              <div class="case-header">
                <h3>{{ caseItem.title }}</h3>
                <span :class="['badge', `badge-${caseItem.case_status}`]">
                  {{ getCaseStatusText(caseItem.case_status) }}
                </span>
              </div>
              <p class="case-description">{{ truncate(caseItem.description, 100) }}</p>
              <div class="case-footer">
                <span class="case-category">{{ caseItem.case_category }}</span>
                <span class="case-budget">预算: ¥{{ caseItem.budget_cny }}</span>
              </div>
            </div>
          </div>
          <div v-else class="empty-state">
            <p>暂无案件</p>
            <button class="btn btn-primary" @click="$router.push('/case-pool')">
              前往案件池接单
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Verification Modal -->
    <div v-if="showVerificationModal" class="modal-overlay" @click="closeVerificationModal">
      <div class="modal-container" @click.stop>
        <div class="modal-header">
          <h2>申请专业认证</h2>
          <button class="modal-close" @click="closeVerificationModal">×</button>
        </div>
        
        <form @submit.prevent="submitVerification" class="modal-body">
          <!-- Basic Info -->
          <div class="form-group">
            <label class="form-label">姓名 <span class="required">*</span></label>
            <input
              v-model="verificationForm.full_name"
              type="text"
              class="form-input"
              placeholder="请输入您的真实姓名"
              required
            />
          </div>

          <div class="form-group">
            <label class="form-label">执业证号 <span class="required">*</span></label>
            <input
              v-model="verificationForm.license_number"
              type="text"
              class="form-input"
              placeholder="请输入您的执业证号"
              required
            />
          </div>

          <div class="form-group">
            <label class="form-label">所属律所</label>
            <input
              v-model="verificationForm.law_firm_name"
              type="text"
              class="form-input"
              placeholder="请输入律所名称"
            />
          </div>

          <!-- Specialty Areas -->
          <div class="form-group">
            <label class="form-label">专业领域 <span class="required">*</span></label>
            <p class="field-hint">至少选择一个专业领域</p>
            <div class="checkbox-grid">
              <label
                v-for="area in specialtyOptions"
                :key="area"
                class="checkbox-label"
              >
                <input
                  type="checkbox"
                  :value="area"
                  v-model="verificationForm.specialty_areas"
                />
                <span>{{ area }}</span>
              </label>
            </div>
            <div v-if="specialtyError" class="error-message">{{ specialtyError }}</div>
          </div>

          <!-- Professional Details -->
          <div class="form-group">
            <label class="form-label">从业年限</label>
            <input
              v-model.number="verificationForm.years_of_experience"
              type="number"
              class="form-input"
              placeholder="请输入从业年限"
              min="0"
            />
          </div>

          <div class="form-group">
            <label class="form-label">教育背景</label>
            <textarea
              v-model="verificationForm.education_background"
              class="form-input"
              rows="3"
              placeholder="请简要描述您的教育背景"
            ></textarea>
          </div>

          <div class="form-group">
            <label class="form-label">个人简介</label>
            <textarea
              v-model="verificationForm.bio"
              class="form-input"
              rows="4"
              placeholder="请简要介绍您的专业经验和服务特色"
            ></textarea>
          </div>

          <!-- Pricing -->
          <div class="form-row">
            <div class="form-group">
              <label class="form-label">咨询费用 (CNY)</label>
              <input
                v-model.number="verificationForm.consultation_fee_cny"
                type="number"
                class="form-input"
                placeholder="单次咨询费用"
                min="0"
                step="0.01"
              />
            </div>

            <div class="form-group">
              <label class="form-label">时薪 (CNY)</label>
              <input
                v-model.number="verificationForm.hourly_rate_cny"
                type="number"
                class="form-input"
                placeholder="每小时收费"
                min="0"
                step="0.01"
              />
            </div>
          </div>

          <!-- Location -->
          <div class="form-row">
            <div class="form-group">
              <label class="form-label">所在城市</label>
              <input
                v-model="verificationForm.city_name"
                type="text"
                class="form-input"
                placeholder="请输入所在城市"
              />
            </div>

            <div class="form-group">
              <label class="form-label">所在省份</label>
              <input
                v-model="verificationForm.province_name"
                type="text"
                class="form-input"
                placeholder="请输入所在省份"
              />
            </div>
          </div>

          <!-- File Upload -->
          <div class="form-group">
            <label class="form-label">上传证明文件 <span class="required">*</span></label>
            <div class="file-upload-area" @click="$refs.fileInput.click()">
              <div class="file-upload-icon">📄</div>
              <div class="file-upload-text">点击上传执业证、学历证明等文件</div>
              <div class="file-upload-hint">支持 PDF、JPG、PNG 格式，最多5个文件</div>
            </div>
            <input
              ref="fileInput"
              type="file"
              multiple
              accept=".pdf,.jpg,.jpeg,.png"
              @change="handleFileSelect"
              style="display: none"
            />
            <div v-if="selectedFiles.length > 0" class="file-list">
              <div v-for="(file, index) in selectedFiles" :key="index" class="file-item">
                <span class="file-name">{{ file.name }}</span>
                <span class="file-size">{{ formatFileSize(file.size) }}</span>
                <button type="button" @click="removeFile(index)" class="btn-remove">×</button>
              </div>
            </div>
            <div v-if="fileError" class="error-message">{{ fileError }}</div>
          </div>

          <!-- Submit Buttons -->
          <div class="modal-footer">
            <button type="button" class="btn btn-cancel" @click="closeVerificationModal">
              取消
            </button>
            <button type="submit" class="btn btn-submit" :disabled="submitting">
              <span v-if="!submitting">提交申请</span>
              <span v-else>提交中...</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import Sidebar from '@/components/Sidebar.vue'
import api from '@/utils/api'

const router = useRouter()
const authStore = useAuthStore()

// State
const loading = ref(true)
const isVerified = ref(false)
const verificationStatus = ref(null)
const stats = ref({})
const recentCases = ref([])
const showVerificationModal = ref(false)
const submitting = ref(false)
const specialtyError = ref('')
const fileError = ref('')
const selectedFiles = ref([])

// Verification Form
const verificationForm = ref({
  full_name: '',
  license_number: '',
  law_firm_name: '',
  specialty_areas: [],
  years_of_experience: null,
  education_background: '',
  bio: '',
  consultation_fee_cny: null,
  hourly_rate_cny: null,
  city_name: '',
  province_name: ''
})

// Specialty Options (matching case categories)
const specialtyOptions = [
  '劳动纠纷',
  '合同纠纷',
  '债务纠纷',
  '交通事故',
  '医疗纠纷',
  '房产纠纷',
  '知识产权',
  '婚姻家庭',
  '刑事辩护',
  '行政诉讼',
  '公司法务',
  '其他'
]

// Check verification status
const checkVerification = async () => {
  try {
    const response = await api.get('/professional/verification-status')
    
    // FIX: Extract 'data' from the axios response
    const data = response.data
    
    isVerified.value = data.is_verified
    verificationStatus.value = data.status
    
    // Also check for existing verification request
    if (!data.is_verified) {
      try {
        const requestResponse = await api.get('/verification/my-request')
        // FIX: Access .data from the request response too
        const requestData = requestResponse.data
        
        if (requestData.status === 'pending') {
          verificationStatus.value = 'pending'
        } else if (requestData.status === 'rejected') {
          verificationStatus.value = 'rejected'
        }
      } catch (error) {
        // No existing request
        verificationStatus.value = 'not_verified'
      }
    }
  } catch (error) {
    console.error('Failed to check verification:', error)
    isVerified.value = false
  }
}

// Load stats (only if verified)
const loadStats = async () => {
  if (!isVerified.value) return
  
  try {
    const response = await api.get('/professional/stats')
    // FIX: Assign response.data, not the whole response object
    stats.value = response.data
  } catch (error) {
    console.error('Failed to load stats:', error)
  }
}

// Load recent cases (only if verified)
const loadRecentCases = async () => {
  if (!isVerified.value) return
  
  try {
    const response = await api.get('/professional/my-cases')
    // FIX: Access .data before accessing .cases
    recentCases.value = (response.data.cases || []).slice(0, 5)
  } catch (error) {
    console.error('Failed to load cases:', error)
  }
}

// Handle file selection
const handleFileSelect = (event) => {
  const files = Array.from(event.target.files)
  
  // Validate file count
  if (selectedFiles.value.length + files.length > 5) {
    fileError.value = '最多只能上传5个文件'
    return
  }
  
  // Validate file size (10MB max per file)
  for (const file of files) {
    if (file.size > 10 * 1024 * 1024) {
      fileError.value = `文件 ${file.name} 超过10MB限制`
      return
    }
  }
  
  selectedFiles.value = [...selectedFiles.value, ...files]
  fileError.value = ''
}

// Remove file
const removeFile = (index) => {
  selectedFiles.value.splice(index, 1)
}

// Format file size
const formatFileSize = (bytes) => {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

// Submit verification
const submitVerification = async () => {
  // Validate specialty areas
  if (verificationForm.value.specialty_areas.length === 0) {
    specialtyError.value = '请至少选择一个专业领域'
    return
  }
  specialtyError.value = ''
  
  // Validate files
  if (selectedFiles.value.length === 0) {
    fileError.value = '请至少上传一个证明文件'
    return
  }
  fileError.value = ''
  
  submitting.value = true
  
  try {
    // Create FormData
    const formData = new FormData()
    
    // Add form fields
    formData.append('full_name', verificationForm.value.full_name)
    formData.append('license_number', verificationForm.value.license_number)
    if (verificationForm.value.law_firm_name) {
      formData.append('law_firm_name', verificationForm.value.law_firm_name)
    }
    
    // Add specialty areas (as individual fields for backend compatibility)
    verificationForm.value.specialty_areas.forEach(area => {
      formData.append('specialty_areas', area)
    })
    
    if (verificationForm.value.years_of_experience) {
      formData.append('years_of_experience', verificationForm.value.years_of_experience.toString())
    }
    if (verificationForm.value.education_background) {
      formData.append('education_background', verificationForm.value.education_background)
    }
    if (verificationForm.value.bio) {
      formData.append('bio', verificationForm.value.bio)
    }
    if (verificationForm.value.consultation_fee_cny) {
      formData.append('consultation_fee_cny', verificationForm.value.consultation_fee_cny.toString())
    }
    if (verificationForm.value.hourly_rate_cny) {
      formData.append('hourly_rate_cny', verificationForm.value.hourly_rate_cny.toString())
    }
    if (verificationForm.value.city_name) {
      formData.append('city_name', verificationForm.value.city_name)
    }
    if (verificationForm.value.province_name) {
      formData.append('province_name', verificationForm.value.province_name)
    }
    
    // Add files
    selectedFiles.value.forEach(file => {
      formData.append('files', file)
    })
    
    // Submit
    await api.post('/verification/request', formData)
    // DON'T set Content-Type manually - browser adds boundary automatically!
    
    alert('认证申请已提交，请等待管理员审核')
    closeVerificationModal()
    await checkVerification()
    
  } catch (error) {
    console.error('Verification submission failed:', error)
    alert(error.response?.data?.detail || '提交失败，请重试')
  } finally {
    submitting.value = false
  }
}

// Close verification modal
const closeVerificationModal = () => {
  showVerificationModal.value = false
  // Reset form
  verificationForm.value = {
    full_name: '',
    license_number: '',
    law_firm_name: '',
    specialty_areas: [],
    years_of_experience: null,
    education_background: '',
    bio: '',
    consultation_fee_cny: null,
    hourly_rate_cny: null,
    city_name: '',
    province_name: ''
  }
  selectedFiles.value = []
  specialtyError.value = ''
  fileError.value = ''
}

// View case detail
const viewCase = (caseUuid) => {
  router.push(`/case/${caseUuid}`)
}

// Format currency
const formatCurrency = (amount) => {
  if (!amount) return '0.00'
  return Number(amount).toLocaleString('zh-CN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  })
}

// Get case status text
const getCaseStatusText = (status) => {
  const statusMap = {
    'pending': '待处理',
    'in_progress': '进行中',
    'completed': '已完成',
    'cancelled': '已取消'
  }
  return statusMap[status] || status
}

// Truncate text
const truncate = (text, length) => {
  if (!text) return ''
  return text.length > length ? text.substring(0, length) + '...' : text
}

onMounted(async () => {
  // Check if user is professional
  if (authStore.userRole !== 'professional') {
    alert('只有专业人士可以访问此页面')
    router.push('/dashboard')
    return
  }

  // Check verification status
  await checkVerification()

  // If verified, load stats and cases
  if (isVerified.value) {
    await Promise.all([loadStats(), loadRecentCases()])
  }

  loading.value = false
})
</script>

<style scoped>
.page-container {
  display: flex;
  min-height: 100vh;
  background: #f5f7fa;
}

.main-content {
  flex: 1;
  padding: 40px;
  max-width: 1400px;
  margin: 0 auto;
}

/* Loading */
.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 400px;
}

.loading {
  width: 48px;
  height: 48px;
  border: 4px solid #e2e8f0;
  border-top-color: #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Header */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 32px;
}

.page-header h1 {
  font-size: 32px;
  color: #2d3748;
  margin-bottom: 8px;
}

.subtitle {
  color: #718096;
  font-size: 16px;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.verified-badge {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  color: white;
  padding: 8px 16px;
  border-radius: 20px;
  font-size: 14px;
  font-weight: 600;
}

.pending-badge {
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
  color: white;
  padding: 8px 16px;
  border-radius: 20px;
  font-size: 14px;
  font-weight: 600;
}

/* Verification Alert */
.verification-alert {
  background: white;
  border-radius: 16px;
  padding: 32px;
  margin-bottom: 32px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.alert-pending,
.alert-not-verified {
  display: flex;
  gap: 24px;
  align-items: center;
}

.alert-icon {
  font-size: 64px;
  flex-shrink: 0;
}

.alert-content h3 {
  font-size: 24px;
  color: #2d3748;
  margin-bottom: 12px;
}

.alert-content p {
  color: #4a5568;
  margin-bottom: 16px;
  line-height: 1.6;
}

/* Dashboard Grid */
.dashboard-grid {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 24px;
  margin-bottom: 40px;
}

.glass-card {
  background: white;
  border-radius: 16px;
  padding: 32px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.welcome-card h2 {
  font-size: 24px;
  margin-bottom: 12px;
  color: #2d3748;
}

.welcome-card p {
  color: #4a5568;
  margin-bottom: 24px;
}

.btn-group {
  display: flex;
  gap: 12px;
}

.stats-panel {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 20px;
}

.mini-stat {
  text-align: center;
}

.mini-stat .label {
  display: block;
  font-size: 12px;
  color: #718096;
  margin-bottom: 4px;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.mini-stat .val {
  font-size: 32px;
  font-weight: 700;
  color: #667eea;
}

.divider {
  height: 1px;
  background: rgba(0, 0, 0, 0.05);
}

/* Recent Cases */
.section {
  margin-top: 40px;
}

.section-title {
  font-size: 24px;
  color: #2d3748;
  margin-bottom: 20px;
}

.cases-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
}

.case-card {
  background: white;
  border-radius: 12px;
  padding: 20px;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.case-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
}

.case-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
}

.case-header h3 {
  font-size: 18px;
  color: #2d3748;
  flex: 1;
}

.badge {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
}

.badge-pending {
  background: #fef5e7;
  color: #f39c12;
}

.badge-in_progress {
  background: #e8f4fd;
  color: #3498db;
}

.badge-completed {
  background: #e8f8f5;
  color: #27ae60;
}

.case-description {
  color: #718096;
  font-size: 14px;
  line-height: 1.6;
  margin-bottom: 16px;
}

.case-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 12px;
  border-top: 1px solid #e2e8f0;
}

.case-category {
  font-size: 12px;
  color: #667eea;
  font-weight: 600;
}

.case-budget {
  font-size: 14px;
  color: #2d3748;
  font-weight: 600;
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
  background: white;
  border-radius: 12px;
}

.empty-state p {
  color: #a0aec0;
  margin-bottom: 20px;
}

/* Buttons */
.btn {
  padding: 12px 24px;
  border-radius: 10px;
  border: none;
  font-weight: 600;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.3s;
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.btn-primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(102, 126, 234, 0.4);
}

.btn-secondary {
  background: #f3f4f6;
  color: #4b5563;
}

.btn-secondary:hover {
  background: #e5e7eb;
}

.btn-cancel {
  background: #f3f4f6;
  color: #6b7280;
}

.btn-submit {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  color: white;
}

.btn-submit:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Modal */
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
}

.modal-container {
  background: white;
  border-radius: 16px;
  width: 90%;
  max-width: 700px;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24px 32px;
  border-bottom: 1px solid #e2e8f0;
}

.modal-header h2 {
  font-size: 24px;
  color: #2d3748;
}

.modal-close {
  background: none;
  border: none;
  font-size: 32px;
  color: #9ca3af;
  cursor: pointer;
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  transition: all 0.2s;
}

.modal-close:hover {
  background: #f3f4f6;
  color: #4b5563;
}

.modal-body {
  padding: 32px;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 24px 32px;
  border-top: 1px solid #e2e8f0;
}

/* Form */
.form-group {
  margin-bottom: 24px;
}

.form-label {
  display: block;
  font-size: 14px;
  font-weight: 600;
  color: #374151;
  margin-bottom: 8px;
}

.required {
  color: #ef4444;
}

.field-hint {
  color: #6b7280;
  font-size: 13px;
  margin: 8px 0;
}

.form-input {
  width: 100%;
  padding: 12px 16px;
  border: 2px solid #e5e7eb;
  border-radius: 10px;
  font-size: 15px;
  transition: all 0.2s;
  font-family: inherit;
}

.form-input:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

textarea.form-input {
  resize: vertical;
  min-height: 80px;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

/* Checkbox Grid */
.checkbox-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 12px;
  margin-top: 12px;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border: 2px solid #e5e7eb;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.checkbox-label:hover {
  border-color: #667eea;
  background: #f9fafb;
}

.checkbox-label input[type="checkbox"] {
  width: 18px;
  height: 18px;
  cursor: pointer;
}

.checkbox-label input[type="checkbox"]:checked + span {
  font-weight: 600;
  color: #667eea;
}

/* File Upload */
.file-upload-area {
  border: 2px dashed #cbd5e0;
  border-radius: 12px;
  padding: 32px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
}

.file-upload-area:hover {
  border-color: #667eea;
  background: #f9fafb;
}

.file-upload-icon {
  font-size: 48px;
  margin-bottom: 12px;
}

.file-upload-text {
  color: #4b5563;
  font-size: 15px;
  margin-bottom: 8px;
}

.file-upload-hint {
  color: #9ca3af;
  font-size: 13px;
}

.file-list {
  margin-top: 16px;
}

.file-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: #f9fafb;
  border-radius: 8px;
  margin-bottom: 8px;
}

.file-name {
  flex: 1;
  font-size: 14px;
  color: #374151;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-size {
  font-size: 12px;
  color: #9ca3af;
}

.btn-remove {
  background: #ef4444;
  color: white;
  border: none;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  cursor: pointer;
  font-size: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.btn-remove:hover {
  background: #dc2626;
}

.error-message {
  color: #ef4444;
  font-size: 13px;
  margin-top: 8px;
}

@media (max-width: 1024px) {
  .dashboard-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .main-content {
    padding: 20px;
  }

  .cases-list {
    grid-template-columns: 1fr;
  }

  .form-row {
    grid-template-columns: 1fr;
  }

  .checkbox-grid {
    grid-template-columns: 1fr;
  }
}
</style>
