<template>
  <div class="dashboard-container">
    <Sidebar />
    
    <div class="main-content">
      <header class="dashboard-header">
        <h1>👤 个人资料</h1>
        <button class="btn btn-secondary" @click="$router.go(-1)">
          ← 返回
        </button>
      </header>

      <!-- Loading state -->
      <div v-if="isLoading" class="loading-container">
        <div class="loading"></div>
        <p>加载中...</p>
      </div>

      <!-- Profile Content -->
      <div v-else class="profile-content">
        <!-- Basic Info Card -->
        <div class="profile-card">
          <div class="card-header">
            <h2>基本信息</h2>
            <button 
              v-if="!editingBasicInfo"
              class="btn btn-sm btn-secondary" 
              @click="editingBasicInfo = true"
            >
              ✏️ 编辑
            </button>
          </div>
          <div class="card-body">
            <div v-if="!editingBasicInfo" class="info-view">
              <div class="info-row">
                <span class="label">姓名:</span>
                <span class="value">{{ profile.full_name || '未设置' }}</span>
              </div>
              <div class="info-row">
                <span class="label">手机号:</span>
                <span class="value">{{ profile.phone }}</span>
              </div>
              <div class="info-row">
                <span class="label">邮箱:</span>
                <span class="value">{{ profile.email || '未设置' }}</span>
              </div>
              <div class="info-row">
                <span class="label">用户类型:</span>
                <span class="value">{{ getRoleText(profile.role) }}</span>
              </div>
              <div class="info-row">
                <span class="label">注册时间:</span>
                <span class="value">{{ formatDateTime(profile.created_at) }}</span>
              </div>
            </div>
            <form v-else @submit.prevent="saveBasicInfo" class="edit-form">
              <div class="form-group">
                <label>姓名*</label>
                <input
                  v-model="editForm.full_name"
                  type="text"
                  class="input"
                  placeholder="请输入真实姓名"
                  required
                />
              </div>
              <div class="form-group">
                <label>邮箱</label>
                <input
                  v-model="editForm.email"
                  type="email"
                  class="input"
                  placeholder="请输入邮箱地址"
                />
              </div>
              <div class="form-actions">
                <button type="button" class="btn btn-secondary" @click="cancelEdit">
                  取消
                </button>
                <button type="submit" class="btn btn-primary" :disabled="isSaving">
                  {{ isSaving ? '保存中...' : '保存' }}
                </button>
              </div>
            </form>
          </div>
        </div>

        <!-- Professional Verification (for professional users) -->
        <div v-if="profile.role === 'professional'" class="profile-card">
          <div class="card-header">
            <h2>专业认证</h2>
            <span :class="['status-badge', `status-${verificationStatus}`]">
              {{ getVerificationStatusText(verificationStatus) }}
            </span>
          </div>
          <div class="card-body">
            <div v-if="verificationStatus === 'pending'" class="verification-pending">
              <p>您还未提交专业认证信息。完成认证后才能接受案件。</p>
              <button class="btn btn-primary" @click="showVerificationForm = true">
                提交认证信息
              </button>
            </div>
            <div v-else-if="verificationStatus === 'submitted'" class="verification-submitted">
              <p>✅ 您的认证资料已提交,正在审核中,请耐心等待。</p>
            </div>
            <div v-else-if="verificationStatus === 'approved'" class="verification-approved">
              <div class="verification-info">
                <div class="info-row">
                  <span class="label">专业领域:</span>
                  <span class="value">{{ verificationData.specialization }}</span>
                </div>
                <div class="info-row">
                  <span class="label">执业证号:</span>
                  <span class="value">{{ verificationData.license_number }}</span>
                </div>
                <div class="info-row">
                  <span class="label">工作单位:</span>
                  <span class="value">{{ verificationData.organization }}</span>
                </div>
              </div>
            </div>
            <div v-else-if="verificationStatus === 'rejected'" class="verification-rejected">
              <p>❌ 您的认证审核未通过。原因: {{ verificationData.rejection_reason }}</p>
              <button class="btn btn-primary" @click="showVerificationForm = true">
                重新提交
              </button>
            </div>
          </div>
        </div>

        <!-- Security Settings -->
        <div class="profile-card">
          <div class="card-header">
            <h2>安全设置</h2>
          </div>
          <div class="card-body">
            <div class="security-item">
              <div>
                <strong>修改密码</strong>
                <p class="security-desc">定期修改密码以保护账户安全</p>
              </div>
              <button class="btn btn-secondary" @click="showPasswordModal = true">
                修改
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Verification Form Modal -->
    <Modal v-if="showVerificationForm" @close="showVerificationForm = false">
      <template #header>
        <h2>专业认证信息</h2>
      </template>
      <template #body>
        <form @submit.prevent="submitVerification" class="verification-form">
          <div class="form-group">
            <label>专业领域*</label>
            <select v-model="verificationForm.specialization" class="input" required>
              <option value="">请选择</option>
              <option value="律师">律师</option>
              <option value="法律顾问">法律顾问</option>
              <option value="调解员">调解员</option>
              <option value="仲裁员">仲裁员</option>
              <option value="其他">其他</option>
            </select>
          </div>
          <div class="form-group">
            <label>执业证号*</label>
            <input
              v-model="verificationForm.license_number"
              type="text"
              class="input"
              placeholder="请输入执业证号"
              required
            />
          </div>
          <div class="form-group">
            <label>工作单位*</label>
            <input
              v-model="verificationForm.organization"
              type="text"
              class="input"
              placeholder="请输入工作单位"
              required
            />
          </div>
          <div class="form-group">
            <label>从业年限*</label>
            <input
              v-model.number="verificationForm.years_experience"
              type="number"
              class="input"
              placeholder="请输入从业年限"
              min="0"
              required
            />
          </div>
          <div class="form-group">
            <label>个人简介</label>
            <textarea
              v-model="verificationForm.bio"
              class="input"
              rows="4"
              placeholder="请简要介绍您的专业背景和经验"
            ></textarea>
          </div>
          <div class="modal-actions">
            <button type="button" class="btn btn-secondary" @click="showVerificationForm = false">
              取消
            </button>
            <button type="submit" class="btn btn-primary" :disabled="isSaving">
              {{ isSaving ? '提交中...' : '提交认证' }}
            </button>
          </div>
        </form>
      </template>
    </Modal>

    <!-- Change Password Modal -->
    <Modal v-if="showPasswordModal" @close="showPasswordModal = false">
      <template #header>
        <h2>修改密码</h2>
      </template>
      <template #body>
        <form @submit.prevent="changePassword" class="password-form">
          <div class="form-group">
            <label>当前密码*</label>
            <input
              v-model="passwordForm.current_password"
              type="password"
              class="input"
              required
            />
          </div>
          <div class="form-group">
            <label>新密码*</label>
            <input
              v-model="passwordForm.new_password"
              type="password"
              class="input"
              minlength="8"
              required
            />
            <small>密码至少8个字符</small>
          </div>
          <div class="form-group">
            <label>确认新密码*</label>
            <input
              v-model="passwordForm.confirm_password"
              type="password"
              class="input"
              required
            />
          </div>
          <div class="modal-actions">
            <button type="button" class="btn btn-secondary" @click="showPasswordModal = false">
              取消
            </button>
            <button type="submit" class="btn btn-primary" :disabled="isSaving">
              {{ isSaving ? '修改中...' : '确认修改' }}
            </button>
          </div>
        </form>
      </template>
    </Modal>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import Sidebar from '@/components/Sidebar.vue'
