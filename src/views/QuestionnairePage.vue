<template>
  <div class="questionnaire-page">
    <div class="questionnaire-wrapper">
      <!-- Back Button -->
      <div class="back-section">
        <button @click="goBack" class="btn-back" :disabled="isSubmitting">
          ← 返回
        </button>
        <span v-if="sessionId" class="session-info">
          会话: {{ sessionId?.slice(0, 12) }}...
        </span>
      </div>

      <!-- Header -->
      <div class="header">
        <h1>{{ title }}</h1>
        <div v-if="progress" class="progress-section">
          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: progress.percentage + '%' }"></div>
          </div>
          <p class="progress-text">
            {{ partInfo?.name || '问卷进行中' }} - 进度: {{ progress.current }} / {{ progress.total }}
          </p>
        </div>
      </div>

      <!-- Loading State -->
      <div v-if="loading" class="loading-container">
        <div class="spinner"></div>
        <p>{{ loadingText }}</p>
      </div>

      <!-- Error State -->
      <div v-else-if="error" class="error-box">
        <div class="error-icon">⚠️</div>
        <p>{{ error }}</p>
        <button @click="retryInit" class="btn btn-primary">重试</button>
      </div>

      <!-- Part Transition Message -->
      <div v-else-if="transitionMessage" class="transition-box">
        <div class="transition-icon">✨</div>
        <p>{{ transitionMessage }}</p>
        <button @click="continueToNext" class="btn btn-primary">继续</button>
      </div>

      <!-- Summary Review -->
      <div v-else-if="showSummaryReview && currentSummary" class="summary-review-box">
        <div class="summary-header">
          <h2>📊 第{{ currentPart }}部分分析结果</h2>
        </div>
        <div class="summary-content">
          <div class="ai-badge">🤖 AI 分析</div>
          <p v-html="formatText(currentSummary)"></p>
        </div>
        <div class="summary-actions">
          <button @click="requestRegenerate" class="btn btn-outline" :disabled="isRegenerating">
            {{ isRegenerating ? '重新生成中...' : '🔄 重新生成' }}
          </button>
          <button @click="confirmSummary" class="btn btn-primary">
            ✓ 确认并继续
          </button>
        </div>
      </div>

      <!-- Question Box -->
      <div v-else-if="currentQuestion" class="question-box">
        <div class="question-header">
          <span class="question-number">Q{{ currentQuestion.id?.replace('q', '') }}</span>
          <h2 class="question-text" v-html="formatText(currentQuestion.text)"></h2>
          <p v-if="currentQuestion.description" class="question-description">
            {{ currentQuestion.description }}
          </p>
        </div>

        <div class="question-content">
          <!-- Radio Type -->
          <div v-if="currentQuestion.type === 'radio'" class="options-list">
            <label 
              v-for="option in currentQuestion.options" 
              :key="option" 
              class="option-item"
              :class="{ selected: currentAnswer === option }"
            >
              <input 
                type="radio" 
                :value="option" 
                v-model="currentAnswer"
                :name="currentQuestion.id"
              />
              <span class="option-label">{{ option }}</span>
            </label>
          </div>

          <!-- Checkbox Type -->
          <div v-else-if="currentQuestion.type === 'checkbox'" class="options-list">
            <label 
              v-for="option in currentQuestion.options" 
              :key="option" 
              class="option-item"
              :class="{ selected: currentAnswerArray.includes(option) }"
            >
              <input 
                type="checkbox" 
                :value="option" 
                v-model="currentAnswerArray"
              />
              <span class="option-label">{{ option }}</span>
            </label>
          </div>

          <!-- Select Type -->
          <div v-else-if="currentQuestion.type === 'select'" class="select-wrapper">
            <select v-model="currentAnswer" class="form-select">
              <option value="">请选择...</option>
              <option v-for="option in currentQuestion.options" :key="option" :value="option">
                {{ option }}
              </option>
            </select>
          </div>

          <!-- Text Type -->
          <div v-else-if="currentQuestion.type === 'text'" class="input-wrapper">
            <input 
              type="text" 
              v-model="currentAnswer"
              :placeholder="currentQuestion.placeholder || '请输入...'"
              class="form-input"
            />
          </div>

          <!-- Textarea Type -->
          <div v-else-if="currentQuestion.type === 'textarea'" class="input-wrapper">
            <textarea 
              v-model="currentAnswer"
              :placeholder="currentQuestion.placeholder || '请详细描述...'"
              class="form-textarea"
              rows="4"
            ></textarea>
          </div>

          <!-- Form Type -->
          <div v-else-if="currentQuestion.type === 'form'" class="form-fields">
            <div v-for="field in currentQuestion.fields" :key="field.name" class="form-field">
              <label class="field-label">
                {{ field.label }}
                <span v-if="field.required" class="required">*</span>
              </label>
              
              <input 
                v-if="field.type === 'text' || field.type === 'date' || field.type === 'datetime-local'"
                :type="field.type"
                v-model="formData[field.name]"
                class="form-input"
              />
              
              <div v-else-if="field.type === 'radio'" class="field-options">
                <label v-for="opt in field.options" :key="opt" class="inline-option">
                  <input type="radio" :value="opt" v-model="formData[field.name]" />
                  {{ opt }}
                </label>
              </div>
            </div>
          </div>

          <!-- Upload Type -->
          <div v-else-if="currentQuestion.type === 'upload'" class="upload-section">
            <div 
              class="upload-dropzone"
              :class="{ 'drag-over': isDragging }"
              @dragover.prevent="isDragging = true"
              @dragleave="isDragging = false"
              @drop.prevent="handleFileDrop"
            >
              <input 
                type="file" 
                ref="fileInput"
                @change="handleFileSelect"
                :accept="currentQuestion.accept_types?.join(',') || '*'"
                class="file-input"
              />
              <div class="upload-content">
                <span class="upload-icon">📎</span>
                <p>拖拽文件到此处或 <span class="link" @click="$refs.fileInput.click()">点击上传</span></p>
                <p class="upload-hint">支持 PDF、图片格式</p>
              </div>
            </div>
            
            <div v-if="uploadedFile" class="uploaded-file">
              <span class="file-icon">📄</span>
              <span class="file-name">{{ uploadedFile.name }}</span>
              <span v-if="isUploading" class="uploading">上传中...</span>
              <span v-else-if="uploadedFile.ocrText" class="ocr-badge">已OCR识别</span>
              <button @click="removeFile" class="remove-file">×</button>
            </div>
          </div>

          <!-- Message Type -->
          <div v-else-if="currentQuestion.type === 'message'" class="message-box">
            <div class="message-content" v-html="formatText(currentQuestion.text)"></div>
          </div>
        </div>

        <!-- Actions -->
        <div class="actions">
          <button 
            @click="submitAnswer" 
            class="btn btn-primary"
            :disabled="!canSubmit || isSubmitting"
          >
            {{ isSubmitting ? '提交中...' : getSubmitButtonText() }}
            <span v-if="!isSubmitting">→</span>
          </button>
        </div>
      </div>

      <!-- Completion Box -->
      <div v-else-if="completed && completionData" class="completion-box">
        <div class="success-icon">✓</div>
        <h2>{{ completionData.title || '问卷完成' }}</h2>
        <p v-html="formatText(completionData.message || '感谢您完成问卷！')"></p>
        
        <div v-if="completionData.submission_id" class="case-info">
          <span class="label">提交编号：</span>
          <span class="value">{{ completionData.submission_id }}</span>
        </div>

        <div v-if="completionData.case_created && completionData.case_uuid" class="case-created-notice">
          <div class="notice-icon">📋</div>
          <p>已为您创建案件，专业律师将会查看您的案件信息。</p>
        </div>

        <div v-if="completionData.summaries" class="summaries-review">
          <h3>📋 AI 分析总结</h3>
          <div v-for="(summary, part) in completionData.summaries" :key="part" class="summary-item">
            <strong>{{ getSummaryTitle(part) }}</strong>
            <p>{{ summary.content || summary }}</p>
          </div>
        </div>

        <div class="completion-actions">
          <button 
            v-if="completionData.case_uuid"
            @click="viewCase"
            class="btn btn-primary"
          >
            查看案件详情
          </button>
          <button 
            @click="goToDashboard"
            class="btn btn-outline"
          >
            返回首页
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import api from '@/utils/api'
import DOMPurify from 'dompurify'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

