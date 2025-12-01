<template>
  <div class="flex min-h-screen bg-slate-50/50">
    <Sidebar />
    
    <main class="flex-1 p-8 ml-64 overflow-y-auto">
      <div v-if="checkingVerification" class="flex flex-col items-center justify-center h-[80vh] space-y-4">
        <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
        <p class="text-muted-foreground">正在验证专业身份...</p>
      </div>

      <div v-else-if="isVerified" class="max-w-7xl mx-auto space-y-6">
        
        <div class="flex flex-col gap-1">
          <h1 class="text-3xl font-bold tracking-tight text-foreground flex items-center gap-2">
            <Briefcase class="h-8 w-8 text-primary" /> 案件池
          </h1>
          <p class="text-muted-foreground">浏览并筛选适合您的法律案件，高效对接客户需求</p>
        </div>

        <div class="grid gap-4 md:grid-cols-3">
          <Card class="bg-gradient-to-br from-white to-blue-50/50">
            <CardHeader class="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle class="text-sm font-medium">可接案件</CardTitle>
              <div class="h-8 w-8 rounded-lg bg-blue-100 flex items-center justify-center">
                <Layers class="h-4 w-4 text-blue-600" />
              </div>
            </CardHeader>
            <CardContent>
              <div class="text-2xl font-bold">{{ cases.length }}</div>
              <p class="text-xs text-muted-foreground mt-1">当前符合筛选条件的案件</p>
            </CardContent>
          </Card>

          <Card class="bg-gradient-to-br from-white to-emerald-50/50">
            <CardHeader class="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle class="text-sm font-medium">今日新增</CardTitle>
              <div class="h-8 w-8 rounded-lg bg-emerald-100 flex items-center justify-center">
                <Clock class="h-4 w-4 text-emerald-600" />
              </div>
            </CardHeader>
            <CardContent>
              <div class="text-2xl font-bold">{{ filterStats.todayCases }}</div>
              <p class="text-xs text-muted-foreground mt-1">24小时内发布的新需求</p>
            </CardContent>
          </Card>

          <Card class="bg-gradient-to-br from-white to-amber-50/50">
            <CardHeader class="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle class="text-sm font-medium">平均预算</CardTitle>
              <div class="h-8 w-8 rounded-lg bg-amber-100 flex items-center justify-center">
                <Banknote class="h-4 w-4 text-amber-600" />
              </div>
            </CardHeader>
            <CardContent>
              <div class="text-2xl font-bold">¥{{ filterStats.avgBudget.toLocaleString() }}</div>
              <p class="text-xs text-muted-foreground mt-1">当前列表案件平均预算</p>
            </CardContent>
          </Card>
        </div>

        <Card class="p-4">
          <div class="flex flex-col md:flex-row gap-4 items-end md:items-center">
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4 flex-1 w-full">
              <div class="space-y-1">
                <Label class="text-xs text-muted-foreground">案件类别</Label>
                <Select v-model="filters.category" @change="loadCases">
                  <option value="">全部类别</option>
                  <option value="劳动纠纷">劳动纠纷</option>
                  <option value="合同纠纷">合同纠纷</option>
                  <option value="债务纠纷">债务纠纷</option>
                  <option value="交通事故">交通事故</option>
                  <option value="医疗纠纷">医疗纠纷</option>
                  <option value="房产纠纷">房产纠纷</option>
                  <option value="知识产权">知识产权</option>
                  <option value="婚姻家庭">婚姻家庭</option>
                  <option value="其他">其他</option>
                </Select>
              </div>
              
              <div class="space-y-1">
                <Label class="text-xs text-muted-foreground">预算范围</Label>
                <Select v-model="filters.budget" @change="loadCases">
                  <option value="">全部预算</option>
                  <option value="0-5000">¥0 - ¥5,000</option>
                  <option value="5000-10000">¥5,000 - ¥10,000</option>
                  <option value="10000-20000">¥10,000 - ¥20,000</option>
                  <option value="20000+">¥20,000+</option>
                </Select>
              </div>

              <div class="space-y-1">
                <Label class="text-xs text-muted-foreground">排序方式</Label>
                <Select v-model="filters.sort" @change="loadCases">
                  <option value="newest">最新发布</option>
                  <option value="highest_budget">预算最高</option>
                  <option value="urgent">紧急优先</option>
                </Select>
              </div>
            </div>
            
            <div class="flex gap-2 w-full md:w-auto">
              <Button variant="outline" @click="resetFilters" class="w-full md:w-auto">
                <RotateCcw class="w-4 h-4 mr-2" /> 重置
              </Button>
              <Button @click="loadCases" class="w-full md:w-auto">
                <Filter class="w-4 h-4 mr-2" /> 筛选
              </Button>
            </div>
          </div>
        </Card>

        <div v-if="isLoading" class="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
          <Card v-for="i in 6" :key="i" class="h-[280px] flex flex-col">
            <CardHeader>
              <div class="flex justify-between mb-2">
                <Skeleton class="h-6 w-20" />
                <Skeleton class="h-6 w-6 rounded-full" />
              </div>
              <Skeleton class="h-6 w-3/4" />
            </CardHeader>
            <CardContent class="flex-1">
              <Skeleton class="h-4 w-full mb-2" />
              <Skeleton class="h-4 w-5/6 mb-2" />
              <Skeleton class="h-4 w-4/6" />
            </CardContent>
            <CardFooter class="border-t pt-4">
              <Skeleton class="h-10 w-full" />
            </CardFooter>
          </Card>
        </div>

        <div v-else-if="cases.length > 0" class="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
          <transition-group name="fade" appear>
            <Card 
              v-for="caseItem in cases" 
              :key="caseItem.case_uuid"
              class="group hover:shadow-lg transition-all duration-300 hover:-translate-y-1 flex flex-col h-full border-muted/60"
            >
              <CardHeader class="pb-3">
                <div class="flex justify-between items-start mb-2">
                  <Badge 
                    :variant="isUrgent(caseItem) ? 'destructive' : 'secondary'"
                    class="font-normal"
                  >
                    {{ isUrgent(caseItem) ? '🔥 紧急案件' : caseItem.case_category }}
                  </Badge>
                  <span class="text-xs text-muted-foreground bg-slate-50 px-2 py-1 rounded">
                    {{ formatDate(caseItem.created_at) }}
                  </span>
                </div>
                <h3 class="font-semibold text-lg leading-tight line-clamp-1 group-hover:text-primary transition-colors">
                  {{ caseItem.title }}
                </h3>
              </CardHeader>
              
              <CardContent class="flex-1 pb-4">
                <p class="text-sm text-muted-foreground line-clamp-3 mb-4 min-h-[60px]">
                  {{ caseItem.description }}
                </p>
                
                <div class="grid grid-cols-2 gap-2 text-xs">
                  <div class="bg-slate-50 p-2 rounded flex items-center gap-2">
                    <Banknote class="w-3.5 h-3.5 text-emerald-600" />
                    <span class="font-medium text-emerald-700">
                      ¥{{ caseItem.budget_cny ? Number(caseItem.budget_cny).toLocaleString() : '面议' }}
                    </span>
                  </div>
                  <div class="bg-slate-50 p-2 rounded flex items-center gap-2">
                    <MapPin class="w-3.5 h-3.5 text-slate-500" />
                    <span class="text-slate-700 truncate">
                      {{ caseItem.location || '线上/未指定' }}
                    </span>
                  </div>
                </div>

                <div v-if="caseItem.requirements" class="mt-3 p-2 bg-amber-50/50 rounded border border-amber-100 text-xs text-amber-800">
                  <span class="font-bold">要求:</span> {{ truncate(caseItem.requirements, 40) }}
                </div>
              </CardContent>
              
              <CardFooter class="pt-0 pb-4 px-6 flex gap-3 mt-auto">
                <Button variant="outline" class="flex-1" @click="viewCaseDetail(caseItem.case_uuid)">
                  详情
                </Button>
                <Button class="flex-1" @click="acceptCase(caseItem.case_uuid)">
                  立即接单
                </Button>
              </CardFooter>
            </Card>
          </transition-group>
        </div>

        <div v-else class="flex flex-col items-center justify-center py-24 bg-white rounded-xl border border-dashed text-center">
          <div class="w-16 h-16 bg-slate-50 rounded-full flex items-center justify-center mb-4">
            <Search class="w-8 h-8 text-muted-foreground/50" />
          </div>
          <h3 class="text-lg font-medium text-foreground mb-1">暂无符合条件的案件</h3>
          <p class="text-sm text-muted-foreground max-w-sm mb-6">当前筛选条件下没有找到可接案件，尝试调整筛选条件或稍后再来看看。</p>
          <Button variant="outline" @click="resetFilters">
            重置所有筛选
          </Button>
        </div>
      </div>
    </main>

    <Dialog :open="showAcceptModal" @close="showAcceptModal = false">
      <div class="space-y-6">
        <div class="text-center space-y-2">
          <div class="mx-auto w-12 h-12 bg-emerald-100 rounded-full flex items-center justify-center mb-2">
            <CheckCircle2 class="w-6 h-6 text-emerald-600" />
          </div>
          <h2 class="text-xl font-bold">确认接受案件</h2>
          <p class="text-sm text-muted-foreground">接单后请及时与客户联系，长期不处理可能会影响您的评分。</p>
        </div>

        <div v-if="selectedCase" class="bg-slate-50 p-4 rounded-lg space-y-3 border">
          <div>
            <span class="text-xs text-muted-foreground">案件标题</span>
            <p class="font-medium text-sm">{{ selectedCase.title }}</p>
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div>
              <span class="text-xs text-muted-foreground">预算</span>
              <p class="font-medium text-emerald-600">¥{{ selectedCase.budget_cny }}</p>
            </div>
            <div>
              <span class="text-xs text-muted-foreground">类别</span>
              <p class="text-sm">{{ selectedCase.case_category }}</p>
            </div>
          </div>
        </div>

        <div class="flex justify-end gap-3 pt-2">
          <Button variant="ghost" @click="showAcceptModal = false">取消</Button>
          <Button @click="confirmAcceptCase" class="bg-emerald-600 hover:bg-emerald-700 text-white">
            确认接单
          </Button>
        </div>
      </div>
    </Dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import Sidebar from '@/components/Sidebar.vue'
