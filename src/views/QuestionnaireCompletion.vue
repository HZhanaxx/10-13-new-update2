<template>
  <div class="flex min-h-screen bg-slate-50/50">
    <div class="flex-1 p-8 overflow-y-auto">
      <div class="max-w-4xl mx-auto space-y-8">
        
        <div class="flex items-center justify-between">
          <div class="space-y-1">
            <h1 class="text-3xl font-bold tracking-tight text-foreground flex items-center gap-2">
              <CheckCircle2 class="h-8 w-8 text-emerald-500" /> 问卷完成
            </h1>
            <p class="text-muted-foreground">您的信息已收集完毕，请确认以下后续操作</p>
          </div>
          <Button variant="outline" @click="goToDashboard">
            返回仪表板
          </Button>
        </div>

        <div v-if="loading" class="space-y-6">
          <Skeleton class="h-40 w-full rounded-xl" />
          <div class="grid md:grid-cols-2 gap-6">
            <Skeleton class="h-64 w-full rounded-xl" />
            <Skeleton class="h-64 w-full rounded-xl" />
          </div>
        </div>

        <Alert v-else-if="error" variant="destructive">
          <AlertTriangle class="h-4 w-4" />
          <div class="ml-2">
            <h3 class="font-medium">加载失败</h3>
            <p class="text-sm opacity-90">{{ error }}</p>
            <Button variant="outline" size="sm" class="mt-3 bg-white/10 hover:bg-white/20 border-white/20" @click="loadCompletionData">
              重试
            </Button>
          </div>
        </Alert>

        <div v-else class="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
          
          <Card v-if="finalizationResult" class="border-emerald-200 bg-emerald-50/30">
            <CardHeader>
              <div class="flex items-center gap-3">
                <div class="p-2 bg-emerald-100 rounded-full text-emerald-600">
                  <Check v-if="finalizationResult.success" class="h-6 w-6" />
                  <AlertTriangle v-else class="h-6 w-6 text-red-600" />
                </div>
                <div>
                  <CardTitle :class="finalizationResult.success ? 'text-emerald-700' : 'text-red-700'">
                    {{ finalizationResult.success ? '操作成功完成' : '部分操作失败' }}
                  </CardTitle>
                  <CardDescription>
                    您的提交已处理
                  </CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent class="space-y-4">
              <div v-if="finalizationResult.answers_saved" class="flex items-center gap-2 text-sm text-slate-600">
                <CheckCircle2 class="h-4 w-4 text-emerald-500" />
                问卷答案已保存 (共 {{ finalizationResult.answers_count }} 题)
              </div>
              
              <div v-if="finalizationResult.case" class="bg-white p-4 rounded-lg border border-emerald-100 shadow-sm">
                <div class="flex justify-between items-start">
                  <div>
                    <h4 class="font-medium text-emerald-900">案件已创建</h4>
                    <p class="text-sm text-emerald-700 mt-1">{{ finalizationResult.case.title }}</p>
                  </div>
                  <Button size="sm" variant="outline" class="text-emerald-700 border-emerald-200 hover:bg-emerald-50" @click="viewCase">
                    查看案件
                  </Button>
                </div>
              </div>

              <div v-if="finalizationResult.case_error" class="bg-red-50 p-4 rounded-lg border border-red-100 text-sm text-red-700 flex items-start gap-2">
                <AlertTriangle class="h-4 w-4 mt-0.5 shrink-0" />
                案件创建失败: {{ finalizationResult.case_error }}
              </div>

              <div v-if="finalizationResult.generated_documents?.length > 0" class="space-y-2">
                <h4 class="font-medium text-sm text-slate-700">已生成文书</h4>
                <div class="grid gap-2">
                  <div v-for="doc in finalizationResult.generated_documents" :key="doc.template_code" 
                    class="flex items-center justify-between p-3 bg-white rounded border text-sm"
                  >
                    <div class="flex items-center gap-2">
                      <FileText class="h-4 w-4 text-blue-500" />
                      <span class="font-medium">{{ doc.filename || doc.template_code }}</span>
                      <span v-if="!doc.success" class="text-red-500 text-xs ml-2">{{ doc.error }}</span>
                    </div>
                    <a v-if="doc.download_url" :href="doc.download_url" download class="btn-link text-primary hover:underline text-xs flex items-center">
                      <Download class="h-3 w-3 mr-1" /> 下载
                    </a>
                  </div>
                </div>
              </div>
            </CardContent>
            <CardFooter>
              <Button class="w-full" @click="goToDashboard">返回仪表板</Button>
            </CardFooter>
          </Card>

          <template v-else>
            
            <Card>
              <CardHeader>
                <CardTitle class="flex items-center gap-2">
                  <Sparkles class="h-5 w-5 text-purple-500" />
                  AI 案情分析
                </CardTitle>
                <CardDescription>基于您的回答生成的智能分析摘要</CardDescription>
              </CardHeader>
              <CardContent>
                <div class="grid gap-4">
                  <div v-for="(summary, partKey) in summaries" :key="partKey" class="bg-slate-50 p-4 rounded-lg border border-slate-100">
                    <div class="flex items-center gap-2 mb-2">
                      <Badge variant="outline" class="bg-white">{{ getPartTitle(partKey) }}</Badge>
                    </div>
                    <p class="text-sm text-slate-600 leading-relaxed">{{ summary.content || summary }}</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card v-if="evidenceList && evidenceList.length > 0">
              <CardHeader>
                <CardTitle class="flex items-center gap-2">
                  <FolderOpen class="h-5 w-5 text-blue-500" />
                  证据清单
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div v-for="(evidence, idx) in evidenceList" :key="idx" class="flex items-center p-3 border rounded-lg bg-slate-50/50">
                    <Badge variant="secondary" class="mr-3">{{ evidence.evidenceNumber || `#${idx + 1}` }}</Badge>
                    <span class="text-sm font-medium truncate">{{ evidence.fileName || evidence.filename }}</span>
                  </div>
                </div>
              </CardContent>
            </Card>

            <div class="grid md:grid-cols-2 gap-6">
              <Card class="h-full flex flex-col">
                <CardHeader>
                  <CardTitle class="flex items-center gap-2">
                    <Scale class="h-5 w-5 text-emerald-600" />
                    案件发布
                  </CardTitle>
                  <CardDescription>将此咨询转化为正式案件，寻找律师</CardDescription>
                </CardHeader>
                <CardContent class="space-y-4 flex-1">
                  <div v-if="isFinalized && caseUuid" class="bg-emerald-50 text-emerald-700 p-4 rounded-lg flex flex-col items-center justify-center h-full text-center space-y-2">
                    <CheckCircle2 class="h-8 w-8" />
                    <p class="font-medium">案件已创建</p>
                    <Button size="sm" variant="outline" class="border-emerald-200 text-emerald-700 hover:bg-emerald-100" @click="viewCase">
                      查看详情
                    </Button>
                  </div>

                  <div v-else class="space-y-4">
                    <div 
                      class="border-2 rounded-xl p-4 cursor-pointer transition-all duration-200"
                      :class="createCase ? 'border-primary bg-primary/5' : 'border-muted hover:border-muted-foreground/50'"
                      @click="createCase = !createCase"
                    >
                      <div class="flex items-start gap-3">
                        <Checkbox :checked="createCase" @update:checked="createCase = $event" class="mt-1" />
                        <div>
                          <h4 class="font-medium text-foreground">发布到案件池</h4>
                          <p class="text-sm text-muted-foreground mt-1">
                            推荐！将案件发布给平台认证律师，获得专业法律援助。
                          </p>
                        </div>
                      </div>
                    </div>

                    <div v-if="createCase" class="space-y-4 pt-2 animate-in slide-in-from-top-2">
                      <div class="space-y-2">
                        <Label>案件标题</Label>
                        <Input v-model="caseTitle" :placeholder="defaultCaseTitle" />
                      </div>
                      <div class="space-y-2">
                        <Label>优先级</Label>
                        <Select v-model="casePriority">
                          <option value="low">低 - 不着急</option>
                          <option value="medium">中 - 正常处理</option>
                          <option value="high">高 - 尽快处理</option>
                          <option value="urgent">紧急 - 立即处理</option>
                        </Select>
                      </div>
                    </div>

                    <Alert v-if="shouldCreateCase && !createCase" class="bg-amber-50 text-amber-800 border-amber-200">
                      <Lightbulb class="h-4 w-4 text-amber-600" />
                      <div class="ml-2 text-xs">
                        根据您的回答，系统建议您发布案件以获得专业帮助。
                      </div>
                    </Alert>
                  </div>
                </CardContent>
              </Card>

              <Card class="h-full flex flex-col">
                <CardHeader>
                  <CardTitle class="flex items-center gap-2">
                    <FileText class="h-5 w-5 text-blue-600" />
                    文书生成
                  </CardTitle>
                  <CardDescription>基于案情自动生成法律文书草稿</CardDescription>
                </CardHeader>
                <CardContent class="flex-1">
                  <div class="space-y-3">
                    <p class="text-sm text-muted-foreground mb-2">选择需要生成的文书：</p>
                    <div 
                      v-for="template in recommendedTemplates" 
                      :key="template.code"
                      class="flex items-start space-x-3 p-3 rounded-lg border transition-colors hover:bg-slate-50 cursor-pointer"
                      :class="selectedTemplates.includes(template.code) ? 'border-primary bg-primary/5 ring-1 ring-primary ring-offset-0' : ''"
                      @click="toggleTemplate(template.code)"
                    >
                      <Checkbox 
                        :checked="selectedTemplates.includes(template.code)"
                        @update:checked="toggleTemplate(template.code)" 
                        class="mt-1"
                      />
                      <div class="space-y-1">
                        <p class="text-sm font-medium leading-none">{{ template.name }}</p>
                        <p class="text-xs text-muted-foreground">{{ template.description }}</p>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>

            <div class="flex flex-col items-center gap-4 pt-6 pb-12">
              <Button 
                v-if="!isFinalized"
                size="lg" 
                class="w-full md:w-1/3 text-lg h-12 shadow-lg"
                @click="finalizeQuestionnaire" 
                :loading="isSubmitting"
              >
                {{ createCase ? '确认并发布案件' : '确认完成' }}
              </Button>
              <Button variant="ghost" @click="goToDashboard" class="text-muted-foreground">
                稍后再说，返回首页
              </Button>
            </div>

          </template>
        </div>

      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '@/utils/api'
