<template>
  <div class="min-h-screen bg-slate-50/50 flex flex-col items-center py-8 px-4">
    
    <div class="w-full max-w-2xl flex items-center justify-between mb-6">
      <Button variant="ghost" size="sm" @click="goBack" :disabled="isSubmitting" class="text-muted-foreground hover:text-foreground">
        <ArrowLeft class="w-4 h-4 mr-2" /> 返回
      </Button>
      <div v-if="sessionId" class="flex items-center gap-2 text-xs text-muted-foreground bg-white px-3 py-1 rounded-full border shadow-sm">
        <Hash class="w-3 h-3" />
        <span class="font-mono">{{ sessionId?.slice(0, 8) }}</span>
      </div>
    </div>

    <Card class="w-full max-w-2xl shadow-lg border-0 bg-white/80 backdrop-blur-sm animate-in fade-in slide-in-from-bottom-4 duration-500">
      
      <CardHeader class="pb-2 space-y-4">
        <div class="flex items-center justify-between">
          <Badge variant="outline" class="bg-primary/5 text-primary border-primary/20 px-3 py-1">
            {{ partInfo?.name || '法律咨询' }}
          </Badge>
          <span class="text-xs font-medium text-muted-foreground" v-if="progress">
            步骤 {{ progress.current }} / {{ progress.total }}
          </span>
        </div>
        <div class="space-y-2">
          <h1 class="text-2xl font-bold tracking-tight">{{ title }}</h1>
          <Progress v-if="progress" :value="progress.percentage" class="h-2" />
        </div>
      </CardHeader>

      <CardContent class="py-6 min-h-[300px]">
        
        <div v-if="loading" class="flex flex-col items-center justify-center h-48 space-y-4">
          <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          <p class="text-sm text-muted-foreground animate-pulse">{{ loadingText }}</p>
        </div>

        <Alert v-else-if="error" variant="destructive" class="my-4">
          <AlertCircle class="h-4 w-4" />
          <div class="ml-2">
            <h3 class="font-medium">发生错误</h3>
            <p class="text-sm opacity-90">{{ error }}</p>
            <Button variant="outline" size="sm" class="mt-3 bg-white/10 hover:bg-white/20 border-white/20" @click="retryInit">
              重试
            </Button>
          </div>
        </Alert>

        <div v-else-if="transitionMessage" class="flex flex-col items-center justify-center h-48 text-center space-y-4 animate-in zoom-in duration-300">
          <div class="h-12 w-12 rounded-full bg-emerald-100 flex items-center justify-center">
            <Sparkles class="h-6 w-6 text-emerald-600" />
          </div>
          <h3 class="text-lg font-medium text-emerald-700">{{ transitionMessage }}</h3>
        </div>

        <div v-else-if="showSummaryReview && currentSummary" class="space-y-6">
          <div class="bg-blue-50/50 rounded-xl p-6 border border-blue-100/50">
            <div class="flex items-center gap-2 mb-4 text-blue-700 font-semibold">
              <Bot class="w-5 h-5" />
              AI 阶段分析 (第{{ currentPart }}部分)
            </div>
            <div class="prose prose-sm max-w-none text-slate-600 leading-relaxed" v-html="formatText(currentSummary)"></div>
          </div>
          <div class="flex justify-end gap-3 pt-2">
            <Button variant="outline" @click="requestRegenerate" :disabled="isRegenerating">
              <RefreshCw class="w-4 h-4 mr-2" :class="{'animate-spin': isRegenerating}" />
              重新生成
            </Button>
            <Button @click="confirmSummary" :disabled="isSubmitting">
              确认并继续 <Check class="w-4 h-4 ml-2" />
            </Button>
          </div>
        </div>

        <div v-else-if="currentQuestion" class="space-y-6">
          
          <div class="space-y-2">
            <div class="inline-flex items-center rounded-md border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 border-transparent bg-primary text-primary-foreground shadow hover:bg-primary/80 mb-2">
              Q{{ currentQuestion.id?.replace('q', '') }}
            </div>
            <h2 class="text-xl font-medium leading-relaxed" v-html="formatText(currentQuestion.text)"></h2>
            <p v-if="currentQuestion.description" class="text-sm text-muted-foreground bg-secondary/50 p-3 rounded-lg border border-border/50">
              💡 {{ currentQuestion.description }}
            </p>
          </div>

          <div class="space-y-4 pt-2">
            <Input 
              v-if="currentQuestion.type === 'text'"
              v-model="currentAnswer" 
              :placeholder="currentQuestion.placeholder || '请输入您的回答...'"
              class="h-12 text-base"
              @keyup.enter="submitAnswer"
            />

            <Textarea 
              v-if="currentQuestion.type === 'textarea'"
              v-model="currentAnswer" 
              :placeholder="currentQuestion.placeholder || '请详细描述...'"
              rows="5"
              class="resize-none text-base"
            />

            <div v-if="currentQuestion.type === 'radio'" class="grid gap-3">
              <div 
                v-for="option in currentQuestion.options" 
                :key="option"
                class="flex items-center space-x-3 p-4 rounded-xl border cursor-pointer transition-all hover:border-primary/50 hover:bg-slate-50"
                :class="currentAnswer === option ? 'border-primary bg-primary/5 ring-1 ring-primary' : 'bg-white'"
                @click="currentAnswer = option"
              >
                <div class="h-4 w-4 rounded-full border border-primary flex items-center justify-center shrink-0">
                  <div v-if="currentAnswer === option" class="h-2 w-2 rounded-full bg-primary" />
                </div>
                <span class="flex-1 text-sm font-medium">{{ option }}</span>
              </div>
            </div>

            <div v-if="currentQuestion.type === 'checkbox'" class="grid gap-3">
              <div 
                v-for="option in currentQuestion.options" 
                :key="option"
                class="flex items-center space-x-3 p-4 rounded-xl border cursor-pointer transition-all hover:border-primary/50 hover:bg-slate-50"
                :class="currentAnswerArray.includes(option) ? 'border-primary bg-primary/5' : 'bg-white'"
                @click="toggleCheckbox(option)"
              >
                <div class="h-4 w-4 rounded border border-primary flex items-center justify-center shrink-0">
                  <Check v-if="currentAnswerArray.includes(option)" class="h-3 w-3 text-primary" />
                </div>
                <span class="flex-1 text-sm font-medium">{{ option }}</span>
              </div>
            </div>

            <div v-if="currentQuestion.type === 'form'" class="grid gap-5 p-5 bg-slate-50 rounded-xl border">
              <div v-if="currentQuestion.triggers_document_generation" class="flex items-center gap-2 text-sm text-amber-600 bg-amber-50 p-3 rounded-lg border border-amber-100">
                <FileText class="w-4 h-4" />
                <span>填写完成后系统将自动生成《{{ getTemplateName(currentQuestion.document_template) }}》</span>
              </div>
              
              <div v-for="field in currentQuestion.fields" :key="field.name" class="space-y-2">
                <Label :class="{ 'after:content-[\'*\'] after:text-red-500 after:ml-0.5': field.required !== false }">
                  {{ field.label }}
                </Label>
                
                <Input v-if="['text', 'number', 'date', 'email'].includes(field.type)" 
                  :type="field.type" 
                  v-model="formData[field.name]" 
                  :placeholder="field.placeholder"
                  class="bg-white"
                />
                
                <Textarea v-else-if="field.type === 'textarea'"
                  v-model="formData[field.name]"
                  :placeholder="field.placeholder"
                  rows="3"
                  class="bg-white"
                />
                
                <div v-else-if="field.type === 'radio'" class="flex flex-wrap gap-4 pt-1">
                  <label v-for="opt in field.options" :key="opt" class="flex items-center gap-2 cursor-pointer text-sm">
                    <input type="radio" :value="opt" v-model="formData[field.name]" class="text-primary focus:ring-primary" />
                    {{ opt }}
                  </label>
                </div>
              </div>

              <div v-if="currentQuestion.triggers_document_generation && isFormValid" class="pt-2 text-center">
                <Button 
                  type="button"
                  variant="outline"
                  @click="previewDocument(currentQuestion.document_template)" 
                  :disabled="isGeneratingDoc"
                  class="w-full border-dashed"
                >
                  <Loader2 v-if="isGeneratingDoc" class="w-4 h-4 mr-2 animate-spin" />
                  <FileText v-else class="w-4 h-4 mr-2" />
                  {{ isGeneratingDoc ? '生成预览中...' : '生成文档预览' }}
                </Button>
              </div>
            </div>

            <div v-if="currentQuestion.type === 'upload'" class="space-y-4">
              <div 
                class="border-2 border-dashed rounded-xl p-8 text-center transition-colors relative cursor-pointer"
                :class="isDragging ? 'border-primary bg-primary/5' : 'border-muted-foreground/25 hover:bg-slate-50'"
                @dragover.prevent="isDragging = true"
                @dragleave="isDragging = false"
                @drop.prevent="handleFileDrop"
                @click="$refs.fileInput.click()"
              >
                <input ref="fileInput" type="file" class="hidden" @change="handleFileSelect" :accept="currentQuestion.acceptTypes?.join(',')"/>
                
                <div v-if="!uploadedFile" class="space-y-3 pointer-events-none">
                  <div class="mx-auto w-12 h-12 bg-primary/10 rounded-full flex items-center justify-center text-primary">
                    <UploadCloud class="w-6 h-6" />
                  </div>
                  <div>
                    <p class="font-medium">点击上传或拖拽文件到此处</p>
                    <p class="text-xs text-muted-foreground mt-1">支持图片、PDF格式 (最大10MB)</p>
                  </div>
                </div>

                <div v-else class="flex items-center justify-between bg-primary/5 p-4 rounded-lg border border-primary/20 pointer-events-none">
                  <div class="flex items-center gap-3">
                    <div class="h-10 w-10 bg-white rounded-lg border flex items-center justify-center text-primary">
                      <FileText class="w-5 h-5" />
                    </div>
                    <div class="text-left">
                      <p class="font-medium text-sm truncate max-w-[200px]">{{ uploadedFile.name }}</p>
                      <div class="flex items-center gap-2 mt-0.5">
                        <span class="text-xs text-muted-foreground">{{ formatFileSize(uploadedFile.size) }}</span>
                        <span v-if="isUploading" class="text-xs text-blue-500 flex items-center gap-1">
                          <Loader2 class="w-3 h-3 animate-spin" /> 上传中...
                        </span>
                        <span v-else-if="uploadedFile.ocrText" class="text-xs bg-emerald-100 text-emerald-700 px-1.5 py-0.5 rounded">OCR已识别</span>
                      </div>
                    </div>
                  </div>
                  <Button size="icon" variant="ghost" class="pointer-events-auto h-8 w-8 hover:bg-red-50 hover:text-red-500" @click.stop="removeFile">
                    <X class="w-4 h-4" />
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </CardContent>

      <CardFooter class="flex justify-between pt-6 border-t bg-slate-50/50 rounded-b-xl" v-if="!loading && !error && !showSummaryReview && !transitionMessage">
        <Button 
          variant="ghost" 
          @click="goToPrevious" 
          :disabled="!canGoBack || isSubmitting"
          v-if="canGoBack"
          class="text-muted-foreground"
        >
          上一步
        </Button>
        <div v-else></div> <Button 
          @click="submitAnswer" 
          :disabled="!canSubmit || isSubmitting" 
          class="px-8"
          :loading="isSubmitting"
        >
          {{ getSubmitButtonText() }}
          <ArrowRight v-if="!isSubmitting" class="w-4 h-4 ml-2" />
        </Button>
      </CardFooter>
    </Card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import apiClient from '@/utils/api'
