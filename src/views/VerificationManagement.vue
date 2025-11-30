<template>
  <div class="page-container">
    <Sidebar />
    <div class="main-content">
      <header class="page-header">
        <h1>✅ 专业认证审核</h1>
        <p class="subtitle">审批律师和专业人员的认证申请</p>
      </header>

      <!-- Stats -->
      <div class="stats-bar">
        <div class="stat-item">
          <span class="stat-label">待审核</span>
          <span class="stat-value pending">{{ stats.pending || 0 }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">已通过</span>
          <span class="stat-value approved">{{ stats.approved || 0 }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">已拒绝</span>
          <span class="stat-value rejected">{{ stats.rejected || 0 }}</span>
        </div>
      </div>

      <!-- Filter Tabs -->
      <div class="filter-tabs">
        <button
          :class="['tab', { active: filter === 'pending' }]"
          @click="filter = 'pending'; loadVerifications()"
        >
          待审核 ({{ stats.pending || 0 }})
        </button>
        <button
          :class="['tab', { active: filter === 'approved' }]"
          @click="filter = 'approved'; loadVerifications()"
        >
          已通过
        </button>
        <button
          :class="['tab', { active: filter === 'rejected' }]"
          @click="filter = 'rejected'; loadVerifications()"
        >
          已拒绝
        </button>
        <button
          :class="['tab', { active: filter === null }]"
          @click="filter = null; loadVerifications()"
        >
          全部
        </button>
      </div>

      <!-- Loading -->
      <div v-if="loading" class="loading-container">
        <div class="loading"></div>
        <p>加载中...</p>
      </div>

      <!-- Verifications List -->
      <div v-else class="verifications-list">
        <div v-if="verifications.length === 0" class="empty-state">
          <p>暂无认证申请</p>
        </div>

        <div
          v-for="verification in verifications"
          :key="verification.request_uuid"
          class="verification-card"
          @click="viewDetail(verification)"
        >
          <div class="card-header">
            <div class="user-info">
              <h3>{{ verification.full_name }}</h3>
              <span class="license">执业证号: {{ verification.license_number }}</span>
            </div>
            <span :class="['status-badge', verification.status]">
              {{ getStatusText(verification.status) }}
            </span>
          </div>

          <div class="card-body">
            <div class="info-grid">
              <div class="info-item">
                <span class="label">律所</span>
                <span class="value">{{ verification.law_firm_name || '-' }}</span>
              </div>
              <div class="info-item">
                <span class="label">从业年限</span>
                <span class="value">{{ verification.years_of_experience || '-' }}年</span>
              </div>
              <div class="info-item">
                <span class="label">专业领域</span>
                <span class="value">{{ formatSpecialtyAreas(verification.specialty_areas) }}</span>
              </div>
              <div class="info-item">
                <span class="label">提交时间</span>
                <span class="value">{{ formatDate(verification.created_at) }}</span>
              </div>
            </div>

            <div v-if="verification.document_count" class="document-info">
              📄 附件: {{ verification.document_count }} 个文件
            </div>
          </div>

          <div v-if="verification.status === 'pending'" class="card-actions">
            <button class="btn btn-approve" @click.stop="approveVerification(verification)">
              ✓ 通过
            </button>
            <button class="btn btn-reject" @click.stop="rejectVerification(verification)">
              ✗ 拒绝
            </button>
          </div>

          <div v-if="verification.admin_notes" class="admin-notes">
            <strong>审核备注:</strong> {{ verification.admin_notes }}
          </div>
        </div>
      </div>

      <!-- Detail Modal -->
      <div v-if="showDetailModal" class="modal-overlay" @click="closeDetailModal">
        <div class="modal-container detail-modal" @click.stop>
          <div class="modal-header">
            <h2>认证申请详情</h2>
            <button class="modal-close" @click="closeDetailModal">×</button>
          </div>

          <div v-if="selectedVerification" class="modal-body">
            <!-- Status -->
            <div class="detail-section">
              <span :class="['status-badge-large', selectedVerification.status]">
                {{ getStatusText(selectedVerification.status) }}
              </span>
            </div>

            <!-- Basic Info -->
            <div class="detail-section">
              <h3 class="section-title">基本信息</h3>
              <div class="detail-grid">
                <div class="detail-item">
                  <span class="label">姓名</span>
                  <span class="value">{{ selectedVerification.full_name }}</span>
                </div>
                <div class="detail-item">
                  <span class="label">执业证号</span>
                  <span class="value">{{ selectedVerification.license_number }}</span>
                </div>
                <div class="detail-item">
                  <span class="label">所属律所</span>
                  <span class="value">{{ selectedVerification.law_firm_name || '-' }}</span>
                </div>
                <div class="detail-item">
                  <span class="label">从业年限</span>
                  <span class="value">{{ selectedVerification.years_of_experience || '-' }}年</span>
                </div>
                <div class="detail-item">
                  <span class="label">所在地</span>
                  <span class="value">{{ selectedVerification.province_name }} {{ selectedVerification.city_name }}</span>
                </div>
              </div>
            </div>

            <!-- Specialty Areas -->
            <div v-if="selectedVerification.specialty_areas" class="detail-section">
              <h3 class="section-title">专业领域</h3>
              <div class="specialty-tags">
                <span
                  v-for="area in parseSpecialtyAreas(selectedVerification.specialty_areas)"
                  :key="area"
                  class="specialty-tag"
                >
                  {{ area }}
                </span>
              </div>
            </div>

            <!-- Education -->
            <div v-if="selectedVerification.education_background" class="detail-section">
              <h3 class="section-title">教育背景</h3>
              <p class="detail-text">{{ selectedVerification.education_background }}</p>
            </div>

            <!-- Bio -->
            <div v-if="selectedVerification.bio" class="detail-section">
              <h3 class="section-title">个人简介</h3>
              <p class="detail-text">{{ selectedVerification.bio }}</p>
            </div>

            <!-- Pricing -->
            <div class="detail-section">
              <h3 class="section-title">收费标准</h3>
              <div class="detail-grid">
                <div class="detail-item">
                  <span class="label">咨询费</span>
                  <span class="value">¥{{ selectedVerification.consultation_fee_cny || '未设置' }}</span>
                </div>
                <div class="detail-item">
                  <span class="label">时薪</span>
                  <span class="value">¥{{ selectedVerification.hourly_rate_cny || '未设置' }}</span>
                </div>
              </div>
            </div>

            <!-- Documents -->
            <div v-if="selectedVerification.documents && selectedVerification.documents.length > 0" class="detail-section">
              <h3 class="section-title">认证文件 ({{ selectedVerification.documents.length }})</h3>
              <div class="document-list">
                <div 
                  v-for="doc in selectedVerification.documents" 
                  :key="doc.document_id"
                  class="document-item clickable"
                  @click="viewDocument(doc)"
                >
                  <span class="icon">
                    {{ getDocumentIcon(doc.mime_type) }}
                  </span>
                  <div class="document-info">
                    <span class="document-name">{{ doc.file_name }}</span>
                    <span class="document-size">{{ formatFileSize(doc.file_size) }}</span>
                  </div>
                  <button class="btn-view" @click.stop="viewDocument(doc)">
                    👁️ 查看
                  </button>
                </div>
              </div>
            </div>

            <!-- Admin Notes -->
            <div v-if="selectedVerification.admin_notes" class="detail-section">
              <h3 class="section-title">审核备注</h3>
              <p class="detail-text admin-notes-text">{{ selectedVerification.admin_notes }}</p>
            </div>

            <!-- Review Info -->
            <div v-if="selectedVerification.reviewed_at" class="detail-section">
              <h3 class="section-title">审核信息</h3>
              <div class="detail-grid">
                <div class="detail-item">
                  <span class="label">审核时间</span>
                  <span class="value">{{ formatDate(selectedVerification.reviewed_at) }}</span>
                </div>
              </div>
            </div>
          </div>

          <div class="modal-footer">
            <button
              v-if="selectedVerification.status === 'pending'"
              class="btn btn-approve"
              @click="approveVerification(selectedVerification)"
            >
              ✓ 通过认证
            </button>
            <button
              v-if="selectedVerification.status === 'pending'"
              class="btn btn-reject"
              @click="rejectVerification(selectedVerification)"
            >
              ✗ 拒绝认证
            </button>
            <button class="btn btn-cancel" @click="closeDetailModal">关闭</button>
          </div>
        </div>
      </div>

      <!-- Reject Modal -->
      <div v-if="showRejectModal" class="modal-overlay" @click="showRejectModal = false">
        <div class="modal-container reject-modal" @click.stop>
          <div class="modal-header">
            <h2>拒绝认证</h2>
            <button class="modal-close" @click="showRejectModal = false">×</button>
          </div>

          <div class="modal-body">
            <p style="margin-bottom: 16px; color: #718096;">
              请说明拒绝原因,以便申请人了解并改进:
            </p>
            <textarea
              v-model="rejectNotes"
              class="form-input"
              rows="5"
              placeholder="例如: 执业证号无法验证，请提供清晰的证件照片"
            ></textarea>
          </div>

          <div class="modal-footer">
            <button class="btn btn-cancel" @click="showRejectModal = false">取消</button>
            <button class="btn btn-reject" @click="confirmReject">确认拒绝</button>
          </div>
        </div>
      </div>

      <!-- Image Viewer Modal -->
      <div v-if="showImageViewer" class="modal-overlay" @click="closeImageViewer">
        <div class="image-viewer-modal" @click.stop>
          <div class="image-viewer-header">
            <h3>{{ currentImage?.file_name }}</h3>
            <button class="modal-close" @click="closeImageViewer">×</button>
          </div>
          <div class="image-viewer-body">
            <img v-if="currentImageUrl" :src="currentImageUrl" :alt="currentImage?.file_name" />
          </div>
          <div class="image-viewer-footer">
            <button class="btn btn-primary" @click="downloadCurrentImage">
              ⬇️ 下载图片
            </button>
            <button class="btn btn-cancel" @click="closeImageViewer">关闭</button>
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
const verifications = ref([])
const filter = ref('pending')
const stats = ref({})
const showDetailModal = ref(false)
const selectedVerification = ref(null)
const showRejectModal = ref(false)
const rejectNotes = ref('')
const verificationToReject = ref(null)

// Image viewer state
const showImageViewer = ref(false)
const currentImage = ref(null)
const currentImageUrl = ref(null)

// Load stats
const loadStats = async () => {
  try {
    const response = await api.get('/admin/verifications/stats')
    stats.value = response.data
  } catch (error) {
    console.error('Failed to load verification stats:', error)
  }
}

// Load verifications
const loadVerifications = async () => {
  loading.value = true
  try {
    const params = {}
    if (filter.value) {
      params.status_filter = filter.value
    }

    const response = await api.get('/admin/verifications', { params })
    verifications.value = response.data
  } catch (error) {
    console.error('Failed to load verifications:', error)
  } finally {
    loading.value = false
  }
}

// View detail
const viewDetail = async (verification) => {
  try {
    // Fetch full detail with documents
    const response = await api.get(`/admin/verifications/${verification.request_uuid}`)
    selectedVerification.value = response.data
    showDetailModal.value = true
  } catch (error) {
    console.error('Failed to load verification detail:', error)
    alert('加载详情失败，请重试')
  }
}

// Close detail modal
const closeDetailModal = () => {
  showDetailModal.value = false
  selectedVerification.value = null
}

// Approve verification
const approveVerification = async (verification) => {
  if (!confirm(`确认通过 ${verification.full_name} 的认证申请？`)) {
    return
  }

  try {
    await api.post(`/admin/verifications/${verification.request_uuid}/approve`, {
      status: 'approved',
      admin_notes: '认证通过'
    })

    alert('认证已通过！')
    closeDetailModal()
    await Promise.all([loadStats(), loadVerifications()])
  } catch (error) {
    console.error('Failed to approve verification:', error)
    alert(error.response?.data?.detail || '操作失败，请重试')
  }
}

// Reject verification - open modal
const rejectVerification = (verification) => {
  verificationToReject.value = verification
  rejectNotes.value = ''
  showRejectModal.value = true
  closeDetailModal()
}

// Confirm reject
const confirmReject = async () => {
  if (!rejectNotes.value.trim()) {
    alert('请填写拒绝原因')
    return
  }

  const verification = verificationToReject.value

  try {
    await api.post(`/admin/verifications/${verification.request_uuid}/reject`, {
      status: 'rejected',
      admin_notes: rejectNotes.value
    })

    alert('已拒绝认证申请')
    showRejectModal.value = false
    verificationToReject.value = null
    await Promise.all([loadStats(), loadVerifications()])
  } catch (error) {
    console.error('Failed to reject verification:', error)
    alert(error.response?.data?.detail || '操作失败，请重试')
  }
}

// Format specialty areas
const formatSpecialtyAreas = (areas) => {
  if (!areas) return '-'
  if (Array.isArray(areas)) {
    return areas.slice(0, 2).join(', ') + (areas.length > 2 ? '...' : '')
  }
  try {
    const parsed = JSON.parse(areas)
    if (Array.isArray(parsed)) {
      return parsed.slice(0, 2).join(', ') + (parsed.length > 2 ? '...' : '')
    }
  } catch (e) {
    // ignore
  }
  return areas
}

// Parse specialty areas
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

// Get status text
const getStatusText = (status) => {
  const statusMap = {
    pending: '待审核',
    approved: '已通过',
    rejected: '已拒绝',
    revoked: '已撤销'
  }
  return statusMap[status] || status
}

// Format date
const formatDate = (dateString) => {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// Get document icon based on mime type
const getDocumentIcon = (mimeType) => {
  if (!mimeType) return '📄'
  if (mimeType.includes('image')) return '🖼️'
  if (mimeType.includes('pdf')) return '📕'
  if (mimeType.includes('word') || mimeType.includes('document')) return '📝'
  return '📄'
}

// Format file size
const formatFileSize = (bytes) => {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
}

// View/download document
const viewDocument = async (doc) => {
  try {
    // For images, use inline viewer
    if (doc.mime_type && doc.mime_type.includes('image')) {
      await viewImageInline(doc)
      return
    }
    
    // For other files (PDFs, etc), fetch and open in new tab or download
    const response = await api.get(`/admin/verifications/documents/${doc.document_id}`, {
      responseType: 'blob'
    })
    
    // Ensure we have a blob
    if (!(response.data instanceof Blob)) {
      console.error('Response is not a Blob:', response.data)
      throw new Error('服务器返回的不是有效的文件数据')
    }
    
    // Create blob from response
    const blob = response.data
    const url = window.URL.createObjectURL(blob)
    
    // Open in new tab or download based on file type
    if (doc.mime_type && doc.mime_type.includes('pdf')) {
      // View PDF in new tab
      const newWindow = window.open(url, '_blank')
      
      // Clean up blob URL after the new window has loaded
      if (newWindow) {
        setTimeout(() => {
          window.URL.revokeObjectURL(url)
        }, 30000) // 30 seconds
      }
    } else {
      // Download file
      const link = document.createElement('a')
      link.href = url
      link.download = doc.file_name
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      
      // Clean up immediately after download starts
      setTimeout(() => window.URL.revokeObjectURL(url), 1000)
    }
  } catch (error) {
    console.error('Failed to load document:', error)
    alert('无法加载文件，请重试: ' + (error.message || error))
  }
}

// View image inline in modal - Using data URL instead of blob URL
const viewImageInline = async (doc) => {
  try {
    console.log('🔵 Loading image:', doc.file_name, 'Type:', doc.mime_type)
    currentImage.value = doc
    
    // Fetch image with authentication
    const response = await api.get(`/admin/verifications/documents/${doc.document_id}`, {
      responseType: 'blob'
    })
    
    console.log('🔵 Response received:', {
      status: response.status,
      dataType: response.data?.constructor?.name,
      isBlob: response.data instanceof Blob,
      size: response.data?.size,
      type: response.data?.type
    })
    
    // Ensure we have a blob
    if (!(response.data instanceof Blob)) {
      console.error('❌ Response is not a Blob:', response.data)
      throw new Error('服务器返回的不是有效的图片数据')
    }
    
    const blob = response.data
    
    // Check if blob is empty
    if (blob.size === 0) {
      console.error('❌ Blob is empty!')
      throw new Error('收到空文件')
    }
    
    console.log('🔵 Blob details:', {
      size: blob.size,
      type: blob.type
    })
    
    // Convert blob to data URL using FileReader
    // This avoids blob URL issues
    const reader = new FileReader()
    
    reader.onload = (e) => {
      const dataUrl = e.target.result
      console.log('✅ Data URL created, length:', dataUrl.length)
      currentImageUrl.value = dataUrl
      showImageViewer.value = true
    }
    
    reader.onerror = (e) => {
      console.error('❌ FileReader error:', e)
      throw new Error('无法读取图片数据')
    }
    
    // Read blob as data URL
    reader.readAsDataURL(blob)
    
  } catch (error) {
    console.error('❌ Failed to load image:', error)
    alert('无法加载图片，请重试: ' + (error.message || error))
  }
}

// Close image viewer
const closeImageViewer = () => {
  showImageViewer.value = false
  // No need to revoke data URLs (they're just strings)
  currentImageUrl.value = null
  currentImage.value = null
}

// Download current image
const downloadCurrentImage = () => {
  if (currentImageUrl.value && currentImage.value) {
    const link = document.createElement('a')
    link.href = currentImageUrl.value
    link.download = currentImage.value.file_name
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }
}

onMounted(async () => {
  await Promise.all([loadStats(), loadVerifications()])
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

.page-header h1 {
  font-size: 32px;
  color: #2d3748;
  margin-bottom: 8px;
}

.subtitle {
  color: #718096;
  font-size: 16px;
  margin-bottom: 32px;
}

/* Stats Bar */
.stats-bar {
  display: flex;
  gap: 24px;
  margin-bottom: 24px;
  padding: 20px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.stat-item {
  flex: 1;
  text-align: center;
}

.stat-label {
  display: block;
  font-size: 13px;
  color: #9ca3af;
  margin-bottom: 8px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.stat-value {
  display: block;
  font-size: 32px;
  font-weight: 700;
}

.stat-value.pending {
  color: #f59e0b;
}

.stat-value.approved {
  color: #10b981;
}

.stat-value.rejected {
  color: #ef4444;
}

/* Filter Tabs */
.filter-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 24px;
}

.tab {
  padding: 10px 20px;
  border: none;
  background: white;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  color: #6b7280;
  transition: all 0.2s;
}

.tab:hover {
  background: #f3f4f6;
}

.tab.active {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

/* Loading */
.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 300px;
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

/* Verifications List */
.verifications-list {
  display: grid;
  gap: 16px;
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
  background: white;
  border-radius: 12px;
  color: #a0aec0;
}

.verification-card {
  background: white;
  border-radius: 12px;
  padding: 24px;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.verification-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
}

.user-info h3 {
  font-size: 20px;
  color: #2d3748;
  margin-bottom: 4px;
}

.license {
  font-size: 13px;
  color: #9ca3af;
}

.status-badge {
  padding: 6px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
}

.status-badge.pending {
  background: #fef5e7;
  color: #f59e0b;
}

.status-badge.approved {
  background: #e8f8f5;
  color: #10b981;
}

.status-badge.rejected {
  background: #fee;
  color: #ef4444;
}

.card-body {
  margin-bottom: 16px;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 16px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.info-item .label {
  font-size: 12px;
  color: #9ca3af;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.info-item .value {
  font-size: 14px;
  color: #374151;
  font-weight: 500;
}

.document-info {
  padding: 12px;
  background: #f9fafb;
  border-radius: 8px;
  font-size: 14px;
  color: #4b5563;
}

.card-actions {
  display: flex;
  gap: 12px;
  padding-top: 16px;
  border-top: 1px solid #e5e7eb;
}

.btn {
  padding: 10px 20px;
  border-radius: 8px;
  border: none;
  font-weight: 600;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-approve {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  color: white;
  flex: 1;
}

.btn-approve:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
}

.btn-reject {
  background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
  color: white;
  flex: 1;
}

.btn-reject:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3);
}

.btn-cancel {
  background: #f3f4f6;
  color: #6b7280;
}

.admin-notes {
  margin-top: 12px;
  padding: 12px;
  background: #f9fafb;
  border-left: 3px solid #667eea;
  border-radius: 4px;
  font-size: 13px;
  color: #4b5563;
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
  max-width: 800px;
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

/* Detail Modal */
.status-badge-large {
  display: inline-block;
  padding: 8px 16px;
  border-radius: 16px;
  font-size: 14px;
  font-weight: 600;
}

.status-badge-large.pending {
  background: #fef5e7;
  color: #f59e0b;
}

.status-badge-large.approved {
  background: #e8f8f5;
  color: #10b981;
}

.status-badge-large.rejected {
  background: #fee;
  color: #ef4444;
}

.detail-section {
  margin-bottom: 24px;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: #374151;
  margin-bottom: 16px;
  padding-bottom: 8px;
  border-bottom: 2px solid #e5e7eb;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.detail-item .label {
  font-size: 12px;
  color: #9ca3af;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.detail-item .value {
  font-size: 15px;
  color: #374151;
  font-weight: 500;
}

.detail-text {
  font-size: 15px;
  color: #4b5563;
  line-height: 1.6;
  white-space: pre-wrap;
}

.admin-notes-text {
  background: #f9fafb;
  padding: 16px;
  border-left: 3px solid #667eea;
  border-radius: 4px;
}

.specialty-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.specialty-tag {
  padding: 6px 12px;
  background: #eef2ff;
  color: #667eea;
  border-radius: 16px;
  font-size: 13px;
  font-weight: 500;
}

.document-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.document-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: #f9fafb;
  border-radius: 8px;
  font-size: 14px;
  color: #4b5563;
  transition: all 0.2s;
}

.document-item.clickable {
  cursor: pointer;
  border: 1px solid #e5e7eb;
}

.document-item.clickable:hover {
  background: #ffffff;
  border-color: #667eea;
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.15);
  transform: translateX(2px);
}

.document-item .icon {
  font-size: 24px;
  flex-shrink: 0;
}

.document-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
  overflow: hidden;
}

.document-name {
  font-weight: 500;
  color: #374151;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.document-size {
  font-size: 12px;
  color: #9ca3af;
}

.btn-view {
  padding: 6px 12px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
  flex-shrink: 0;
  font-weight: 500;
}

.btn-view:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(102, 126, 234, 0.3);
}

/* Reject Modal */
.form-input {
  width: 100%;
  padding: 12px 16px;
  border: 2px solid #e5e7eb;
  border-radius: 10px;
  font-size: 15px;
  transition: all 0.2s;
  font-family: inherit;
  resize: vertical;
}

.form-input:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

/* Image Viewer Modal */
.image-viewer-modal {
  background: white;
  border-radius: 16px;
  width: 90%;
  max-width: 1000px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

.image-viewer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid #e2e8f0;
}

.image-viewer-header h3 {
  margin: 0;
  font-size: 18px;
  color: #2d3748;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.image-viewer-body {
  flex: 1;
  padding: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: auto;
  background: #f9fafb;
}

.image-viewer-body img {
  max-width: 100%;
  max-height: 70vh;
  object-fit: contain;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.image-viewer-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 24px;
  border-top: 1px solid #e2e8f0;
  background: #f9fafb;
}

@media (max-width: 768px) {
  .main-content {
    padding: 20px;
  }

  .stats-bar {
    flex-direction: column;
  }

  .info-grid,
  .detail-grid {
    grid-template-columns: 1fr;
  }
}
</style>