import { 
  Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter,
  Button, Badge, Skeleton, Alert, Input, Label, Select, Checkbox 
} from '@/components/ui'
import { 
  CheckCircle2, AlertTriangle, ArrowRight, Sparkles, FolderOpen, 
  Scale, FileText, Download, Check, Lightbulb 
} from 'lucide-vue-next'

const route = useRoute()
const router = useRouter()

// State
const loading = ref(true)
const error = ref('')
const isSubmitting = ref(false)

const sessionId = ref('')
const isFinalized = ref(false)
const caseUuid = ref(null)
const shouldCreateCase = ref(false)
const answers = ref({})
const summaries = ref({})
const evidenceList = ref([])
const recommendedTemplates = ref([])
const generatedDocs = ref([])

// Form state
const createCase = ref(false)
const caseTitle = ref('')
const casePriority = ref('medium')
const selectedTemplates = ref([])

const finalizationResult = ref(null)

// Computed
const defaultCaseTitle = computed(() => {
  const accidentType = answers.value?.q2?.value || '交通事故'
  const date = new Date().toISOString().slice(0, 10).replace(/-/g, '')
  return `${accidentType}案件 - ${date}`
})

// Methods
const loadCompletionData = async () => {
  loading.value = true
  error.value = ''
  
  try {
    sessionId.value = route.params.sessionId
    
    const response = await api.get(`/workflow/questionnaire/session/${sessionId.value}/completion-data`)
    const data = response.data
    
    if (data.success) {
      isFinalized.value = data.is_finalized
      caseUuid.value = data.case_uuid
      shouldCreateCase.value = data.should_create_case
      answers.value = data.answers || {}
      summaries.value = data.summaries || {}
      evidenceList.value = data.evidence_list || []
      recommendedTemplates.value = data.recommended_templates || []
      
      // Pre-select create case if should_create_case is true
      if (shouldCreateCase.value && !isFinalized.value) {
        createCase.value = true
      }
      
      // Pre-select recommended templates (priority 1)
      if (recommendedTemplates.value.length > 0 && !isFinalized.value) {
        selectedTemplates.value = recommendedTemplates.value
          .filter(t => t.priority === 1)
          .map(t => t.code)
      }
    } else {
      error.value = data.message || '无法加载数据'
    }
  } catch (err) {
    console.error('Load completion data error:', err)
    error.value = err.response?.data?.detail || err.message || '加载失败'
  } finally {
    loading.value = false
  }
}

