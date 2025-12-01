<template>
  <div class="flex min-h-screen bg-slate-50/50">
    <Sidebar />
    
    <main class="flex-1 p-8 ml-64 overflow-y-auto">
      <div class="max-w-6xl mx-auto space-y-8">
        
        <div class="space-y-1">
          <h1 class="text-3xl font-bold tracking-tight text-foreground">案件监控</h1>
          <p class="text-muted-foreground">实时查看全平台案件状态与处理进度</p>
        </div>

        <div class="grid gap-4 md:grid-cols-4">
          <Card class="hover:shadow-md transition-shadow">
            <CardHeader class="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle class="text-sm font-medium">总案件数</CardTitle>
              <FileText class="h-4 w-4 text-slate-500" />
            </CardHeader>
            <CardContent>
              <div class="text-2xl font-bold">{{ stats.total_cases }}</div>
            </CardContent>
          </Card>
          <Card class="hover:shadow-md transition-shadow bg-amber-50/30 border-amber-200">
            <CardHeader class="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle class="text-sm font-medium text-amber-700">待处理</CardTitle>
              <Clock class="h-4 w-4 text-amber-600" />
            </CardHeader>
            <CardContent>
              <div class="text-2xl font-bold text-amber-700">{{ stats.pending }}</div>
            </CardContent>
          </Card>
          <Card class="hover:shadow-md transition-shadow bg-blue-50/30 border-blue-200">
            <CardHeader class="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle class="text-sm font-medium text-blue-700">进行中</CardTitle>
              <Activity class="h-4 w-4 text-blue-600" />
            </CardHeader>
            <CardContent>
              <div class="text-2xl font-bold text-blue-700">{{ stats.in_progress }}</div>
            </CardContent>
          </Card>
          <Card class="hover:shadow-md transition-shadow bg-emerald-50/30 border-emerald-200">
            <CardHeader class="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle class="text-sm font-medium text-emerald-700">已完成</CardTitle>
              <CheckCircle2 class="h-4 w-4 text-emerald-600" />
            </CardHeader>
            <CardContent>
              <div class="text-2xl font-bold text-emerald-700">{{ stats.completed }}</div>
            </CardContent>
          </Card>
        </div>

        <Card class="border shadow-sm">
          <CardHeader class="flex flex-row items-center justify-between">
            <div>
              <CardTitle>最近动态</CardTitle>
              <CardDescription>最新的案件创建与状态更新</CardDescription>
            </div>
            <Button variant="outline" size="sm" @click="loadData" :disabled="loading">
              <RefreshCw class="h-4 w-4 mr-2" :class="{ 'animate-spin': loading }" /> 刷新
            </Button>
          </CardHeader>
          <CardContent>
            <div class="space-y-6">
              <div v-if="loading" class="space-y-4">
                <Skeleton v-for="i in 5" :key="i" class="h-16 w-full rounded-lg" />
              </div>
              
              <div v-else-if="recentCases.length === 0" class="text-center py-10 text-muted-foreground">
                暂无数据
              </div>

              <div v-else class="space-y-4">
                <div 
                  v-for="log in recentCases" 
                  :key="log.case_uuid" 
                  class="flex items-center justify-between p-4 rounded-lg border bg-card hover:bg-slate-50 transition-colors"
                >
                  <div class="flex items-start gap-4">
                    <div :class="['mt-1.5 h-2.5 w-2.5 rounded-full shrink-0', getStatusDotColor(log.case_status)]"></div>
                    <div class="space-y-1">
                      <p class="font-medium leading-none">{{ log.title }}</p>
                      <div class="flex items-center gap-2 text-sm text-muted-foreground">
                        <span>{{ formatDate(log.updated_at || log.created_at) }}</span>
                        <span>•</span>
                        <span v-if="log.professional_name" class="flex items-center gap-1 text-blue-600 bg-blue-50 px-1.5 rounded text-xs">
                          <User class="h-3 w-3" /> {{ log.professional_name }}
                        </span>
                        <span v-else class="text-amber-600 bg-amber-50 px-1.5 rounded text-xs">
                          待接单
                        </span>
                      </div>
                    </div>
                  </div>
                  <Badge variant="secondary" :class="getStatusBadgeClass(log.case_status)">
                    {{ getStatusText(log.case_status) }}
                  </Badge>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import Sidebar from '@/components/Sidebar.vue'
import apiClient from '@/utils/api'
import { 
  Card, CardHeader, CardTitle, CardContent, CardDescription,
  Button, Badge, Skeleton
} from '@/components/ui'
import { 
  FileText, Clock, Activity, CheckCircle2, RefreshCw, User 
} from 'lucide-vue-next'

const stats = ref({ total_cases: 0, pending: 0, in_progress: 0, completed: 0 })
const recentCases = ref([])
const loading = ref(false)

const loadData = async () => {
  loading.value = true
  try {
    // 1. Load Stats
    const statRes = await apiClient.get('/admin/stats')
    // Adapt response structure to our needs if necessary
    const rawStats = statRes.data
    stats.value = {
        total_cases: rawStats.totalCases || 0,
        pending: 0, // Need backend support for precise breakdown, using placeholders or derived values
        in_progress: 0,
        completed: 0
    }

    // 2. Load Cases (Assuming an endpoint exists or reusing /admin/all-cases)
    // Note: Adjust endpoint based on your actual API
    const caseRes = await apiClient.get('/admin/all-cases', { params: { limit: 10 } })
    recentCases.value = caseRes.data || []
    
    // Calculate stats from loaded cases if stats endpoint doesn't provide breakdown
    if (recentCases.value.length > 0) {
       // This is just a client-side approximation if server doesn't return full counts
       // Ideally server returns these counts
    }
  } catch (e) {
    console.error('Load monitoring data failed', e)
  } finally {
    loading.value = false
  }
}

const getStatusText = (status) => {
  const map = { pending: '待接单', in_progress: '处理中', completed: '已结案', cancelled: '已取消' }
  return map[status] || status
}

const getStatusDotColor = (status) => {
  const map = {
    pending: 'bg-amber-500',
    in_progress: 'bg-blue-500',
    completed: 'bg-emerald-500',
    cancelled: 'bg-slate-400'
  }
  return map[status] || 'bg-slate-400'
}

const getStatusBadgeClass = (status) => {
  const map = {
    pending: 'bg-amber-50 text-amber-700 hover:bg-amber-50',
    in_progress: 'bg-blue-50 text-blue-700 hover:bg-blue-50',
    completed: 'bg-emerald-50 text-emerald-700 hover:bg-emerald-50',
    cancelled: 'bg-slate-100 text-slate-600 hover:bg-slate-100'
  }
  return map[status] || ''
}

const formatDate = (d) => new Date(d).toLocaleString('zh-CN')

onMounted(loadData)
</script>