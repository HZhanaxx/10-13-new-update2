<template>
  <div class="verification-container">
    <Sidebar />
    
    <div class="main-content">
      <!-- Header -->
      <header class="page-header">
        <h1>🎓 专业认证</h1>
        <p class="subtitle">Professional Verification - 完成认证后即可接单</p>
      </header>

      <!-- Status Check -->
      <div v-if="loading" class="loading-container">
        <div class="loading"></div>
        <p>加载中...</p>
      </div>

      <!-- Already has pending/approved request -->
      <div v-else-if="verificationStatus" class="status-card">
        <div v-if="verificationStatus.status === 'pending'" class="status pending">
          <div class="status-icon">⏳</div>
          <h2>认证审核中</h2>
          <p>您的认证申请已提交,管理员正在审核中</p>
          <div class="status-details">
            <p><strong>提交时间:</strong> {{ formatDate(verificationStatus.created_at) }}</p>
            <p><strong>执业证号:</strong> {{ verificationStatus.license_number }}</p>
            <p><strong>律所:</strong> {{ verificationStatus.law_firm_name || '未填写' }}</p>
          </div>
          <p class="note">通常审核时间为1-3个工作日,请耐心等待</p>
        </div>

        <div v-else-if="verificationStatus.status === 'approved'" class="status approved">
          <div class="status-icon">✅</div>
          <h2>认证已通过</h2>
          <p>恭喜!您已完成专业认证,可以开始接单了</p>
          <div class="status-details">
            <p><strong>通过时间:</strong> {{ formatDate(verificationStatus.reviewed_at) }}</p>
            <p><strong>执业证号:</strong> {{ verificationStatus.license_number }}</p>
          </div>
          <button class="btn btn-primary" @click="$router.push('/case-pool')">
            前往案件池接单 →
          </button>
        </div>

        <div v-else-if="verificationStatus.status === 'rejected'" class="status rejected">
          <div class="status-icon">❌</div>
          <h2>认证未通过</h2>
          <p>很抱歉,您的认证申请未通过审核</p>
          <div class="status-details">
            <p><strong>审核时间:</strong> {{ formatDate(verificationStatus.reviewed_at) }}</p>
            <p><strong>原因:</strong> {{ verificationStatus.admin_notes || '未说明' }}</p>
          </div>
          <button class="btn btn-secondary" @click="retryVerification">
            重新申请认证
          </button>
        </div>
      </div>

      <!-- Verification Form -->
      <div v-else class="verification-form-container">
        <div class="info-banner">
          <h3>📝 为什么需要认证?</h3>
          <ul>
            <li>✅ 提高客户信任度,获得更多订单</li>
            <li>✅ 访问完整案件池,接收更多案件</li>
            <li>✅ 展示专业资质,提升个人品牌</li>
          </ul>
        </div>

        <form @submit.prevent="submitVerification" class="verification-form">
          <h2>填写认证信息</h2>

          <!-- Basic Info -->
          <div class="form-section">
            <h3>基本信息</h3>
            
            <div class="form-group">
              <label class="required">姓名</label>
              <input
                v-model="form.full_name"
                type="text"
                class="input"
                placeholder="请输入您的真实姓名"
                required
              />
            </div>

            <div class="form-group">
              <label class="required">执业证号</label>
              <input
                v-model="form.license_number"
                type="text"
                class="input"
                placeholder="例如: A12345678"
                required
              />
              <small>请输入您的律师执业证号</small>
            </div>

            <div class="form-group">
              <label>所在律所</label>
              <input
                v-model="form.law_firm_name"
                type="text"
                class="input"
                placeholder="例如: 北京某某律师事务所"
              />
            </div>
          </div>

          <!-- Professional Info -->
          <div class="form-section">
            <h3>专业信息</h3>

            <div class="form-group">
              <label>执业年限</label>
              <input
                v-model.number="form.years_of_experience"
                type="number"
                class="input"
                placeholder="例如: 5"
                min="0"
                max="50"
              />
              <small>您从事法律工作的年数</small>
            </div>

            <div class="form-group">
              <label>专业领域</label>
              <div class="checkbox-group">
                <label v-for="area in specialtyOptions" :key="area" class="checkbox-label">
                  <input
                    type="checkbox"
                    :value="area"
                    v-model="form.specialty_areas"
                  />
                  {{ area }}
                </label>
              </div>
              <small>请选择您擅长的法律领域(可多选)</small>
            </div>

            <div class="form-group">
              <label>教育背景</label>
              <textarea
                v-model="form.education_background"
                class="textarea"
                rows="3"
                placeholder="例如: 北京大学法学院 本科/硕士&#10;中国政法大学 法律硕士"
              ></textarea>
            </div>

            <div class="form-group">
              <label>个人简介</label>
              <textarea
                v-model="form.bio"
                class="textarea"
                rows="4"
                placeholder="请简要介绍您的从业经历、专长领域、成功案例等&#10;例如: 专注刑事辩护10年,擅长经济犯罪、职务犯罪案件,曾办理多起重大案件..."
              ></textarea>
            </div>
          </div>

          <!-- Location -->
          <div class="form-section">
            <h3>执业地区</h3>
            
            <div class="form-row">
              <div class="form-group">
                <label>省份</label>
                <input
                  v-model="form.province_name"
                  type="text"
                  class="input"
                  placeholder="例如: 北京市"
                />
              </div>

              <div class="form-group">
                <label>城市</label>
                <input
                  v-model="form.city_name"
                  type="text"
                  class="input"
                  placeholder="例如: 北京"
                />
              </div>
            </div>
          </div>

          <!-- Pricing -->
          <div class="form-section">
            <h3>收费标准</h3>
            
            <div class="form-row">
              <div class="form-group">
                <label>咨询费 (元/次)</label>
                <input
                  v-model.number="form.consultation_fee_cny"
                  type="number"
                  class="input"
                  placeholder="例如: 500"
                  min="0"
                  step="1"
                />
                <small>单次咨询服务费用</small>
              </div>

              <div class="form-group">
                <label>时薪 (元/小时)</label>
                <input
                  v-model.number="form.hourly_rate_cny"
                  type="number"
                  class="input"
                  placeholder="例如: 1000"
                  min="0"
                  step="1"
                />
                <small>按小时计费标准</small>
              </div>
            </div>
          </div>

          <!-- Document Upload -->
          <div class="form-section">
            <h3>上传证明文件</h3>
            
            <div class="upload-area">
              <input
                type="file"
                ref="fileInput"
                @change="handleFileSelect"
                accept=".pdf,.jpg,.jpeg,.png"
                multiple
                style="display: none"
              />
              
              <button
                type="button"
                class="btn btn-secondary"
                @click="$refs.fileInput.click()"
              >
                📎 选择文件
              </button>
              
              <p class="upload-hint">
                请上传执业证、身份证等证明文件 (支持 PDF、JPG、PNG,最多5个文件)
              </p>

              <div v-if="selectedFiles.length > 0" class="file-list">
                <div v-for="(file, index) in selectedFiles" :key="index" class="file-item">
                  <span class="file-name">{{ file.name }}</span>
                  <span class="file-size">{{ formatFileSize(file.size) }}</span>
                  <button type="button" @click="removeFile(index)" class="btn-remove">✕</button>
                </div>
              </div>
            </div>
          </div>

          <!-- Terms -->
          <div class="form-section">
            <label class="checkbox-label agreement">
              <input type="checkbox" v-model="agreedToTerms" required />
              我已阅读并同意<a href="#" @click.prevent="showTerms">《专业人士服务协议》</a>
            </label>
          </div>

          <!-- Submit -->
          <div class="form-actions">
            <button type="submit" class="btn btn-primary" :disabled="submitting">
              <span v-if="!submitting">提交认证申请</span>
              <span v-else>提交中...</span>
            </button>
            <button type="button" class="btn btn-secondary" @click="$router.push('/professional')">
              取消
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
const submitting = ref(false)
const verificationStatus = ref(null)
const agreedToTerms = ref(false)
const fileInput = ref(null)
const selectedFiles = ref([])

