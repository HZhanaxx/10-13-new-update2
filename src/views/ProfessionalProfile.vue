<template>
  <div class="dashboard-container">
    <Sidebar />
    
    <div class="main-content">
      <header class="dashboard-header">
        <h1>⚖️ 专业资料</h1>
        <button class="btn btn-secondary" @click="$router.go(-1)">
          ← 返回
        </button>
      </header>

      <!-- Loading state -->
      <div v-if="loading" class="loading-container">
        <div class="loading"></div>
        <p>加载中...</p>
      </div>

      <!-- Content -->
      <div v-else class="profile-content">
        <!-- Verification Status Banner -->
        <div v-if="verificationStatus" class="status-banner" :class="`status-${verificationStatus.status}`">
          <div class="status-content">
            <span class="status-icon">
              {{ getStatusIcon(verificationStatus.status) }}
            </span>
            <div class="status-text">
              <h3>{{ getStatusTitle(verificationStatus.status) }}</h3>
              <p>{{ getStatusMessage(verificationStatus.status) }}</p>
            </div>
          </div>
        </div>

        <!-- Professional Information Card -->
        <div class="profile-card">
          <div class="card-header">
            <h2>📋 专业信息</h2>
            <button 
              v-if="!editing && professionalInfo"
              class="btn btn-primary" 
              @click="startEdit"
            >
              ✏️ 编辑资料
            </button>
          </div>
          
          <div class="card-body">
            <!-- View Mode -->
            <div v-if="!editing && professionalInfo" class="info-view">
              <div class="info-section">
                <h3>基本信息</h3>
                <div class="info-grid">
                  <div class="info-item">
                    <span class="label">姓名</span>
                    <span class="value">{{ professionalInfo.full_name || '-' }}</span>
                  </div>
                  <div class="info-item">
                    <span class="label">律师执照号</span>
                    <span class="value">{{ professionalInfo.license_number || '-' }}</span>
                  </div>
                  <div class="info-item">
                    <span class="label">律所名称</span>
                    <span class="value">{{ professionalInfo.law_firm_name || '-' }}</span>
                  </div>
                  <div class="info-item">
                    <span class="label">执业年限</span>
                    <span class="value">{{ professionalInfo.years_of_experience || 0 }} 年</span>
                  </div>
                  <div class="info-item">
                    <span class="label">所在城市</span>
                    <span class="value">{{ formatLocation(professionalInfo.province_name, professionalInfo.city_name) }}</span>
                  </div>
                </div>
              </div>

              <div class="info-section">
                <h3>专业领域</h3>
                <div class="specialty-tags">
                  <span 
                    v-for="(area, index) in parseSpecialtyAreas(professionalInfo.specialty_areas)" 
                    :key="index"
                    class="specialty-tag"
                  >
                    {{ area }}
                  </span>
                  <span v-if="!professionalInfo.specialty_areas || parseSpecialtyAreas(professionalInfo.specialty_areas).length === 0" class="empty-state">
                    未设置专业领域
                  </span>
                </div>
              </div>

              <div class="info-section">
                <h3>教育背景</h3>
                <p class="text-content">{{ professionalInfo.education_background || '未设置' }}</p>
              </div>

              <div class="info-section">
                <h3>个人简介</h3>
                <p class="text-content">{{ professionalInfo.bio || '未设置' }}</p>
              </div>

              <div class="info-section">
                <h3>收费标准</h3>
                <div class="info-grid">
                  <div class="info-item">
                    <span class="label">咨询费用</span>
                    <span class="value">¥{{ professionalInfo.consultation_fee_cny || 0 }} / 次</span>
                  </div>
                  <div class="info-item">
                    <span class="label">时薪</span>
                    <span class="value">¥{{ professionalInfo.hourly_rate_cny || 0 }} / 小时</span>
                  </div>
                </div>
              </div>

              <div class="info-section">
                <h3>认证信息</h3>
                <div class="info-grid">
                  <div class="info-item">
                    <span class="label">认证状态</span>
                    <span class="value">
                      <span :class="['badge', `badge-${professionalInfo.is_verified ? 'success' : 'warning'}`]">
                        {{ professionalInfo.is_verified ? '✓ 已认证' : '⚠ 未认证' }}
                      </span>
                    </span>
                  </div>
                  <div class="info-item" v-if="professionalInfo.verified_at">
                    <span class="label">认证时间</span>
                    <span class="value">{{ formatDate(professionalInfo.verified_at) }}</span>
                  </div>
                  <div class="info-item">
                    <span class="label">账户状态</span>
                    <span class="value">
                      <span :class="['badge', `badge-${professionalInfo.account_status === 'active' ? 'success' : 'danger'}`]">
                        {{ getAccountStatusText(professionalInfo.account_status) }}
                      </span>
                    </span>
                  </div>
                </div>
              </div>
            </div>

            <!-- Edit Mode -->
            <form v-else-if="editing" @submit.prevent="saveChanges" class="edit-form">
              <div class="form-section">
                <h3>基本信息</h3>
                <div class="form-grid">
                  <div class="form-group">
                    <label>姓名 *</label>
                    <input
                      v-model="editForm.full_name"
                      type="text"
                      class="input"
                      placeholder="请输入真实姓名"
                      required
                    />
                  </div>
                  <div class="form-group">
                    <label>律师执照号 *</label>
                    <input
                      v-model="editForm.license_number"
                      type="text"
                      class="input"
                      placeholder="请输入律师执照号"
                      required
                    />
                  </div>
                  <div class="form-group">
                    <label>律所名称 *</label>
                    <input
                      v-model="editForm.law_firm_name"
                      type="text"
                      class="input"
                      placeholder="请输入律所名称"
                      required
                    />
                  </div>
                  <div class="form-group">
                    <label>执业年限 *</label>
                    <input
                      v-model.number="editForm.years_of_experience"
                      type="number"
                      class="input"
                      placeholder="请输入执业年限"
                      min="0"
                      required
                    />
                  </div>
                  <div class="form-group">
                    <label>所在省份</label>
                    <input
                      v-model="editForm.province_name"
                      type="text"
                      class="input"
                      placeholder="例如: 北京市"
                    />
                  </div>
                  <div class="form-group">
                    <label>所在城市</label>
                    <input
                      v-model="editForm.city_name"
                      type="text"
                      class="input"
                      placeholder="例如: 朝阳区"
                    />
                  </div>
                </div>
              </div>

              <div class="form-section">
                <h3>专业领域 *</h3>
                <div class="specialty-selector">
                  <div class="specialty-options">
                    <label 
                      v-for="area in availableSpecialties" 
                      :key="area"
                      class="specialty-option"
                    >
                      <input 
                        type="checkbox" 
                        :value="area"
                        v-model="editForm.specialty_areas"
                      />
                      <span>{{ area }}</span>
                    </label>
                  </div>
                  <div class="custom-specialty">
                    <input
                      v-model="customSpecialty"
                      type="text"
                      class="input"
                      placeholder="其他专业领域"
                      @keyup.enter="addCustomSpecialty"
                    />
                    <button type="button" class="btn btn-sm btn-secondary" @click="addCustomSpecialty">
                      添加
                    </button>
                  </div>
                  <p class="hint">已选择: {{ editForm.specialty_areas.length }} 个专业领域</p>
                </div>
              </div>

              <div class="form-section">
                <h3>教育背景</h3>
                <textarea
                  v-model="editForm.education_background"
                  class="textarea"
                  rows="4"
                  placeholder="例如: 中国政法大学 法学学士 (2010-2014)&#10;北京大学 法学硕士 (2014-2017)"
                ></textarea>
              </div>

              <div class="form-section">
                <h3>个人简介</h3>
                <textarea
                  v-model="editForm.bio"
                  class="textarea"
                  rows="6"
                  placeholder="请介绍您的专业背景、执业经验、擅长领域等..."
                ></textarea>
              </div>

              <div class="form-section">
                <h3>收费标准</h3>
                <div class="form-grid">
                  <div class="form-group">
                    <label>咨询费用 (元/次)</label>
                    <input
                      v-model.number="editForm.consultation_fee_cny"
                      type="number"
                      class="input"
                      placeholder="0"
                      min="0"
                      step="0.01"
                    />
                  </div>
                  <div class="form-group">
                    <label>时薪 (元/小时)</label>
                    <input
                      v-model.number="editForm.hourly_rate_cny"
                      type="number"
                      class="input"
                      placeholder="0"
                      min="0"
                      step="0.01"
                    />
                  </div>
                </div>
              </div>

              <div class="form-actions">
                <button type="button" class="btn btn-secondary" @click="cancelEdit">
                  取消
                </button>
                <button type="submit" class="btn btn-primary" :disabled="saving">
                  {{ saving ? '保存中...' : '保存修改' }}
                </button>
              </div>

              <div class="form-notice">
                <p>💡 提示: 修改后的资料需要管理员重新审核后才能生效</p>
              </div>
            </form>

            <!-- No Professional Info -->
            <div v-else-if="!professionalInfo" class="empty-state">
              <p>暂无专业资料</p>
              <button class="btn btn-primary" @click="$router.push('/professional/verification')">
                提交认证申请
              </button>
            </div>
          </div>
        </div>
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
const editing = ref(false)
const saving = ref(false)
const professionalInfo = ref(null)
const verificationStatus = ref(null)
const customSpecialty = ref('')

