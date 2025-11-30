<template>
  <div class="questionnaire-container">
    <!-- 头部 -->
    <div class="header">
      <h1>{{ title }}</h1>
      <div class="progress-bar" v-if="!completed && currentQuestion && progress">
        <div class="progress-fill" :style="{ width: progress.percentage + '%' }"></div>
      </div>
      <p class="progress-text" v-if="!completed && currentQuestion && progress">
        进度: {{ progress.current }} / {{ progress.total }}
      </p>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="loading">
      <div class="spinner"></div>
      <p>{{ loadingText }}</p>
    </div>

    <!-- 错误提示 -->
    <div v-if="error" class="error-box">
      <p>{{ error }}</p>
      <button @click="retryConnection" class="btn-retry">重试</button>
    </div>

    <!-- 问卷内容 -->
    <div v-if="!loading && !error && !completed && currentQuestion" class="question-box">
      <div class="question-header">
        <h2 class="question-text" v-html="formatQuestionText(currentQuestion.text)"></h2>
        <p v-if="currentQuestion.description" class="question-description">
          {{ currentQuestion.description }}
        </p>
      </div>

      <div class="question-content">
        <!-- 动态渲染不同类型的问题 -->
        <component 
          :is="getQuestionComponent(currentQuestion.type)"
          :question="currentQuestion"
          :modelValue="currentAnswer"
          @update:modelValue="updateAnswer"
          :formData="formData"
          @update:formData="updateFormData"
        />
      </div>

      <!-- 操作按钮 -->
      <div class="actions">
        <button 
          v-if="canGoBack"
          @click="goBack" 
          class="btn btn-back"
          :disabled="submitting"
        >
          <span class="btn-icon">←</span>
          上一步
        </button>
        <button 
          @click="submitAnswer" 
          class="btn btn-primary"
          :disabled="!canSubmit || submitting"
        >
          {{ submitting ? '提交中...' : getSubmitButtonText() }}
          <span class="btn-icon" v-if="!submitting">→</span>
        </button>
      </div>

      <!-- 答案预览（可选） -->
      <div class="answer-preview" v-if="showAnswerPreview && Object.keys(answers).length > 0">
        <details>
          <summary>查看已填写的答案 ({{ Object.keys(answers).length }})</summary>
          <div class="answer-list">
            <div v-for="(value, key) in answers" :key="key" class="answer-item">
              <strong>{{ key }}:</strong> 
              <span>{{ formatAnswerValue(value) }}</span>
            </div>
          </div>
        </details>
      </div>
    </div>

    <!-- 完成页面 -->
    <div v-if="completed && completionData" class="completed-box">
      <div class="success-icon" :class="completionData.icon || 'success'">✓</div>
      <h2>{{ completionData.title || '问卷提交成功！' }}</h2>
      <p v-html="formatQuestionText(completionData.message)"></p>
      
      <div v-if="completionData.submissionId" class="submission-info">
        <p><strong>案件编号：</strong>{{ completionData.submissionId }}</p>
      </div>

      <div v-if="completionData.nextSteps && completionData.nextSteps.length" class="next-steps">
        <h3>下一步：</h3>
        <ul>
          <li v-for="(step, idx) in completionData.nextSteps" :key="idx">{{ step }}</li>
        </ul>
      </div>

      <div v-if="completionData.actions && completionData.actions.length" class="action-buttons">
        <button 
          v-for="action in completionData.actions" 
          :key="action.action"
          @click="handleCompletionAction(action.action)"
          class="btn btn-action"
        >
          {{ action.label }}
        </button>
      </div>

      <button v-else @click="startOver" class="btn btn-primary">开始新问卷</button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, defineAsyncComponent } from 'vue'
import DOMPurify from 'dompurify'

// ==================== Props ====================
const props = defineProps({
  n8nWebhookUrl: {
    type: String,
    default: 'http://localhost:5678/webhook/type1-start'
  },
  templateType: {
    type: Number,
    default: 1
  },
  title: {
    type: String,
    default: '交通事故法律咨询问卷'
  },
  showAnswerPreview: {
    type: Boolean,
    default: true
  },
  autoSaveDraft: {
    type: Boolean,
    default: true
  }
})

// ==================== Emits ====================
const emit = defineEmits(['completed', 'error', 'step-changed'])

// ==================== 状态管理 ====================
const loading = ref(false)
const loadingText = ref('正在加载问题...')
const error = ref('')
const submitting = ref(false)
const completed = ref(false)