// State
const sessionId = ref(null)
const loading = ref(true)
const loadingText = ref('正在加载问卷...')
const error = ref(null)
const title = ref('交通事故法律咨询')

// Question state
const currentQuestion = ref(null)
const currentAnswer = ref('')
const currentAnswerArray = ref([])
const formData = ref({})
const partInfo = ref(null)
const progress = ref(null)
const currentPart = ref(1)

// File upload
const uploadedFile = ref(null)
const isUploading = ref(false)
const isDragging = ref(false)
const fileInput = ref(null)

// Summary
const showSummaryReview = ref(false)
const currentSummary = ref(null)
const isRegenerating = ref(false)

// Transition
const transitionMessage = ref(null)

// Completion
const completed = ref(false)
const completionData = ref(null)

// Submission state
const isSubmitting = ref(false)

// Computed
const canSubmit = computed(() => {
  if (!currentQuestion.value) return false
  
  const q = currentQuestion.value
  
  // Optional questions can be skipped
  if (!q.required) return true
  
  switch (q.type) {
    case 'radio':
    case 'select':
    case 'text':
    case 'textarea':
      return currentAnswer.value !== '' && currentAnswer.value !== null
    case 'checkbox':
      return currentAnswerArray.value.length > 0
    case 'form':
      // Check required fields
      if (!q.fields) return true
      for (const field of q.fields) {
        if (field.required && !formData.value[field.name]) {
          return false
        }
      }
      return true
    case 'upload':
      return !q.required || uploadedFile.value !== null
    case 'message':
      return true
    default:
      return true
  }
})