const toggleTemplate = (code) => {
  const index = selectedTemplates.value.indexOf(code)
  if (index === -1) selectedTemplates.value.push(code)
  else selectedTemplates.value.splice(index, 1)
}

const finalizeQuestionnaire = async () => {
  isSubmitting.value = true
  finalizationResult.value = null
  
  try {
    const response = await api.post('/workflow/questionnaire/finalize', {
      session_id: sessionId.value,
      create_case: createCase.value,
      case_title: caseTitle.value || defaultCaseTitle.value,
      case_priority: casePriority.value,
      selected_templates: selectedTemplates.value
    })
    
    finalizationResult.value = response.data
    
    if (response.data.success) {
      isFinalized.value = true
      if (response.data.case) {
        caseUuid.value = response.data.case.case_uuid
      }
      if (response.data.generated_documents) {
        generatedDocs.value = response.data.generated_documents
      }
    }
  } catch (err) {
    console.error('Finalize error:', err)
    finalizationResult.value = {
      success: false,
      error: err.response?.data?.detail || err.message
    }
  } finally {
    isSubmitting.value = false
  }
}

const viewCase = () => {
  if (caseUuid.value) {
    router.push(`/case/${caseUuid.value}`)
  }
}

const goToDashboard = () => {
  router.push('/dashboard')
}

const getPartTitle = (partKey) => {
  const titles = {
    'part1': '基本信息',
    'part2': '事故详情',
    'part3': '赔偿诉求'
  }
  return titles[partKey] || partKey
}

onMounted(loadCompletionData)
</script>