const currentQuestion = ref(null)
const currentAnswer = ref('')
const formData = ref({})

const sessionId = ref(null)
const resumeUrl = ref(null)
const answers = ref({})
const questionHistory = ref([])
const progress = ref(null)
const completionData = ref(null)

// ==================== 动态组件映射 ====================
const questionComponents = {
  radio: defineAsyncComponent(() => import('./questions/RadioQuestion.vue')),
  checkbox: defineAsyncComponent(() => import('./questions/CheckboxQuestion.vue')),
  text: defineAsyncComponent(() => import('./questions/TextQuestion.vue')),
  textarea: defineAsyncComponent(() => import('./questions/TextareaQuestion.vue')),
  number: defineAsyncComponent(() => import('./questions/NumberQuestion.vue')),
  date: defineAsyncComponent(() => import('./questions/DateQuestion.vue')),
  select: defineAsyncComponent(() => import('./questions/SelectQuestion.vue')),
  form: defineAsyncComponent(() => import('./questions/FormQuestion.vue')),
  message: defineAsyncComponent(() => import('./questions/MessageQuestion.vue')),
  upload: defineAsyncComponent(() => import('./questions/UploadQuestion.vue'))
}

const getQuestionComponent = (type) => {
  return questionComponents[type] || questionComponents.text
}

// ==================== 计算属性 ====================
const canGoBack = computed(() => {
  return questionHistory.value.length > 0 && !submitting.value
})

const canSubmit = computed(() => {
  if (!currentQuestion.value) return false
  
  const question = currentQuestion.value
  
  // 消息类型直接可以继续
  if (question.type === 'message') return true
  
  // 检查必填
  if (question.required) {
    if (question.type === 'form') {
      // 检查表单中所有必填字段
      return question.fields.every(field => {
        if (field.required !== false) {
          const value = formData.value[field.name]
          return value && String(value).trim() !== ''
        }
        return true
      })
    } else if (question.type === 'checkbox') {
      // 多选至少选一个
      return Array.isArray(currentAnswer.value) && currentAnswer.value.length > 0
    } else {
      // 其他类型检查有值
      return currentAnswer.value !== '' && currentAnswer.value !== null && currentAnswer.value !== undefined
    }
  }
  
  return true
})

// ==================== 工具函数 ====================
const getJwtToken = () => {
  return localStorage.getItem('jwt_token') || sessionStorage.getItem('jwt_token')
}

const formatQuestionText = (text) => {
  if (!text) return ''
  // First sanitize the HTML to prevent XSS attacks
  const sanitized = DOMPurify.sanitize(text, {
    ALLOWED_TAGS: ['br', 'b', 'i', 'u', 'strong', 'em', 'p'],
    ALLOWED_ATTR: []
  })
  // Then support line breaks
  return sanitized.replace(/\\n/g, '<br>').replace(/\n/g, '<br>')
}

const formatAnswerValue = (value) => {
  if (Array.isArray(value)) {
    return value.join(', ')
  }
  if (typeof value === 'object' && value !== null) {
    return Object.entries(value).map(([k, v]) => `${k}: ${v}`).join(', ')
  }
  return String(value)
}

const getSubmitButtonText = () => {
  if (!currentQuestion.value) return '下一步'
  
  const question = currentQuestion.value
  if (question.type === 'message') {
    return question.continueText || '继续'
  }
  if (question.submitText) {
    return question.submitText
  }
  return '下一步'
}

const updateAnswer = (value) => {
  currentAnswer.value = value
}

const updateFormData = (data) => {
  formData.value = data
}

// ==================== 草稿保存 ====================
const saveDraft = () => {
  if (!props.autoSaveDraft) return
  
  const draft = {
    sessionId: sessionId.value,
    templateType: props.templateType,
    answers: answers.value,
    timestamp: Date.now()
  }
  
  localStorage.setItem(`questionnaire_draft_${props.templateType}`, JSON.stringify(draft))
}

const loadDraft = () => {
  if (!props.autoSaveDraft) return null
  
  const draftStr = localStorage.getItem(`questionnaire_draft_${props.templateType}`)
  if (!draftStr) return null
  
  try {
    const draft = JSON.parse(draftStr)
    // 检查是否在24小时内
    if (Date.now() - draft.timestamp < 24 * 60 * 60 * 1000) {
      return draft
    }
  } catch (e) {
    console.error('Failed to load draft:', e)
  }
  
  return null
}