import DOMPurify from 'dompurify'
import { 
  Card, CardHeader, CardContent, CardFooter,
  Button, Input, Textarea, Progress, Badge, Alert, Label 
} from '@/components/ui'
import { 
  ArrowLeft, ArrowRight, UploadCloud, X, FileText, 
  AlertCircle, Sparkles, RefreshCw, Check, Hash, Bot, Loader2
} from 'lucide-vue-next'

const route = useRoute()
const router = useRouter()

// --- State ---
const sessionId = ref(route.params.sessionId)
const loading = ref(true)
const loadingText = ref('正在初始化问卷...')
const error = ref('')
const isSubmitting = ref(false)
const isRegenerating = ref(false)
const isUploading = ref(false)
const isDragging = ref(false)
const isGeneratingDoc = ref(false)

const title = ref('交通事故法律咨询')
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
const questionHistory = ref([])

// --- Computed ---
const canGoBack = computed(() => {
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
      return !!uploadedFile.value
    } else {
      return currentAnswer.value !== '' && currentAnswer.value !== null
    }
  }
  return true
})

const isFormValid = computed(() => {
  if (!currentQuestion.value || currentQuestion.value.type !== 'form') return false
  return currentQuestion.value.fields.every(f => {
    if (f.required !== false) {
      return formData.value[f.name] && String(formData.value[f.name]).trim()
    }
    return true
  })
})