// Methods
const formatText = (text) => {
  if (!text) return ''
  return DOMPurify.sanitize(text.replace(/\n/g, '<br>'), {
    ALLOWED_TAGS: ['br', 'b', 'strong', 'i', 'em', 'p']
  })
}

const getSubmitButtonText = () => {
  if (!currentQuestion.value) return '继续'
  
  if (currentQuestion.value.type === 'upload' && !currentQuestion.value.required && !uploadedFile.value) {
    return '跳过'
  }
  
  return '继续'
}

const getSummaryTitle = (partKey) => {
  const titles = {
    'part1': '第一部分：基本信息',
    'part2': '第二部分：事故过程',
    'part3': '第三部分：保险与赔偿'
  }
  return titles[partKey] || partKey
}

// Initialize
const initQuestionnaire = async () => {
  loading.value = true
  loadingText.value = '正在初始化问卷...'
  
  try {
    sessionId.value = route.params.sessionId
    
    // Check for stored session data
    const storedSession = sessionStorage.getItem('questionnaire_session')
    if (storedSession) {
      const sessionData = JSON.parse(storedSession)
      
      // If we have initial question data, use it
      if (sessionData.question && sessionData.sessionId === sessionId.value) {
        currentQuestion.value = sessionData.question
        partInfo.value = sessionData.partInfo
        progress.value = sessionData.progress
        loading.value = false
        return
      }
    }
    
    // Otherwise fetch session status
    const res = await api.get(`/workflow/questionnaire/session/${sessionId.value}`)
    
    if (res.data.status === 'completed') {
      completed.value = true
      completionData.value = res.data
    } else {
      // Session is in progress, need to submit empty answer to get current question
      // Or we can add a "get current question" endpoint
      error.value = '请从头开始问卷'
    }
    
  } catch (e) {
    console.error('Init error:', e)
    error.value = e.response?.data?.detail || '加载问卷失败'
  } finally {
    loading.value = false
  }
}