import Modal from '@/components/Modal.vue'
import api from '@/utils/api'

const router = useRouter()
const authStore = useAuthStore()

// State
const isLoading = ref(false)
const isSaving = ref(false)
const editingBasicInfo = ref(false)
const showVerificationForm = ref(false)
const showPasswordModal = ref(false)

const profile = ref({
  phone: '',
  full_name: '',
  email: '',
  role: 'user',
  created_at: ''
})

const editForm = ref({
  full_name: '',
  email: ''
})

const verificationStatus = ref('pending') // pending, submitted, approved, rejected
const verificationData = ref({})

const verificationForm = ref({
  specialization: '',
  license_number: '',
  organization: '',
  years_experience: 0,
  bio: ''
})

const passwordForm = ref({
  current_password: '',
  new_password: '',
  confirm_password: ''
})

// Methods
const loadProfile = async () => {
  isLoading.value = true
  try {
    const response = await api.get('/profile')
    profile.value = response.data
    editForm.value = {
      full_name: profile.value.full_name || '',
      email: profile.value.email || ''
    }
    
    // Load verification status if professional
    if (profile.value.role === 'professional') {
      await loadVerificationStatus()
    }
  } catch (error) {
    console.error('Failed to load profile:', error)
  } finally {
    isLoading.value = false
  }
}

const loadVerificationStatus = async () => {
  try {
    const response = await api.get('/professional/verification-status')
    verificationStatus.value = response.data.status
    verificationData.value = response.data.data || {}
  } catch (error) {
    console.error('Failed to load verification status:', error)
  }
}