// --- Methods ---

const formatText = (text) => {
  if (!text) return ''
  const sanitized = DOMPurify.sanitize(text, {
    ALLOWED_TAGS: ['br', 'b', 'i', 'u', 'strong', 'em', 'p'],
    ALLOWED_ATTR: []
  })
  return sanitized.replace(/\\n/g, '<br>').replace(/\n/g, '<br>')
}

const getSubmitButtonText = () => {
  if (!currentQuestion.value) return '下一步'
  if (currentQuestion.value.type === 'message') return currentQuestion.value.continueText || '继续'
  if (currentQuestion.value.submitText) return currentQuestion.value.submitText
  return '下一步'
}

const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const getTemplateName = (code) => {
  const templates = {
    '035': '民事起诉状',
    '008': '授权委托书',
    '002': '民事上诉状'
  }
  return templates[code] || `文书模板`
}

const getSessionFromStorage = () => {
  const stored = sessionStorage.getItem('questionnaire_session')
  return stored ? JSON.parse(stored) : null
}

const initQuestionnaire = async () => {
  loading.value = true
  loadingText.value = '正在初始化问卷...'
  error.value = ''

  try {
    const storedSession = getSessionFromStorage()
    const currentSessionId = route.params.sessionId || storedSession?.sessionId
    
    if (!currentSessionId) throw new Error('会话信息丢失')

    sessionInfo.value = { sessionId: currentSessionId }

    // Resume session
    const response = await apiClient.get(`/workflow/questionnaire/session/${currentSessionId}/resume`)
    const data = response.data

    if (data.success) {
      if (data.status === 'completed') {
        router.push(`/questionnaire/${currentSessionId}/complete`)
        return
      }
      
      if (data.question) {
        currentQuestion.value = data.question
        progress.value = data.progress
        partInfo.value = data.part_info
        
        // Restore answers if available
        if (data.answers && data.question) {
          const qId = data.question.id
          if (data.answers[qId]) {
             const saved = data.answers[qId]
             if(data.question.type === 'form') formData.value = saved.value || saved
             else if(data.question.type === 'checkbox') currentAnswerArray.value = saved.value || saved
             else currentAnswer.value = saved.value || saved
          }
        }
      } else {
        // Fallback or restart
        // error.value = '无法恢复会话进度'
      }
    } else {
      error.value = data.message || '会话状态异常'
    }
  } catch (err) {
    console.error('Init error:', err)
    error.value = err.response?.data?.detail || err.message || '初始化失败'
  } finally {
    loading.value = false
  }
}

