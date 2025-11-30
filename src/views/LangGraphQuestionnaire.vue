<template>
  <div class="langgraph-questionnaire-page">
    <div class="questionnaire-wrapper">
      <!-- Back Button -->
      <div class="back-section">
        <button @click="goBack" class="btn-back" :disabled="isSubmitting">
          ← 返回
        </button>
        <span v-if="sessionInfo" class="session-info">
          会话: {{ sessionInfo.sessionId?.slice(0, 12) }}...
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
            <!-- Document generation hint -->
            <div v-if="currentQuestion.triggers_document_generation" class="document-hint">
              <span class="hint-icon">📄</span>
              <span>填写完成后，系统将自动生成《{{ getTemplateName(currentQuestion.document_template) }}》</span>
            </div>
            
            <div v-for="field in currentQuestion.fields" :key="field.name" class="form-field">
              <label class="field-label">
                {{ field.label }}
                <span v-if="field.required !== false" class="required">*</span>
              </label>
              
              <!-- Text input -->
              <input 
                v-if="field.type === 'text'"
                type="text"
                v-model="formData[field.name]"
                :placeholder="field.placeholder || ''"
                class="form-input"
              />
              
              <!-- Number input -->
              <input 
                v-else-if="field.type === 'number'"
                type="number"
                v-model="formData[field.name]"
                :placeholder="field.placeholder || ''"
                class="form-input"
              />
              
              <!-- Date input -->
              <input 
                v-else-if="field.type === 'date' || field.type === 'datetime-local'"
                :type="field.type"
                v-model="formData[field.name]"
                class="form-input"
              />
              
              <!-- Textarea input -->
              <textarea 
                v-else-if="field.type === 'textarea'"
                v-model="formData[field.name]"
                :placeholder="field.placeholder || ''"
                class="form-textarea"
                rows="4"
              ></textarea>
              
              <!-- Radio input -->
              <div v-else-if="field.type === 'radio'" class="field-options">
                <label v-for="opt in field.options" :key="opt" class="inline-option">
                  <input type="radio" :value="opt" v-model="formData[field.name]" />
                  {{ opt }}
                </label>
              </div>
              
              <!-- Default to text input -->
              <input 
                v-else
                type="text"
                v-model="formData[field.name]"
                :placeholder="field.placeholder || ''"
                class="form-input"
              />
            </div>
            
            <!-- Document preview button -->
            <div v-if="currentQuestion.triggers_document_generation && isFormValid" class="document-preview-section">
              <button 
                @click="previewDocument(currentQuestion.document_template)" 
                class="btn btn-outline"
                :disabled="isGeneratingDoc"
              >
                {{ isGeneratingDoc ? '生成中...' : '📄 预览生成的文档' }}
              </button>
              <p class="preview-hint">点击预览按钮查看根据您填写的信息生成的文档</p>
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
                :accept="currentQuestion.acceptTypes?.join(',') || '*'"
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
            v-if="canGoBack"
            @click="goToPrevious" 
            class="btn btn-outline"
            :disabled="isSubmitting"
          >
            ← 上一步
          </button>
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
        <h2>{{ completionData.title }}</h2>
        <p v-html="formatText(completionData.message)"></p>
        
        <div v-if="completionData.submissionId" class="case-info">
          <span class="label">案件编号：</span>
          <span class="value">{{ completionData.submissionId }}</span>
        </div>

        <div v-if="completionData.summaries" class="summaries-review">
          <h3>📋 AI 分析总结</h3>
          <div v-for="(summary, part) in completionData.summaries" :key="part" class="summary-item">
            <strong>{{ getSummaryTitle(part) }}</strong>
            <p>{{ summary.content }}</p>
          </div>
        </div>

        <div v-if="completionData.evidenceList?.length" class="evidence-section">
          <h3>📁 证据清单</h3>
          <ul class="evidence-list">
            <li v-for="evidence in completionData.evidenceList" :key="evidence.evidenceNumber">
              <strong>{{ evidence.evidenceNumber }}:</strong> {{ evidence.fileName }}
            </li>
          </ul>
        </div>

        <div v-if="completionData.nextSteps?.length" class="next-steps">
          <h3>下一步</h3>
          <ul>
            <li v-for="(step, idx) in completionData.nextSteps" :key="idx">{{ step }}</li>
          </ul>
        </div>

        <div class="completion-actions">
          <button 
            v-for="action in completionData.actions" 
            :key="action.action"
            @click="handleAction(action.action)"
            class="btn"
            :class="action.action === 'view_case' ? 'btn-primary' : 'btn-outline'"
          >
            {{ action.label }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import api from '@/utils/api'
import DOMPurify from 'dompurify'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

// Props
const props = defineProps({
  title: {
    type: String,
    default: '交通事故法律咨询问卷'
  }
})

// State
const loading = ref(true)
const loadingText = ref('正在初始化问卷...')
const error = ref('')
const isSubmitting = ref(false)
const isRegenerating = ref(false)
const isUploading = ref(false)
const isDragging = ref(false)
const completed = ref(false)
const isGeneratingDoc = ref(false)
const generatedDocUrl = ref(null)

const sessionInfo = ref(null)
const currentQuestion = ref(null)
const currentAnswer = ref('')
const currentAnswerArray = ref([])
const formData = ref({})
const uploadedFile = ref(null)

const progress = ref(null)
const partInfo = ref(null)
const currentPart = ref(1)
const currentSummary = ref(null)
const showSummaryReview = ref(false)
const transitionMessage = ref(null)
const completionData = ref(null)
const questionHistory = ref([])

// Computed
const canGoBack = computed(() => {
  // Can go back if we're not at the first question
  // Check progress.current or questionHistory
  if (isSubmitting.value) return false
  if (questionHistory.value.length > 0) return true
  if (progress.value && progress.value.current > 1) return true
  return false
})

const canSubmit = computed(() => {
  if (!currentQuestion.value) return false
  const q = currentQuestion.value
  
  if (q.type === 'message') return true
  
  if (q.required !== false) {
    if (q.type === 'form') {
      return q.fields.every(f => {
        if (f.required !== false) {
          return formData.value[f.name] && String(formData.value[f.name]).trim()
        }
        return true
      })
    } else if (q.type === 'checkbox') {
      return currentAnswerArray.value.length > 0
    } else if (q.type === 'upload') {
      return true
    } else {
      return currentAnswer.value !== '' && currentAnswer.value !== null
    }
  }
  return true
})

const isFormValid = computed(() => {
  if (!currentQuestion.value || currentQuestion.value.type !== 'form') return false
  const q = currentQuestion.value
  return q.fields.every(f => {
    if (f.required !== false) {
      return formData.value[f.name] && String(formData.value[f.name]).trim()
    }
    return true
  })
})

// Methods
const getTemplateName = (code) => {
  const templates = {
    '035': '民事起诉状',
    '008': '授权委托书',
    '002': '民事上诉状',
    '001': '异议书',
    '004': '复议申请书'
  }
  return templates[code] || `模板${code}`
}

const previewDocument = async (templateCode) => {
  isGeneratingDoc.value = true
  generatedDocUrl.value = null
  
  try {
    const response = await api.post('/workflow/questionnaire/generate-document', {
      session_id: sessionInfo.value.sessionId || route.params.sessionId,
      template_code: templateCode,
      preview_only: true
    })
    
    if (response.data.success) {
      generatedDocUrl.value = response.data.download_url
      // Open in new tab if URL is available
      if (response.data.download_url) {
        window.open(response.data.download_url, '_blank')
      }
      alert(`文档生成成功！共填充 ${response.data.filled_fields || 0} 个字段。`)
    } else {
      alert('文档生成失败: ' + (response.data.error || '未知错误'))
    }
  } catch (err) {
    console.error('Document generation error:', err)
    alert('文档生成失败: ' + (err.response?.data?.detail || err.message))
  } finally {
    isGeneratingDoc.value = false
  }
}

const formatText = (text) => {
  if (!text) return ''
  // First sanitize the HTML to prevent XSS
  const sanitized = DOMPurify.sanitize(text, {
    ALLOWED_TAGS: ['br', 'b', 'i', 'u', 'strong', 'em', 'p'],
    ALLOWED_ATTR: []
  })
  // Then replace \n with <br> for line breaks
  return sanitized.replace(/\\n/g, '<br>').replace(/\n/g, '<br>')
}

const getSubmitButtonText = () => {
  if (!currentQuestion.value) return '下一步'
  if (currentQuestion.value.type === 'message') return '继续'
  return '下一步'
}

const getSummaryTitle = (part) => {
  const titles = {
    part1: '第一部分：基本信息采集',
    part2: '第二部分：事故过程与责任认定',
    part3: '第三部分:保险信息采集'
  }
  return titles[part] || part
}

const getSessionFromStorage = () => {
  const stored = sessionStorage.getItem('questionnaire_session')
  if (stored) {
    return JSON.parse(stored)
  }
  return null
}

const initQuestionnaire = async () => {
  loading.value = true
  loadingText.value = '正在初始化问卷...'
  error.value = ''

  try {
    // Get session from route params or storage
    const storedSession = getSessionFromStorage()
    const sessionId = route.params.sessionId || storedSession?.sessionId
    
    if (!sessionId) {
      throw new Error('会话信息丢失，请重新开始问卷')
    }

    sessionInfo.value = storedSession || { sessionId }

    // If we have stored question data, use it directly
    if (storedSession?.question && storedSession.sessionId === sessionId) {
      currentQuestion.value = storedSession.question
      progress.value = storedSession.progress
      partInfo.value = storedSession.partInfo
      
      // Restore previous answers if available (for resumed sessions)
      if (storedSession.answers) {
        const currentQId = currentQuestion.value?.id
        const prevAnswer = storedSession.answers[currentQId]
        if (prevAnswer) {
          if (currentQuestion.value.type === 'checkbox') {
            const val = prevAnswer.value || prevAnswer
            currentAnswerArray.value = Array.isArray(val) ? [...val] : []
          } else if (currentQuestion.value.type === 'form') {
            formData.value = prevAnswer.value || prevAnswer
          } else {
            currentAnswer.value = prevAnswer.value !== undefined ? prevAnswer.value : prevAnswer
          }
        }
      }
      
      sessionStorage.removeItem('questionnaire_session')
      loading.value = false
      return
    }

    // Try to resume the session using the resume endpoint
    loadingText.value = '正在恢复会话...'
    const response = await api.get(`/workflow/questionnaire/session/${sessionId}/resume`)
    const data = response.data

    if (data.success) {
      if (data.status === 'completed') {
        // Redirect to completion page
        router.push(`/questionnaire/${sessionId}/complete`)
        return
      } else if (data.question) {
        currentQuestion.value = data.question
        progress.value = data.progress
        partInfo.value = data.part_info
        
        // Store answers for reference (needed for go-back)
        if (data.answers) {
          sessionInfo.value.answers = data.answers
        }
      } else {
        error.value = data.message || '会话状态异常，请重新开始问卷'
      }
    } else {
      // Fallback to regular session status endpoint
      const statusResponse = await api.get(`/workflow/questionnaire/session/${sessionId}`)
      const statusData = statusResponse.data

      if (statusData.status === 'completed') {
        // Redirect to completion page
        router.push(`/questionnaire/${sessionId}/complete`)
        return
      } else {
        error.value = '会话状态异常，请重新开始问卷'
      }
    }

  } catch (err) {
    console.error('Init error:', err)
    error.value = err.response?.data?.detail || err.message || '初始化失败，请重试'
  } finally {
    loading.value = false
  }
}

const submitAnswer = async () => {
  if (!canSubmit.value) return
  
  isSubmitting.value = true

  try {
    // Prepare answer based on question type
    let answerValue
    if (currentQuestion.value.type === 'checkbox') {
      answerValue = currentAnswerArray.value
    } else if (currentQuestion.value.type === 'form') {
      answerValue = { ...formData.value }
    } else if (currentQuestion.value.type === 'upload') {
      answerValue = uploadedFile.value
    } else {
      answerValue = currentAnswer.value
    }

    // Save to history
    questionHistory.value.push({
      question: currentQuestion.value,
      answer: answerValue,
      progress: { ...progress.value },
      partInfo: { ...partInfo.value }
    })

    // Prepare file data if upload
    let fileData = null
    if (currentQuestion.value.type === 'upload' && uploadedFile.value) {
      fileData = {
        filename: uploadedFile.value.name,
        content_type: uploadedFile.value.type,
        base64: uploadedFile.value.base64 || null
      }
    }

    // Submit to LangGraph workflow API
    const response = await api.post('/workflow/questionnaire/answer', {
      session_id: sessionInfo.value.sessionId || route.params.sessionId,
      question_id: currentQuestion.value.id,
      answer: answerValue,
      file: fileData
    })

    const data = response.data

    if (data.error) {
      throw new Error(data.error)
    }

    // Handle response based on interrupt type
    if (data.completed || data.status === 'completed' || data.status === 'documents_ready') {
      // Redirect to completion page
      sessionStorage.removeItem('questionnaire_session')
      router.push(`/questionnaire/${sessionInfo.value.sessionId || route.params.sessionId}/complete`)
    } else if (data.show_summary || data.interrupt_type === 'summary_validation') {
      showSummaryReview.value = true
      currentSummary.value = data.summary?.content || data.summary
      currentPart.value = data.current_part || currentPart.value
    } else if (data.show_template_selection || data.interrupt_type === 'template_selection') {
      // Redirect to completion page for template selection
      sessionStorage.removeItem('questionnaire_session')
      router.push(`/questionnaire/${sessionInfo.value.sessionId || route.params.sessionId}/complete`)
    } else if (data.question) {
      currentQuestion.value = data.question
      progress.value = data.progress
      partInfo.value = data.part_info
      resetAnswers()
      
      // Check for part transition
      if (data.part_info && currentPart.value !== data.part_info.current) {
        currentPart.value = data.part_info.current
        transitionMessage.value = `进入 ${data.part_info.name}`
        setTimeout(() => { transitionMessage.value = null }, 2000)
      }
    }

  } catch (err) {
    console.error('Submit error:', err)
    alert('提交失败: ' + (err.response?.data?.detail || err.message))
    // Rollback
    questionHistory.value.pop()
  } finally {
    isSubmitting.value = false
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }
}

const continueToNext = () => {
  transitionMessage.value = null
}

const confirmSummary = async () => {
  isSubmitting.value = true
  try {
    // Call LangGraph validate-summary API with approved=true
    const response = await api.post('/workflow/questionnaire/validate-summary', {
      session_id: sessionInfo.value.sessionId || route.params.sessionId,
      approved: true,
      feedback: null
    })

    showSummaryReview.value = false
    currentSummary.value = null

    const data = response.data
    
    if (data.completed || data.status === 'completed' || data.status === 'documents_ready') {
      // Redirect to completion page
      sessionStorage.removeItem('questionnaire_session')
      router.push(`/questionnaire/${sessionInfo.value.sessionId || route.params.sessionId}/complete`)
    } else if (data.question) {
      currentQuestion.value = data.question
      progress.value = data.progress
      partInfo.value = data.part_info
      resetAnswers()
    } else if (data.show_template_selection || data.interrupt_type === 'template_selection') {
      // Redirect to completion page for template selection
      sessionStorage.removeItem('questionnaire_session')
      router.push(`/questionnaire/${sessionInfo.value.sessionId || route.params.sessionId}/complete`)
    }
  } catch (err) {
    console.error('Confirm summary error:', err)
    alert('确认失败: ' + (err.response?.data?.detail || err.message))
  } finally {
    isSubmitting.value = false
  }
}

const requestRegenerate = async () => {
  isRegenerating.value = true
  try {
    // Call LangGraph validate-summary API with approved=false
    const response = await api.post('/workflow/questionnaire/validate-summary', {
      session_id: sessionInfo.value.sessionId || route.params.sessionId,
      approved: false,
      feedback: '请重新生成更准确的总结'
    })
    
    if (response.data.summary) {
      currentSummary.value = response.data.summary?.content || response.data.summary
    }
  } catch (err) {
    console.error('Regenerate error:', err)
    alert('重新生成失败: ' + (err.response?.data?.detail || err.message))
  } finally {
    isRegenerating.value = false
  }
}

const goToPrevious = async () => {
  if (isSubmitting.value) return
  
  isSubmitting.value = true
  
  try {
    // Call backend API to go back
    const response = await api.post('/workflow/questionnaire/go-back', {
      session_id: sessionInfo.value.sessionId || route.params.sessionId
    })
    
    if (response.data.success) {
      // Update local state with response
      currentQuestion.value = response.data.question
      progress.value = response.data.progress
      partInfo.value = response.data.part_info
      
      // Restore previous answer if available
      const prevAnswer = response.data.previous_answer
      if (prevAnswer !== null && prevAnswer !== undefined) {
        if (currentQuestion.value.type === 'checkbox') {
          currentAnswerArray.value = Array.isArray(prevAnswer) ? [...prevAnswer] : []
        } else if (currentQuestion.value.type === 'form') {
          // Handle form data
          if (typeof prevAnswer === 'object') {
            formData.value = { ...prevAnswer }
          }
        } else {
          // Handle simple values (extract value if it's an object)
          if (typeof prevAnswer === 'object' && prevAnswer.value !== undefined) {
            currentAnswer.value = prevAnswer.value
          } else {
            currentAnswer.value = prevAnswer
          }
        }
      } else {
        resetAnswers()
      }
      
      // Update canGoBack based on response
      // (server tells us if we can go back further)
    }
  } catch (err) {
    console.error('Go back error:', err)
    alert('返回上一步失败: ' + (err.response?.data?.detail || err.message))
    
    // Fallback to local history if available
    if (questionHistory.value.length > 0) {
      const last = questionHistory.value.pop()
      currentQuestion.value = last.question
      progress.value = last.progress
      partInfo.value = last.partInfo
      
      if (last.question.type === 'checkbox') {
        currentAnswerArray.value = Array.isArray(last.answer) ? [...last.answer] : []
      } else if (last.question.type === 'form') {
        formData.value = { ...last.answer }
      } else {
        currentAnswer.value = last.answer
      }
    }
  } finally {
    isSubmitting.value = false
  }
}

const resetAnswers = () => {
  currentAnswer.value = ''
  currentAnswerArray.value = []
  formData.value = {}
  uploadedFile.value = null
}

const handleFileSelect = (e) => {
  const file = e.target.files[0]
  if (file) processFile(file)
}

const handleFileDrop = (e) => {
  isDragging.value = false
  const file = e.dataTransfer.files[0]
  if (file) processFile(file)
}

const processFile = async (file) => {
  isUploading.value = true
  uploadedFile.value = { name: file.name, size: file.size, type: file.type }
  
  try {
    // Create FormData for multipart upload
    const formDataPayload = new FormData()
    formDataPayload.append('file', file)
    formDataPayload.append('session_id', sessionInfo.value.sessionId || route.params.sessionId)
    formDataPayload.append('question_id', currentQuestion.value.id)
    
    // Upload using FormData
    const response = await api.post('/workflow/questionnaire/upload', formDataPayload, {
      headers: {
        // Let browser set Content-Type with boundary for FormData
        // The axios interceptor will handle this
      }
    })
    
    const data = response.data
    if (data.success) {
      uploadedFile.value = {
        ...uploadedFile.value,
        id: data.file_id,
        filename: data.filename,
        ocrText: data.ocr_result?.text || null,
        evidenceNumber: data.evidence_number
      }
      console.log('File uploaded successfully:', data)
    } else {
      throw new Error(data.detail || 'Upload failed')
    }
  } catch (err) {
    console.error('Upload error:', err)
    alert('文件上传失败: ' + (err.response?.data?.detail || err.message))
    uploadedFile.value = null
  } finally {
    isUploading.value = false
  }
}

const removeFile = () => {
  uploadedFile.value = null
}

const goBack = () => {
  if (confirm('确定要暂时离开问卷吗？您可以稍后在仪表板上继续填写。')) {
    sessionStorage.removeItem('questionnaire_session')
    router.push('/dashboard')
  }
}

const retryInit = () => {
  initQuestionnaire()
}

const handleAction = (action) => {
  switch (action) {
    case 'view_case':
      router.push(`/case/${completionData.value.submissionId}`)
      break
    case 'go_dashboard':
      router.push('/dashboard')
      break
    case 'match_lawyer':
      router.push('/case-pool')
      break
    default:
      router.push('/dashboard')
  }
}

// Lifecycle
onMounted(() => {
  initQuestionnaire()
})
</script>

<style scoped>
.langgraph-questionnaire-page {
  min-height: 100vh;
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  padding: 24px;
}

.questionnaire-wrapper {
  max-width: 800px;
  margin: 0 auto;
}

.back-section {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
}

.btn-back {
  background: white;
  border: 2px solid #e2e8f0;
  padding: 8px 16px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
}

.btn-back:hover:not(:disabled) { border-color: #667eea; }
.btn-back:disabled { opacity: 0.5; cursor: not-allowed; }

.session-info {
  color: #718096;
  font-size: 14px;
  font-family: monospace;
}

.header {
  background: white;
  padding: 32px;
  border-radius: 16px;
  margin-bottom: 24px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.08);
}

.header h1 {
  margin: 0 0 20px;
  font-size: 28px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.progress-section { margin-top: 24px; }

.progress-bar {
  width: 100%;
  height: 8px;
  background: #e2e8f0;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 8px;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
  transition: width 0.3s;
}

.progress-text {
  font-size: 14px;
  color: #718096;
  margin: 0;
}

.loading-container, .error-box, .transition-box {
  background: white;
  padding: 48px;
  border-radius: 16px;
  text-align: center;
  box-shadow: 0 4px 20px rgba(0,0,0,0.08);
}

.spinner {
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

.document-hint {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 18px;
  background: linear-gradient(135deg, #ebf4ff 0%, #e6e9ff 100%);
  border-radius: 10px;
  border-left: 4px solid #667eea;
  margin-bottom: 8px;
  font-size: 14px;
  color: #4a5568;
}

.document-hint .hint-icon {
  font-size: 20px;
}

.document-preview-section {
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px dashed #cbd5e0;
  text-align: center;
}

.document-preview-section .btn {
  display: inline-flex;
}

.preview-hint {
  margin-top: 8px;
  font-size: 13px;
  color: #718096;
}

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

.summaries-review, .evidence-section, .next-steps {
  text-align: left;
  margin: 24px 0;
  padding: 20px;
  background: #f7fafc;
  border-radius: 12px;
}

.summaries-review h3, .evidence-section h3, .next-steps h3 {
  margin: 0 0 16px;
  font-size: 16px;
  color: #2d3748;
}

.summary-item {
  padding: 12px 0;
  border-bottom: 1px solid #e2e8f0;
}

.summary-item:last-child { border-bottom: none; }

.evidence-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.evidence-list li {
  padding: 8px 0;
  border-bottom: 1px solid #e2e8f0;
}

.next-steps ul {
  margin: 0;
  padding-left: 20px;
}

.next-steps li {
  padding: 8px 0;
  color: #4a5568;
}

.completion-actions {
  display: flex;
  justify-content: center;
  gap: 12px;
  margin-top: 32px;
}

@media (max-width: 768px) {
  .langgraph-questionnaire-page { padding: 16px; }
  .question-box, .summary-review-box, .completion-box { padding: 20px; }
  .actions { flex-direction: column-reverse; }
  .btn { width: 100%; justify-content: center; }
}
</style>