import apiClient from '@/utils/api'
import { 
  Card, CardHeader, CardTitle, CardContent, CardFooter,
  Button, Badge, Skeleton, Dialog, Select, Label
} from '@/components/ui'
import { 
  Briefcase, Layers, Clock, Banknote, Filter, 
  RotateCcw, MapPin, Search, CheckCircle2
} from 'lucide-vue-next'

const router = useRouter()
const authStore = useAuthStore()

// State
const isLoading = ref(false)
const cases = ref([])
const showAcceptModal = ref(false)
const selectedCase = ref(null)
const checkingVerification = ref(true)
const isVerified = ref(false)

const filters = ref({
  category: '',
  budget: '',
  sort: 'newest'
})

// Computed
const filterStats = computed(() => {
  const today = new Date().toDateString()
  const todayCases = cases.value.filter(c => 
    new Date(c.created_at).toDateString() === today
  ).length
  
  const avgBudget = cases.value.length > 0
    ? Math.round(cases.value.reduce((sum, c) => sum + (c.budget_cny || 0), 0) / cases.value.length)
    : 0
  
  return { todayCases, avgBudget }
})

// Check verification
const checkVerification = async () => {
  checkingVerification.value = true
  try {
    const response = await apiClient.get('/professional/verification-status')
    const data = response.data
    isVerified.value = data.is_verified
    
    if (!data.is_verified) {
      if (data.status === 'pending') {
        alert('您的认证申请正在审核中,审核通过后即可访问案件池')
      } else {
        alert('您需要完成专业认证后才能访问案件池')
      }
      router.push('/professional')
      return false
    }
    return true
  } catch (error) {
    console.error('Failed to check verification:', error)
    router.push('/professional')
    return false
  } finally {
    checkingVerification.value = false
  }
}