const submitAnswer = async () => {
  if (!canSubmit.value) return
  isSubmitting.value = true
  
  try {
    let answerValue
    if (currentQuestion.value.type === 'checkbox') answerValue = currentAnswerArray.value
    else if (currentQuestion.value.type === 'form') answerValue = { ...formData.value }
    else if (currentQuestion.value.type === 'upload') answerValue = uploadedFile.value
    else answerValue = currentAnswer.value

    // Push to history
    questionHistory.value.push({
      question: JSON.parse(JSON.stringify(currentQuestion.value)),
      answer: JSON.parse(JSON.stringify(answerValue)),
      progress: JSON.parse(JSON.stringify(progress.value)),
      partInfo: JSON.parse(JSON.stringify(partInfo.value))
    })

    let fileData = null
    if (currentQuestion.value.type === 'upload' && uploadedFile.value) {
      fileData = {
        filename: uploadedFile.value.name,
        content_type: uploadedFile.value.type,
        base64: uploadedFile.value.base64 || null
      }
    }

    const response = await apiClient.post('/workflow/questionnaire/answer', {
      session_id: sessionInfo.value.sessionId,
      question_id: currentQuestion.value.id,
      answer: answerValue,
      file: fileData
    })

    const data = response.data

    if (data.status === 'completed' || data.completed) {
      sessionStorage.removeItem('questionnaire_session')
      router.push(`/questionnaire/${sessionInfo.value.sessionId}/complete`)
    } else if (data.show_summary) {
      showSummaryReview.value = true
      currentSummary.value = data.summary?.content || data.summary
      currentPart.value = data.current_part
    } else if (data.question) {
      currentQuestion.value = data.question
      progress.value = data.progress
      partInfo.value = data.part_info
      resetAnswers()
      
      if (data.part_info && currentPart.value !== data.part_info.current) {
        currentPart.value = data.part_info.current
        transitionMessage.value = `进入 ${data.part_info.name}`
        setTimeout(() => transitionMessage.value = null, 2000)
      }
    }
  } catch (err) {
    console.error(err)
    alert(err.response?.data?.detail || '提交失败')
    questionHistory.value.pop()
  } finally {
    isSubmitting.value = false
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }
}