// Form data
const form = ref({
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

// Specialty options (matching case categories)
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

// Check existing verification status
const checkVerificationStatus = async () => {
  try {
    const response = await api.get('/verification/my-request')
    if (response.status !== 'none') {
      verificationStatus.value = response
    }
  } catch (error) {
    console.error('Failed to check verification status:', error)
  } finally {
    loading.value = false
  }
}

// Handle file selection
const handleFileSelect = (event) => {
  const files = Array.from(event.target.files)
  
  // Limit to 5 files
  if (selectedFiles.value.length + files.length > 5) {
    alert('最多只能上传5个文件')
    return
  }
  
  // Check file size (max 10MB per file)
  for (const file of files) {
    if (file.size > 10 * 1024 * 1024) {
      alert(`文件 ${file.name} 超过10MB限制`)
      return
    }
  }
  
  selectedFiles.value = [...selectedFiles.value, ...files]
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

// Format date
const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

// Submit verification
const submitVerification = async () => {
  // Validation
  if (!form.value.full_name || !form.value.license_number) {
    alert('请填写必填项:姓名和执业证号')
    return
  }
  
  if (!agreedToTerms.value) {
    alert('请阅读并同意服务协议')
    return
  }
  
  if (selectedFiles.value.length === 0) {
    alert('请至少上传一个证明文件')
    return
  }
  
  submitting.value = true
  
  try {
    // Create FormData
    const formData = new FormData()
    
    // Append form fields
    formData.append('full_name', form.value.full_name)
    formData.append('license_number', form.value.license_number)
    if (form.value.law_firm_name) formData.append('law_firm_name', form.value.law_firm_name)
    if (form.value.specialty_areas.length > 0) {
      formData.append('specialty_areas', form.value.specialty_areas.join(','))
    }
    if (form.value.years_of_experience) {
      formData.append('years_of_experience', form.value.years_of_experience)
    }
    if (form.value.education_background) {
      formData.append('education_background', form.value.education_background)
    }
    if (form.value.bio) formData.append('bio', form.value.bio)
    if (form.value.consultation_fee_cny) {
      formData.append('consultation_fee_cny', form.value.consultation_fee_cny)
    }
    if (form.value.hourly_rate_cny) {
      formData.append('hourly_rate_cny', form.value.hourly_rate_cny)
    }
    if (form.value.city_name) formData.append('city_name', form.value.city_name)
    if (form.value.province_name) formData.append('province_name', form.value.province_name)
    
    // Append files
    for (const file of selectedFiles.value) {
      formData.append('files', file)
    }
    
    // Submit
    await api.post('/verification/request', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
    
    alert('认证申请已提交!管理员将在1-3个工作日内审核')
    
    // Reload status
    await checkVerificationStatus()
    
  } catch (error) {
    console.error('Verification submission failed:', error)
    alert(error.response?.data?.detail || '提交失败,请重试')
  } finally {
    submitting.value = false
  }
}

// Retry verification (for rejected status)
const retryVerification = () => {
  verificationStatus.value = null
}

// Show terms
const showTerms = () => {
  alert('《专业人士服务协议》\n\n1. 您保证提交的所有信息真实有效\n2. 您同意遵守平台服务规则\n3. 您承诺提供专业、优质的法律服务\n4. 平台有权对违规行为进行处罚')
}

onMounted(() => {
  // Check if user is professional
  if (authStore.userRole !== 'professional') {
    alert('只有专业人士可以申请认证')
    router.push('/dashboard')
    return
  }
  
  checkVerificationStatus()
})
</script>

<style scoped>
.verification-container {
  display: flex;
  min-height: 100vh;
  background: #f5f7fa;
}

.main-content {
  flex: 1;
  padding: 40px;
  max-width: 1000px;
  margin: 0 auto;
}

.page-header {
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

/* Status Card */
.status-card {
  background: white;
  border-radius: 12px;
  padding: 48px;
  text-align: center;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}

.status {
  max-width: 500px;
  margin: 0 auto;
}

.status-icon {
  font-size: 64px;
  margin-bottom: 24px;
}

.status h2 {
  font-size: 28px;
  margin-bottom: 16px;
  color: #2d3748;
}

.status p {
  color: #718096;
  font-size: 16px;
  margin-bottom: 24px;
}

.status-details {
  background: #f7fafc;
  padding: 20px;
  border-radius: 8px;
  margin: 24px 0;
  text-align: left;
}

.status-details p {
  margin: 8px 0;
  color: #4a5568;
  font-size: 14px;
}

.note {
  font-size: 14px;
  color: #a0aec0;
  font-style: italic;
}

/* Info Banner */
.info-banner {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 32px;
  border-radius: 12px;
  margin-bottom: 32px;
}

.info-banner h3 {
  font-size: 24px;
  margin-bottom: 16px;
}

.info-banner ul {
  list-style: none;
}

.info-banner li {
  padding: 8px 0;
  font-size: 16px;
}

/* Form Container */
.verification-form-container {
  background: white;
  border-radius: 12px;
  padding: 40px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}

.verification-form h2 {
  font-size: 24px;
  color: #2d3748;
  margin-bottom: 32px;
}

.form-section {
  margin-bottom: 40px;
}

.form-section h3 {
  font-size: 18px;
  color: #4a5568;
  margin-bottom: 20px;
  padding-bottom: 12px;
  border-bottom: 2px solid #e2e8f0;
}

.form-group {
  margin-bottom: 24px;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

label {
  display: block;
  font-weight: 600;
  color: #4a5568;
  margin-bottom: 8px;
  font-size: 14px;
}

label.required::after {
  content: ' *';
  color: #e53e3e;
}

.input,
.textarea {
  width: 100%;
  padding: 12px 16px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 14px;
  transition: all 0.2s;
}

.input:focus,
.textarea:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

small {
  display: block;
  color: #a0aec0;
  font-size: 12px;
  margin-top: 6px;
}

/* Checkbox Group */
.checkbox-group {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 12px;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: normal;
  cursor: pointer;
  padding: 8px;
  border-radius: 6px;
  transition: background 0.2s;
}

.checkbox-label:hover {
  background: #f7fafc;
}

.checkbox-label input[type="checkbox"] {
  width: auto;
  margin: 0;
}

/* Upload Area */
.upload-area {
  border: 2px dashed #cbd5e0;
  border-radius: 8px;
  padding: 24px;
  text-align: center;
}

.upload-hint {
  color: #a0aec0;
  font-size: 14px;
  margin-top: 12px;
}

.file-list {
  margin-top: 20px;
  text-align: left;
}

.file-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: #f7fafc;
  border-radius: 6px;
  margin-bottom: 8px;
}

.file-name {
  flex: 1;
  font-size: 14px;
  color: #2d3748;
}

.file-size {
  font-size: 12px;
  color: #a0aec0;
}

.btn-remove {
  background: #fc8181;
  color: white;
  border: none;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  cursor: pointer;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* Agreement */
.agreement {
  padding: 16px;
  background: #f7fafc;
  border-radius: 8px;
}

.agreement a {
  color: #667eea;
  text-decoration: none;
}

.agreement a:hover {
  text-decoration: underline;
}

/* Form Actions */
.form-actions {
  display: flex;
  gap: 16px;
  justify-content: center;
  padding-top: 32px;
  border-top: 1px solid #e2e8f0;
}

/* Loading */
.loading-container {
  text-align: center;
  padding: 60px 20px;
}

.loading {
  width: 48px;
  height: 48px;
  border: 4px solid #e2e8f0;
  border-top-color: #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 16px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@media (max-width: 768px) {
  .main-content {
    padding: 20px;
  }
  
  .form-row {
    grid-template-columns: 1fr;
  }
  
  .checkbox-group {
    grid-template-columns: 1fr;
  }
}
</style>
