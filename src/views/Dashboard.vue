<template>
  <div class="flex min-h-screen bg-slate-50/50">
    <Sidebar />
    
    <main class="flex-1 p-8 ml-64 overflow-y-auto">
      <div class="max-w-6xl mx-auto space-y-8">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div class="space-y-1">
            <h1 class="text-3xl font-bold tracking-tight text-foreground">欢迎回来, {{ authStore.userName }}</h1>
            <p class="text-muted-foreground">这里是您的案件概览与智能服务中心</p>
          </div>
          <div class="flex gap-3">
            <Button variant="secondary" @click="showQuestionnaireModal = true">
              <ClipboardList class="w-4 h-4 mr-2" />
              智能问卷咨询
            </Button>
            <Button @click="$router.push('/cases/new')">
              <Plus class="w-4 h-4 mr-2" />
              新建案件
            </Button>
          </div>
        </div>

        <div v-if="isLoading" class="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          <Card v-for="i in 3" :key="i" class="flex flex-col justify-between h-[220px]">
            <CardHeader class="pb-4">
              <div class="flex justify-between">
                <Skeleton class="h-5 w-20 rounded-full" />
                <Skeleton class="h-3 w-3 rounded-full" />
              </div>
              <Skeleton class="h-6 w-3/4 mt-2" />
            </CardHeader>
            <CardContent>
              <Skeleton class="h-4 w-full mb-2" />
              <Skeleton class="h-4 w-5/6" />
            </CardContent>
            <CardFooter class="pt-4 border-t">
              <Skeleton class="h-4 w-24" />
            </CardFooter>
          </Card>
        </div>

        <div v-else-if="cases.length > 0" class="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          <transition-group name="fade" appear>
            <Card 
              v-for="c in cases" 
              :key="c.case_uuid" 
              class="cursor-pointer hover:shadow-lg transition-all duration-300 hover:-translate-y-1 group border-muted/60"
              @click="$router.push(`/case/${c.case_uuid}`)"
            >
              <CardHeader class="flex flex-row items-center justify-between space-y-0 pb-3">
                <Badge variant="outline" class="font-normal bg-secondary/50 hover:bg-secondary">
                  {{ c.case_category || '未分类' }}
                </Badge>
                <div 
                  class="flex items-center gap-1.5 text-[10px] font-medium uppercase tracking-wider px-2 py-0.5 rounded-full"
                  :class="getStatusStyle(c.case_status)"
                >
                  <div class="h-1.5 w-1.5 rounded-full bg-current" />
                  {{ getStatusText(c.case_status) }}
                </div>
              </CardHeader>
              
              <CardContent class="pb-4">
                <h3 class="font-semibold text-lg mb-2 line-clamp-1 group-hover:text-primary transition-colors">
                  {{ c.title }}
                </h3>
                <p class="text-sm text-muted-foreground line-clamp-3 min-h-[60px] leading-relaxed">
                  {{ c.description }}
                </p>
              </CardContent>
              
              <CardFooter class="text-xs text-muted-foreground border-t pt-4 mt-auto justify-between bg-slate-50/30 rounded-b-xl">
                <span class="flex items-center font-medium">
                  <Banknote class="w-3.5 h-3.5 mr-1.5 text-emerald-600" />
                  {{ c.budget_cny ? `¥${c.budget_cny}` : '面议' }}
                </span>
                <span class="flex items-center">
                  <Clock class="w-3.5 h-3.5 mr-1.5" />
                  {{ formatDate(c.created_at) }}
                </span>
              </CardFooter>
            </Card>
          </transition-group>
        </div>

        <div v-else class="flex flex-col items-center justify-center py-20 text-center border-2 border-dashed rounded-xl border-muted bg-slate-50/50">
          <div class="p-4 bg-white rounded-full shadow-sm mb-4">
            <FolderOpen class="w-10 h-10 text-muted-foreground/50" />
          </div>
          <h3 class="text-xl font-semibold mb-2">暂无案件</h3>
          <p class="text-muted-foreground max-w-sm mb-6">您还没有发布任何法律咨询或案件。开始您的第一次法律咨询吧。</p>
          <Button size="lg" @click="$router.push('/cases/new')">
            <Plus class="w-4 h-4 mr-2" /> 立即发布
          </Button>
        </div>
      </div>
    </main>

    <Dialog :open="showQuestionnaireModal" @close="showQuestionnaireModal = false">
      <div class="space-y-6 p-1">
        <div class="space-y-2 text-center">
          <div class="mx-auto w-12 h-12 bg-primary/10 rounded-full flex items-center justify-center mb-3">
            <Car class="w-6 h-6 text-primary" />
          </div>
          <h2 class="text-xl font-bold">交通事故法律咨询</h2>
          <p class="text-sm text-muted-foreground px-4">
            AI 智能助手将协助您梳理案情，生成专业法律文书，并为您匹配合适的律师。
          </p>
        </div>
        
        <div class="grid gap-3">
          <div class="flex items-start gap-4 p-3 bg-secondary/30 rounded-lg hover:bg-secondary/50 transition-colors">
            <div class="mt-1 bg-white p-1.5 rounded-md shadow-sm">
              <FileText class="w-4 h-4 text-primary" />
            </div>
            <div class="text-sm">
              <p class="font-medium text-foreground">案情梳理</p>
              <p class="text-muted-foreground text-xs mt-0.5">系统化收集事故信息，生成清晰的案件摘要</p>
            </div>
          </div>
          
          <div class="flex items-start gap-4 p-3 bg-secondary/30 rounded-lg hover:bg-secondary/50 transition-colors">
            <div class="mt-1 bg-white p-1.5 rounded-md shadow-sm">
              <Sparkles class="w-4 h-4 text-primary" />
            </div>
            <div class="text-sm">
              <p class="font-medium text-foreground">AI 智能分析</p>
              <p class="text-muted-foreground text-xs mt-0.5">基于法律法规分析责任归属、赔偿标准及风险点</p>
            </div>
          </div>
          
          <div class="flex items-start gap-4 p-3 bg-secondary/30 rounded-lg hover:bg-secondary/50 transition-colors">
            <div class="mt-1 bg-white p-1.5 rounded-md shadow-sm">
              <Gavel class="w-4 h-4 text-primary" />
            </div>
            <div class="text-sm">
              <p class="font-medium text-foreground">专业对接</p>
              <p class="text-muted-foreground text-xs mt-0.5">自动生成起诉状等文档，并匹配合适的专业律师</p>
            </div>
          </div>
        </div>

        <div class="flex flex-col gap-3 pt-2">
          <Button size="lg" class="w-full" @click="launchQuestionnaire" :loading="isLaunching">
            {{ isLaunching ? '系统准备中...' : '开始咨询 (预计10分钟)' }}
          </Button>
          <Button variant="ghost" size="sm" class="w-full text-muted-foreground" @click="showQuestionnaireModal = false">
            稍后再说
          </Button>
        </div>
      </div>
    </Dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import apiClient from '@/utils/api'