// Available specialty areas
const availableSpecialties = [
  '刑事辩护',
  '民事诉讼',
  '商事诉讼',
  '行政诉讼',
  '劳动争议',
  '婚姻家庭',
  '房产纠纷',
  '合同纠纷',
  '知识产权',
  '公司法务',
  '税务筹划',
  '金融证券',
  '建筑工程',
  '交通事故',
  '医疗纠纷',
  '环境保护'
]

// Edit form
const editForm = ref({
  full_name: '',
  license_number: '',
  law_firm_name: '',
  specialty_areas: [],
  years_of_experience: 0,
  education_background: '',
  bio: '',
  consultation_fee_cny: 0,
  hourly_rate_cny: 0,
  city_name: '',
  province_name: ''
})

// Load professional info
const loadProfessionalInfo = async () => {
  try {
    const response = await api.get('/professional/profile')
    professionalInfo.value = response.data
  } catch (error) {
    console.error('Failed to load professional info:', error)
    if (error.response?.status === 404) {
      professionalInfo.value = null
    }
  }
}

// Load verification status
const loadVerificationStatus = async () => {
  try {
    const response = await api.get('/verification/status')
    verificationStatus.value = response.data
  } catch (error) {
    console.error('Failed to load verification status:', error)
  }
}

// Start editing
const startEdit = () => {
  // Populate edit form with current data
  editForm.value = {
    full_name: professionalInfo.value.full_name || '',
    license_number: professionalInfo.value.license_number || '',
    law_firm_name: professionalInfo.value.law_firm_name || '',
    specialty_areas: parseSpecialtyAreas(professionalInfo.value.specialty_areas),
    years_of_experience: professionalInfo.value.years_of_experience || 0,
    education_background: professionalInfo.value.education_background || '',
    bio: professionalInfo.value.bio || '',
    consultation_fee_cny: professionalInfo.value.consultation_fee_cny || 0,
    hourly_rate_cny: professionalInfo.value.hourly_rate_cny || 0,
    city_name: professionalInfo.value.city_name || '',
    province_name: professionalInfo.value.province_name || ''
  }
  editing.value = true
}