const saveBasicInfo = async () => {
  isSaving.value = true
  try {
    await api.put('/profile', editForm.value)
    await loadProfile()
    editingBasicInfo.value = false
    alert('保存成功')
  } catch (error) {
    console.error('Failed to save profile:', error)
    alert('保存失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    isSaving.value = false
  }
}

const cancelEdit = () => {
  editForm.value = {
    full_name: profile.value.full_name || '',
    email: profile.value.email || ''
  }
  editingBasicInfo.value = false
}

const submitVerification = async () => {
  isSaving.value = true
  try {
    await api.post('/professional/verification', verificationForm.value)
    showVerificationForm.value = false
    await loadVerificationStatus()
    alert('认证信息已提交,请等待审核')
  } catch (error) {
    console.error('Failed to submit verification:', error)
    alert('提交失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    isSaving.value = false
  }
}

const changePassword = async () => {
  if (passwordForm.value.new_password !== passwordForm.value.confirm_password) {
    alert('两次输入的新密码不一致')
    return
  }
  
  isSaving.value = true
  try {
    await api.post('/auth/change-password', {
      current_password: passwordForm.value.current_password,
      new_password: passwordForm.value.new_password
    })
    showPasswordModal.value = false
    passwordForm.value = {
      current_password: '',
      new_password: '',
      confirm_password: ''
    }
    alert('密码修改成功')
  } catch (error) {
    console.error('Failed to change password:', error)
    alert('修改失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    isSaving.value = false
  }
}

const getRoleText = (role) => {
  const roleMap = {
    user: '普通用户',
    professional: '专业人员',
    admin: '管理员'
  }
  return roleMap[role] || role
}

const getVerificationStatusText = (status) => {
  const statusMap = {
    pending: '未认证',
    submitted: '审核中',
    approved: '已认证',
    rejected: '未通过'
  }
  return statusMap[status] || status
}

const formatDateTime = (dateString) => {
  return new Date(dateString).toLocaleString('zh-CN')
}

// Lifecycle
onMounted(() => {
  loadProfile()
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

.profile-content {
  max-width: 800px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.profile-card {
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  overflow: hidden;
}

.card-header {
  padding: 20px;
  border-bottom: 1px solid #e5e5e5;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header h2 {
  font-size: 20px;
  margin: 0;
}

.card-body {
  padding: 20px;
}

.info-view {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.info-row {
  display: flex;
  gap: 12px;
}

.info-row .label {
  font-weight: 600;
  color: #6c757d;
  min-width: 100px;
}

.info-row .value {
  color: #2d2d2d;
}

.edit-form, .verification-form, .password-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-group label {
  font-weight: 600;
  color: #2d2d2d;
  font-size: 14px;
}

.form-group small {
  color: #6c757d;
  font-size: 12px;
}

.input {
  padding: 10px 12px;
  border: 1px solid #dee2e6;
  border-radius: 8px;
  font-size: 14px;
  transition: border-color 0.2s;
}

.input:focus {
  outline: none;
  border-color: #667eea;
}

textarea.input {
  resize: vertical;
  font-family: inherit;
}

.form-actions, .modal-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  margin-top: 8px;
}

.status-badge {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
}

.status-pending { background: #fff3cd; color: #856404; }
.status-submitted { background: #cfe2ff; color: #084298; }
.status-approved { background: #d1e7dd; color: #0f5132; }
.status-rejected { background: #f8d7da; color: #842029; }

.verification-pending, .verification-submitted, .verification-approved, .verification-rejected {
  padding: 16px;
  border-radius: 8px;
}

.verification-pending {
  background: #fff3cd;
  color: #856404;
}

.verification-submitted {
  background: #d1ecf1;
  color: #0c5460;
}

.verification-approved {
  background: #d1e7dd;
  color: #0f5132;
}

.verification-rejected {
  background: #f8d7da;
  color: #721c24;
}

.verification-info {
  margin-top: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.security-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border: 1px solid #e5e5e5;
  border-radius: 8px;
}

.security-desc {
  color: #6c757d;
  font-size: 14px;
  margin-top: 4px;
}

.btn {
  padding: 10px 20px;
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

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.btn-secondary {
  background: #f8f9fa;
  color: #495057;
  border: 1px solid #dee2e6;
}

.btn-secondary:hover {
  background: #e9ecef;
}

.btn-sm {
  padding: 6px 12px;
  font-size: 13px;
}
</style>