const clearDraft = () => {
  localStorage.removeItem(`questionnaire_draft_${props.templateType}`)
}

// ==================== API 调用 ====================
const apiCall = async (url, options = {}) => {
  const token = getJwtToken()
  
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers
  }
  
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  
  const response = await fetch(url, {
    ...options,
    headers
  })
  
  if (!response.ok) {
    if (response.status === 401) {
      emit('error', { type: 'auth', message: 'Token 已过期，请重新登录' })
      throw new Error('Unauthorized')
    }
    throw new Error(`HTTP ${response.status}`)
  }
  
  return response.json()
}

const startQuestionnaire = async () => {
  loading.value = true
  loadingText.value = '正在初始化问卷...'
  error.value = ''
  
  try {
    const token = getJwtToken()
    if (!token) {
      throw new Error('未找到认证 Token，请先登录')
    }
    
    const data = await apiCall(props.n8nWebhookUrl, {
      method: 'POST',
      body: JSON.stringify({
        jwt: token,
        templateType: props.templateType,
        action: 'start',
        timestamp: new Date().toISOString()
      })
    })
    
    // 保存会话信息
    sessionId.value = data.sessionId
    resumeUrl.value = data.resumeUrl
    currentQuestion.value = data.question
    progress.value = data.progress
    
    emit('step-changed', {
      step: 1,
      question: data.question
    })
    
  } catch (err) {
    console.error('启动问卷失败:', err)
    error.value = err.message || '连接服务器失败，请检查网络连接或稍后重试。'
    emit('error', { type: 'network', message: error.value, error: err })
  } finally {
    loading.value = false
  }
}

const submitAnswer = async () => {
  if (!canSubmit.value) return
  
  submitting.value = true
  loadingText.value = '正在提交答案...'
  error.value = ''
  
  try {
    // 准备提交的答案数据
    let answerData
    if (currentQuestion.value.type === 'form') {
      answerData = { ...formData.value }
    } else {
      answerData = currentAnswer.value
    }
    
    // 保存当前问题到历史（用于返回）
    questionHistory.value.push({
      question: { ...currentQuestion.value },
      answer: answerData,
      resumeUrl: resumeUrl.value,
      progress: progress.value ? { ...progress.value } : null
    })
    
    // 保存答案
    answers.value[currentQuestion.value.id] = answerData
    
    // 保存草稿
    saveDraft()
    
    // 提交到 n8n
    const data = await apiCall(resumeUrl.value, {
      method: 'POST',
      body: JSON.stringify({
        sessionId: sessionId.value,
        questionId: currentQuestion.value.id,
        answer: answerData,
        allAnswers: answers.value,
        timestamp: new Date().toISOString()
      })
    })
    
    // 检查是否完成
    if (data.completed) {
      completed.value = true
      completionData.value = {
        title: data.title || '问卷提交成功！',
        message: data.message || '感谢您的配合',
        submissionId: data.submissionId,
        nextSteps: data.nextSteps,
        actions: data.actions,
        icon: data.icon || 'success'
      }
      
      clearDraft()
      
      emit('completed', {
        sessionId: sessionId.value,
        answers: answers.value,
        submissionId: data.submissionId
      })
    } else {
      // 加载下一个问题
      currentQuestion.value = data.question
      resumeUrl.value = data.resumeUrl
      progress.value = data.progress
      
      // 清空当前答案
      currentAnswer.value = ''
      formData.value = {}
      
      emit('step-changed', {
        step: progress.value?.current || 0,
        question: data.question
      })
      
      // 滚动到顶部
      window.scrollTo({ top: 0, behavior: 'smooth' })
    }
    
  } catch (err) {
    console.error('提交答案失败:', err)
    error.value = err.message || '提交失败，请重试。'
    
    // 回滚状态
    if (questionHistory.value.length > 0) {
      questionHistory.value.pop()
      delete answers.value[currentQuestion.value.id]
    }
    
    emit('error', { type: 'submit', message: error.value, error: err })
  } finally {
    submitting.value = false
  }
}