// Cancel editing
const cancelEdit = () => {
  editing.value = false
  editForm.value = {
    full_name: '',
    license_number: '',
    law_firm_name: '',
    specialty_areas: [],
    years_of_experience: 0,
    education_background: '',
    bio: '',
    consultation_fee_cny: 0,
    hourly_rate_cny: 0,
    city_name: '',
    province_name: ''
  }
}

// Add custom specialty
const addCustomSpecialty = () => {
  if (customSpecialty.value.trim() && !editForm.value.specialty_areas.includes(customSpecialty.value.trim())) {
    editForm.value.specialty_areas.push(customSpecialty.value.trim())
    customSpecialty.value = ''
  }
}

// Save changes
const saveChanges = async () => {
  if (editForm.value.specialty_areas.length === 0) {
    alert('请至少选择一个专业领域')
    return
  }

  saving.value = true
  try {
    // Submit as new verification request for admin review
    await api.post('/verification/update', {
      ...editForm.value,
      specialty_areas: JSON.stringify(editForm.value.specialty_areas)
    })

    alert('修改已提交！资料将在管理员审核后更新。')
    editing.value = false
    await loadVerificationStatus()
  } catch (error) {
    console.error('Failed to save changes:', error)
    alert(error.response?.data?.detail || '保存失败，请重试')
  } finally {
    saving.value = false
  }
}

// Helper functions
const parseSpecialtyAreas = (areas) => {
  if (!areas) return []
  if (Array.isArray(areas)) return areas
  try {
    const parsed = JSON.parse(areas)
    if (Array.isArray(parsed)) return parsed
  } catch (e) {
    // ignore
  }
  return []
}

const formatLocation = (province, city) => {
  if (!province && !city) return '-'
  if (!city) return province
  if (!province) return city
  return `${province} ${city}`
}

const formatDate = (dateString) => {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleDateString('zh-CN')
}

const getStatusIcon = (status) => {
  const icons = {
    pending: '⏳',
    approved: '✅',
    rejected: '❌'
  }
  return icons[status] || '📋'
}

const getStatusTitle = (status) => {
  const titles = {
    pending: '审核中',
    approved: '认证已通过',
    rejected: '认证未通过'
  }
  return titles[status] || '未知状态'
}

const getStatusMessage = (status) => {
  const messages = {
    pending: '您的资料正在审核中，请耐心等待',
    approved: '您已通过专业认证，可以接受案件了',
    rejected: '您的认证申请被拒绝，请重新提交'
  }
  return messages[status] || ''
}