const retryInit = () => {
  error.value = null
  initQuestionnaire()
}

const goBack = () => {
  if (confirm('确定要退出问卷吗？进度将被保存。')) {
    router.push('/dashboard')
  }
}

const goToDashboard = () => {
  sessionStorage.removeItem('questionnaire_session')
  router.push('/dashboard')
}

const viewCase = () => {
  if (completionData.value?.case_uuid) {
    router.push(`/case/${completionData.value.case_uuid}`)
  }
}

// Submit answer
const submitAnswer = async () => {
  if (!canSubmit.value || isSubmitting.value) return
  
  isSubmitting.value = true
  loadingText.value = '正在提交答案...'
  
  try {
    // Prepare answer based on question type
    let answerValue = currentAnswer.value
    let fileData = null
    
    switch (currentQuestion.value.type) {
      case 'checkbox':
        answerValue = currentAnswerArray.value
        break
      case 'form':
        answerValue = { ...formData.value }
        break
      case 'upload':
        if (uploadedFile.value) {
          answerValue = uploadedFile.value.name
          fileData = {
            filename: uploadedFile.value.name,
            content_type: uploadedFile.value.type,
            base64: uploadedFile.value.base64
          }
        } else {
          answerValue = null
        }
        break
    }
    
    // Submit to LangGraph workflow API
    const res = await api.post('/workflow/questionnaire/answer', {
      session_id: sessionId.value,
      question_id: currentQuestion.value.id,
      answer: answerValue,
      file: fileData
    })
    
    // Handle response
    if (res.data.completed) {
      // Questionnaire completed
      completed.value = true
      completionData.value = {
        title: '问卷完成',
        message: '感谢您完成问卷！我们已收到您的信息。',
        submission_id: res.data.submission_id,
        case_uuid: res.data.case_uuid,
        case_created: res.data.case_created,
        summaries: res.data.summaries
      }
      sessionStorage.removeItem('questionnaire_session')
    } else if (res.data.question) {
      // Next question
      currentQuestion.value = res.data.question
      partInfo.value = res.data.part_info
      progress.value = res.data.progress
      
      // Reset answer state
      resetAnswerState()
      
      // Check for part transition
      if (partInfo.value && currentPart.value !== partInfo.value.current) {
        currentPart.value = partInfo.value.current
      }
    } else if (res.data.status === 'generating_summary') {
      // Summary being generated
      loadingText.value = 'AI正在分析您的回答...'
      // Poll for completion or wait for next response
    }
    
  } catch (e) {
    console.error('Submit error:', e)
    error.value = e.response?.data?.detail || '提交失败，请重试'
  } finally {
    isSubmitting.value = false
  }
}

const resetAnswerState = () => {
  currentAnswer.value = ''
  currentAnswerArray.value = []
  formData.value = {}
  uploadedFile.value = null
}

// Summary functions
const requestRegenerate = async () => {
  isRegenerating.value = true
  
  try {
    const res = await api.post('/workflow/questionnaire/regenerate-summary', {
      session_id: sessionId.value,
      part_number: currentPart.value
    })
    
    if (res.data.summary) {
      currentSummary.value = res.data.summary.content || res.data.summary
    }
  } catch (e) {
    console.error('Regenerate error:', e)
  } finally {
    isRegenerating.value = false
  }
}

const confirmSummary = () => {
  showSummaryReview.value = false
  currentSummary.value = null
}

const continueToNext = () => {
  transitionMessage.value = null
}

// File upload functions
const handleFileSelect = async (event) => {
  const file = event.target.files[0]
  if (file) {
    await processFile(file)
  }
}