const goBack = async () => {
  if (isSubmitting.value) return
  isSubmitting.value = true
  
  try {
    const res = await apiClient.post('/workflow/questionnaire/go-back', {
      session_id: sessionInfo.value.sessionId
    })
    
    if (res.data.success) {
      currentQuestion.value = res.data.question
      progress.value = res.data.progress
      partInfo.value = res.data.part_info
      
      const prevAnswer = res.data.previous_answer
      resetAnswers()
      
      if (prevAnswer !== null && prevAnswer !== undefined) {
        if (currentQuestion.value.type === 'form') {
          formData.value = typeof prevAnswer === 'object' ? { ...prevAnswer } : {}
        } else if (currentQuestion.value.type === 'checkbox') {
          currentAnswerArray.value = Array.isArray(prevAnswer) ? [...prevAnswer] : []
        } else {
          currentAnswer.value = (typeof prevAnswer === 'object' && prevAnswer.value) ? prevAnswer.value : prevAnswer
        }
      }
    }
  } catch (e) {
    // Fallback to local history
    if (questionHistory.value.length > 0) {
      const last = questionHistory.value.pop()
      currentQuestion.value = last.question
      progress.value = last.progress
      partInfo.value = last.partInfo
      if (last.question.type === 'form') formData.value = last.answer
      else if (last.question.type === 'checkbox') currentAnswerArray.value = last.answer
      else currentAnswer.value = last.answer
    }
  } finally {
    isSubmitting.value = false
  }
}

const toggleCheckbox = (option) => {
  const idx = currentAnswerArray.value.indexOf(option)
  if (idx === -1) currentAnswerArray.value.push(option)
  else currentAnswerArray.value.splice(idx, 1)
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
  if (file.size > 10 * 1024 * 1024) {
    alert('文件大小不能超过10MB')
    return
  }
  
  isUploading.value = true
  uploadedFile.value = { name: file.name, size: file.size, type: file.type }
  
  try {
    const formDataPayload = new FormData()
    formDataPayload.append('file', file)
    formDataPayload.append('session_id', sessionInfo.value.sessionId)
    formDataPayload.append('question_id', currentQuestion.value.id)
    
    const res = await apiClient.post('/workflow/questionnaire/upload', formDataPayload)
    
    if (res.data.success) {
      uploadedFile.value = {
        ...uploadedFile.value,
        id: res.data.file_id,
        ocrText: res.data.ocr_result?.text || null
      }
    }
  } catch (e) {
    alert('文件上传失败')
    uploadedFile.value = null
  } finally {
    isUploading.value = false
  }
}

const removeFile = () => { uploadedFile.value = null }

const requestRegenerate = async () => {
  isRegenerating.value = true
  try {
    const res = await apiClient.post('/workflow/questionnaire/validate-summary', {
      session_id: sessionInfo.value.sessionId,
      approved: false,
      feedback: '重新生成'
    })
    if (res.data.summary) currentSummary.value = res.data.summary.content || res.data.summary
  } catch (e) { alert('生成失败') } finally { isRegenerating.value = false }
}

const confirmSummary = async () => {
  isSubmitting.value = true
  try {
    const res = await apiClient.post('/workflow/questionnaire/validate-summary', {
      session_id: sessionInfo.value.sessionId,
      approved: true
    })
    
    showSummaryReview.value = false
    currentSummary.value = null
    
    if (res.data.status === 'completed' || res.data.completed) {
      router.push(`/questionnaire/${sessionInfo.value.sessionId}/complete`)
    } else if (res.data.question) {
      currentQuestion.value = res.data.question
      progress.value = res.data.progress
      partInfo.value = res.data.part_info
      resetAnswers()
    }
  } catch (e) { alert('确认失败') } finally { isSubmitting.value = false }
}

const previewDocument = async (templateCode) => {
  isGeneratingDoc.value = true
  try {
    const res = await apiClient.post('/workflow/questionnaire/generate-document', {
      session_id: sessionInfo.value.sessionId,
      template_code: templateCode,
      preview_only: true
    })
    if(res.data.download_url) window.open(res.data.download_url, '_blank')
    else alert('生成失败')
  } catch (e) { alert('生成预览失败') } finally { isGeneratingDoc.value = false }
}

const retryInit = () => initQuestionnaire()

onMounted(initQuestionnaire)
</script>