const goBack = () => {
  if (questionHistory.value.length === 0) return
  
  // 恢复上一个问题
  const lastState = questionHistory.value.pop()
  currentQuestion.value = lastState.question
  resumeUrl.value = lastState.resumeUrl
  progress.value = lastState.progress
  
  // 恢复答案
  if (lastState.question.type === 'form') {
    formData.value = { ...lastState.answer }
  } else {
    currentAnswer.value = lastState.answer
  }
  
  // 从答案记录中删除
  delete answers.value[lastState.question.id]
  
  // 保存草稿
  saveDraft()
  
  emit('step-changed', {
    step: progress.value?.current || 0,
    question: lastState.question,
    direction: 'back'
  })
  
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

const retryConnection = () => {
  startQuestionnaire()
}

const startOver = () => {
  // 重置所有状态
  completed.value = false
  completionData.value = null
  currentQuestion.value = null
  currentAnswer.value = ''
  formData.value = {}
  sessionId.value = null
  resumeUrl.value = null
  answers.value = {}
  questionHistory.value = []
  progress.value = null
  error.value = ''
  
  clearDraft()
  
  // 重新开始
  startQuestionnaire()
}

const handleCompletionAction = (action) => {
  emit('action', action)
  
  // 默认行为
  if (action === 'restart' || action === 'start_new') {
    startOver()
  } else if (action === 'go_home') {
    window.location.href = '/'
  }
}

// ==================== 生命周期 ====================
onMounted(() => {
  // 尝试恢复草稿
  const draft = loadDraft()
  if (draft) {
    // TODO: 实现草稿恢复逻辑
    console.log('Found draft:', draft)
  }
  
  startQuestionnaire()
})
</script>

<style scoped>
/* 保持与之前相同的样式 */
.questionnaire-container {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
}

.header {
  text-align: center;
  margin-bottom: 40px;
}

.header h1 {
  color: #1a1a1a;
  font-size: 28px;
  margin-bottom: 20px;
}

.progress-bar {
  width: 100%;
  height: 8px;
  background-color: #e0e0e0;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 10px;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #4CAF50, #45a049);
  transition: width 0.3s ease;
}

.progress-text {
  color: #666;
  font-size: 14px;
}

.loading {
  text-align: center;
  padding: 60px 20px;
}

.spinner {
  border: 4px solid #f3f3f3;
  border-top: 4px solid #4CAF50;
  border-radius: 50%;
  width: 50px;
  height: 50px;
  animation: spin 1s linear infinite;
  margin: 0 auto 20px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.error-box {
  background-color: #ffebee;
  border: 1px solid #ef5350;
  border-radius: 8px;
  padding: 20px;
  margin: 20px 0;
  text-align: center;
}

.error-box p {
  color: #c62828;
  margin-bottom: 15px;
}

.btn-retry {
  background-color: #ef5350;
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 6px;
  cursor: pointer;
}

.question-box {
  background-color: white;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  padding: 30px;
  margin-bottom: 20px;
}

.question-text {
  color: #1a1a1a;
  font-size: 20px;
  font-weight: 600;
  line-height: 1.5;
  margin-bottom: 10px;
}

.question-description {
  color: #666;
  font-size: 14px;
  margin-bottom: 20px;
}

.actions {
  display: flex;
  gap: 15px;
  margin-top: 30px;
  justify-content: flex-end;
}

.btn {
  padding: 12px 30px;
  border: none;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-back {
  background-color: #f5f5f5;
  color: #666;
}

.btn-primary {
  background-color: #4CAF50;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background-color: #45a049;
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(76, 175, 80, 0.3);
}

.completed-box {
  text-align: center;
  padding: 60px 30px;
  background-color: white;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}

.success-icon {
  width: 80px;
  height: 80px;
  background-color: #4CAF50;
  color: white;
  font-size: 48px;
  line-height: 80px;
  border-radius: 50%;
  margin: 0 auto 30px;
}

.submission-info {
  background-color: #f9f9f9;
  padding: 15px;
  border-radius: 8px;
  margin: 20px 0;
}

.next-steps {
  text-align: left;
  background-color: #f0f8ff;
  padding: 20px;
  border-radius: 8px;
  margin: 20px 0;
}

.next-steps ul {
  margin: 10px 0 0 20px;
}

.action-buttons {
  display: flex;
  gap: 10px;
  justify-content: center;
  margin-top: 20px;
}

@media (max-width: 768px) {
  .questionnaire-container {
    padding: 15px;
  }
  
  .actions {
    flex-direction: column-reverse;
  }
  
  .btn {
    width: 100%;
  }
}
</style>