const handleFileDrop = async (event) => {
  isDragging.value = false
  const file = event.dataTransfer.files[0]
  if (file) {
    await processFile(file)
  }
}

const processFile = async (file) => {
  isUploading.value = true
  
  try {
    // Convert to base64
    const base64 = await fileToBase64(file)
    
    uploadedFile.value = {
      name: file.name,
      type: file.type,
      size: file.size,
      base64: base64
    }
  } catch (e) {
    console.error('File processing error:', e)
    alert('文件处理失败')
  } finally {
    isUploading.value = false
  }
}

const fileToBase64 = (file) => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.readAsDataURL(file)
    reader.onload = () => {
      // Extract base64 content (remove data:*/*;base64, prefix)
      const base64 = reader.result.split(',')[1]
      resolve(base64)
    }
    reader.onerror = reject
  })
}

const removeFile = () => {
  uploadedFile.value = null
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}

// Lifecycle
onMounted(() => {
  initQuestionnaire()
})
</script>

<style scoped>
.questionnaire-page {
  min-height: 100vh;
  background: linear-gradient(135deg, #f5f7fa 0%, #e4e8eb 100%);
  padding: 20px;
}

.questionnaire-wrapper {
  max-width: 700px;
  margin: 0 auto;
}

.back-section {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.btn-back {
  background: white;
  border: 1px solid #e2e8f0;
  padding: 8px 16px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}
.btn-back:hover { background: #f7fafc; }
.btn-back:disabled { opacity: 0.5; cursor: not-allowed; }

.session-info {
  font-size: 12px;
  color: #a0aec0;
  font-family: monospace;
}

.header {
  margin-bottom: 24px;
}

.header h1 {
  font-size: 24px;
  color: #2d3748;
  margin: 0 0 16px;
}

.progress-section {
  background: white;
  padding: 16px;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.05);
}

.progress-bar {
  height: 8px;
  background: #e2e8f0;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 8px;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #667eea, #764ba2);
  border-radius: 4px;
  transition: width 0.3s ease;
}

.progress-text {
  margin: 0;
  font-size: 14px;
  color: #718096;
}

.loading-container {
  text-align: center;
  padding: 60px;
  background: white;
  border-radius: 16px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.08);
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #e2e8f0;
  border-top-color: #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 16px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.error-box, .transition-box {
  text-align: center;
  padding: 40px;
  background: white;
  border-radius: 16px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.08);
}

.error-icon, .transition-icon { font-size: 48px; margin-bottom: 16px; }

.question-box, .summary-review-box, .completion-box {
  background: white;
  border-radius: 16px;
  padding: 32px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.08);
}

.question-header { margin-bottom: 24px; }

.question-number {
  display: inline-block;
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: white;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 12px;
}

.question-text {
  font-size: 20px;
  color: #2d3748;
  line-height: 1.5;
  margin: 0;
}

.question-description {
  color: #718096;
  font-size: 14px;
  margin-top: 8px;
  background: #f7fafc;
  padding: 12px;
  border-radius: 8px;
}

.options-list { display: flex; flex-direction: column; gap: 12px; }

.option-item {
  display: flex;
  align-items: center;
  padding: 16px;
  border: 2px solid #e2e8f0;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s;
}