const getAccountStatusText = (status) => {
  const statusMap = {
    active: '正常',
    inactive: '停用',
    suspended: '暂停'
  }
  return statusMap[status] || status
}

onMounted(async () => {
  loading.value = true
  await Promise.all([loadProfessionalInfo(), loadVerificationStatus()])
  loading.value = false
})
</script>

<style scoped>
.dashboard-container {
  display: flex;
  min-height: 100vh;
  background: #f5f7fa;
}

.main-content {
  flex: 1;
  padding: 32px;
  max-width: 1400px;
  margin: 0 auto;
}

.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 32px;
}

.dashboard-header h1 {
  font-size: 28px;
  color: #1a202c;
  font-weight: 600;
}

.loading-container {
  text-align: center;
  padding: 64px 0;
}

.loading {
  display: inline-block;
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

.profile-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

/* Status Banner */
.status-banner {
  padding: 20px 24px;
  border-radius: 12px;
  border-left: 4px solid;
}

.status-banner.status-pending {
  background: #fef3c7;
  border-color: #f59e0b;
}

.status-banner.status-approved {
  background: #d1fae5;
  border-color: #10b981;
}

.status-banner.status-rejected {
  background: #fee2e2;
  border-color: #ef4444;
}

.status-content {
  display: flex;
  align-items: center;
  gap: 16px;
}

.status-icon {
  font-size: 32px;
}

.status-text h3 {
  font-size: 18px;
  font-weight: 600;
  margin: 0 0 4px 0;
  color: #1a202c;
}

.status-text p {
  margin: 0;
  color: #4b5563;
  font-size: 14px;
}

/* Profile Card */
.profile-card {
  background: white;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24px;
  border-bottom: 1px solid #e5e7eb;
}

.card-header h2 {
  font-size: 20px;
  font-weight: 600;
  color: #1a202c;
  margin: 0;
}

.card-body {
  padding: 24px;
}

/* Info View */
.info-view {
  display: flex;
  flex-direction: column;
  gap: 32px;
}

.info-section h3 {
  font-size: 16px;
  font-weight: 600;
  color: #374151;
  margin: 0 0 16px 0;
  padding-bottom: 8px;
  border-bottom: 2px solid #667eea;
  display: inline-block;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.info-item .label {
  font-size: 13px;
  color: #6b7280;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.info-item .value {
  font-size: 15px;
  color: #1f2937;
  font-weight: 500;
}

.text-content {
  font-size: 15px;
  color: #4b5563;
  line-height: 1.7;
  white-space: pre-wrap;
}

.specialty-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.specialty-tag {
  padding: 6px 14px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 500;
}

.badge {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 13px;
  font-weight: 500;
}

.badge-success {
  background: #d1fae5;
  color: #065f46;
}

.badge-warning {
  background: #fef3c7;
  color: #92400e;
}

.badge-danger {
  background: #fee2e2;
  color: #991b1b;
}

/* Edit Form */
.edit-form {
  display: flex;
  flex-direction: column;
  gap: 32px;
}

.form-section h3 {
  font-size: 16px;
  font-weight: 600;
  color: #374151;
  margin: 0 0 16px 0;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-group label {
  font-size: 14px;
  font-weight: 500;
  color: #374151;
}

.input, .textarea {
  padding: 10px 14px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 15px;
  transition: all 0.2s;
}

.input:focus, .textarea:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.textarea {
  resize: vertical;
  font-family: inherit;
}

.specialty-selector {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.specialty-options {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 12px;
}

.specialty-option {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.specialty-option:hover {
  border-color: #667eea;
  background: #f5f7ff;
}

.specialty-option input[type="checkbox"] {
  cursor: pointer;
}

.custom-specialty {
  display: flex;
  gap: 12px;
}

.hint {
  font-size: 13px;
  color: #6b7280;
  margin: 0;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding-top: 16px;
  border-top: 1px solid #e5e7eb;
}

.form-notice {
  padding: 16px;
  background: #eff6ff;
  border-left: 4px solid #3b82f6;
  border-radius: 8px;
}

.form-notice p {
  margin: 0;
  font-size: 14px;
  color: #1e40af;
}

/* Buttons */
.btn {
  padding: 10px 20px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.btn-primary:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.btn-secondary {
  background: #f3f4f6;
  color: #374151;
}

.btn-secondary:hover {
  background: #e5e7eb;
}

.btn-sm {
  padding: 6px 12px;
  font-size: 13px;
}

.empty-state {
  text-align: center;
  padding: 48px 0;
  color: #9ca3af;
}

.empty-state p {
  margin: 0 0 16px 0;
  font-size: 16px;
}
</style>