import Sidebar from '@/components/Sidebar.vue'
import { 
  Card, CardHeader, CardContent, CardFooter, 
  Button, Badge, Skeleton, Dialog 
} from '@/components/ui'
import { 
  Plus, ClipboardList, Clock, Banknote, 
  FolderOpen, Car, FileText, Sparkles, Gavel 
} from 'lucide-vue-next'

const router = useRouter()
const authStore = useAuthStore()
const cases = ref([])
const isLoading = ref(true)
const showQuestionnaireModal = ref(false)
const isLaunching = ref(false)

const loadCases = async () => {
  try {
    const res = await apiClient.get('/cases/my-cases')
    cases.value = res.data.cases || []
  } catch (e) {
    console.error(e)
  } finally {
    isLoading.value = false
  }
}

const formatDate = (d) => new Date(d).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })

const getStatusStyle = (status) => {
  const map = {
    pending: 'bg-amber-100 text-amber-700',
    in_progress: 'bg-blue-100 text-blue-700',
    completed: 'bg-emerald-100 text-emerald-700',
    cancelled: 'bg-slate-100 text-slate-600'
  }
  return map[status] || 'bg-slate-100 text-slate-600'
}

const getStatusText = (status) => {
  const map = {
    pending: '待接单',
    in_progress: '处理中',
    completed: '已结案',
    cancelled: '已取消'
  }
  return map[status] || '未知'
}

const launchQuestionnaire = async () => {
  isLaunching.value = true
  try {
    // Call the new LangGraph workflow API
    const res = await apiClient.post('/workflow/questionnaire/start', {
      template_type: 1  // Traffic accident template
    })
    
    if (res.data.success) {
      // Store session info
      const sessionData = {
        sessionId: res.data.session_id,
        status: res.data.status,
        question: res.data.question,
        partInfo: res.data.part_info,
        progress: res.data.progress
      }
      
      sessionStorage.setItem('questionnaire_session', JSON.stringify(sessionData))
      showQuestionnaireModal.value = false
      router.push(`/questionnaire/${res.data.session_id}`)
    }
  } catch (error) {
    console.error('Failed to start questionnaire:', error)
    alert('启动问卷失败，请稍后重试')
  } finally {
    isLaunching.value = false
  }
}

onMounted(loadCases)
</script>

<style scoped>
/* Optional transition for list items */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease, transform 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
  transform: translateY(10px);
}
</style>