.option-item:hover { border-color: #667eea; background: #f7fafc; }
.option-item.selected { border-color: #667eea; background: #ebf4ff; }

.option-item input { margin-right: 12px; }

.form-input, .form-textarea, .form-select {
  width: 100%;
  padding: 12px 16px;
  border: 2px solid #e2e8f0;
  border-radius: 8px;
  font-size: 16px;
  transition: border-color 0.2s;
}

.form-input:focus, .form-textarea:focus, .form-select:focus {
  outline: none;
  border-color: #667eea;
}

.form-fields { display: flex; flex-direction: column; gap: 20px; }

.field-label {
  display: block;
  margin-bottom: 8px;
  font-weight: 500;
  color: #4a5568;
}

.required { color: #e53e3e; }

.field-options { display: flex; gap: 20px; }

.inline-option {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.upload-dropzone {
  border: 2px dashed #cbd5e0;
  border-radius: 12px;
  padding: 40px;
  text-align: center;
  transition: all 0.2s;
  position: relative;
}

.upload-dropzone.drag-over {
  border-color: #667eea;
  background: #ebf4ff;
}

.file-input {
  position: absolute;
  opacity: 0;
  width: 100%;
  height: 100%;
  cursor: pointer;
}

.upload-icon { font-size: 48px; }
.upload-hint { color: #a0aec0; font-size: 14px; margin-top: 8px; }
.link { color: #667eea; cursor: pointer; text-decoration: underline; }

.uploaded-file {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 16px;
  padding: 12px;
  background: #f7fafc;
  border-radius: 8px;
}

.file-icon { font-size: 24px; }
.file-name { flex: 1; }
.uploading { color: #667eea; }
.ocr-badge { background: #48bb78; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; }
.remove-file { background: none; border: none; font-size: 20px; cursor: pointer; color: #a0aec0; }

.message-box {
  background: #f7fafc;
  padding: 24px;
  border-radius: 12px;
  border-left: 4px solid #667eea;
}

.actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 32px;
  padding-top: 24px;
  border-top: 1px solid #e2e8f0;
}

.btn {
  padding: 12px 24px;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn:disabled { opacity: 0.5; cursor: not-allowed; }

.btn-primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
}
.btn-primary:hover:not(:disabled) { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4); }

.btn-outline {
  background: white;
  border: 2px solid #e2e8f0;
  color: #4a5568;
}
.btn-outline:hover:not(:disabled) { border-color: #667eea; }

/* Summary Review */
.summary-header h2 { margin: 0 0 20px; color: #2d3748; }

.summary-content {
  background: #f7fafc;
  padding: 24px;
  border-radius: 12px;
  margin-bottom: 24px;
}

.ai-badge {
  display: inline-block;
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: white;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 12px;
  margin-bottom: 16px;
}

.summary-actions { display: flex; justify-content: flex-end; gap: 12px; }

/* Completion */
.completion-box { text-align: center; }

.success-icon {
  width: 80px;
  height: 80px;
  background: linear-gradient(135deg, #48bb78, #38a169);
  color: white;
  font-size: 40px;
  line-height: 80px;
  border-radius: 50%;
  margin: 0 auto 24px;
}

.case-info {
  background: #f7fafc;
  padding: 16px;
  border-radius: 8px;
  margin: 24px 0;
}

.case-info .label { color: #718096; }
.case-info .value { font-weight: 600; color: #2d3748; font-family: monospace; }

.case-created-notice {
  background: #ebf8ff;
  border: 1px solid #90cdf4;
  padding: 16px;
  border-radius: 8px;
  margin: 24px 0;
}

.case-created-notice .notice-icon {
  font-size: 24px;
  margin-bottom: 8px;
}

.summaries-review {
  text-align: left;
  margin: 24px 0;
  padding: 20px;
  background: #f7fafc;
  border-radius: 12px;
}

.summaries-review h3 {
  margin: 0 0 16px;
  font-size: 16px;
  color: #2d3748;
}

.summary-item {
  padding: 12px 0;
  border-bottom: 1px solid #e2e8f0;
}

.summary-item:last-child { border-bottom: none; }

.completion-actions {
  display: flex;
  justify-content: center;
  gap: 12px;
  margin-top: 32px;
}

@media (max-width: 768px) {
  .questionnaire-page { padding: 16px; }
  .question-box, .summary-review-box, .completion-box { padding: 20px; }
  .actions { flex-direction: column-reverse; }
  .btn { width: 100%; justify-content: center; }
}
</style>