// Methods
const loadCases = async () => {
  isLoading.value = true
  try {
    const params = {}
    if (filters.value.category) params.category = filters.value.category
    if (filters.value.budget) {
      const [min, max] = filters.value.budget.split('-')
      params.min_budget = min
      if (max !== '+') params.max_budget = max
    }
    if (filters.value.sort) params.sort = filters.value.sort
    
    const response = await apiClient.get('/cases/pool', { params })
    cases.value = response.data.cases || []
  } catch (error) {
    console.error('Failed to load cases:', error)
    cases.value = []
  } finally {
    isLoading.value = false
  }
}

const resetFilters = () => {
  filters.value = { category: '', budget: '', sort: 'newest' }
  loadCases()
}

const acceptCase = (caseUuid) => {
  selectedCase.value = cases.value.find(c => c.case_uuid === caseUuid)
  showAcceptModal.value = true
}

const confirmAcceptCase = async () => {
  try {
    await apiClient.post(`/professional/cases/${selectedCase.value.case_uuid}/accept`)
    showAcceptModal.value = false
    router.push('/professional')
  } catch (error) {
    alert('接受案件失败: ' + (error.response?.data?.detail || error.message))
  }
}

const viewCaseDetail = (caseUuid) => {
  router.push(`/case/${caseUuid}`)
}

const isUrgent = (caseItem) => {
  const createdDate = new Date(caseItem.created_at)
  const now = new Date()
  const hoursDiff = (now - createdDate) / (1000 * 60 * 60)
  return hoursDiff < 24 && caseItem.budget_cny > 10000
}

const formatDate = (dateString) => {
  const date = new Date(dateString)
  const now = new Date()
  const diffHours = Math.floor((now - date) / (1000 * 60 * 60))
  
  if (diffHours < 1) return '刚刚'
  if (diffHours < 24) return `${diffHours}小时前`
  return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}

const truncate = (text, length) => {
  if (!text) return ''
  return text.length > length ? text.substring(0, length) + '...' : text
}

onMounted(async () => {
  if (authStore.userRole !== 'professional') {
    alert('只有专业人士可以访问案件池')
    router.push('/dashboard')
    return
  }
  const verified = await checkVerification()
  if (verified) await loadCases()
})
</script>

<style scoped>
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