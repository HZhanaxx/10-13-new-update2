<template>
  <div class="flex min-h-screen bg-slate-50/50">
    <Sidebar />
    
    <main class="flex-1 p-8 ml-64 overflow-y-auto">
      <div class="max-w-6xl mx-auto space-y-8">
        
        <div class="flex items-center justify-between">
          <div class="space-y-1">
            <h1 class="text-3xl font-bold tracking-tight text-foreground">我的承接案件</h1>
            <p class="text-muted-foreground">管理您负责的法律咨询与案件进度</p>
          </div>
          <Button @click="$router.push('/case-pool')">
            <Plus class="w-4 h-4 mr-2" /> 接新单
          </Button>
        </div>

        <div v-if="loading" class="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          <Skeleton v-for="i in 3" :key="i" class="h-[250px] rounded-xl" />
        </div>

        <div v-else-if="cases.length > 0" class="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          <Card 
            v-for="c in cases" 
            :key="c.case_uuid" 
            class="group cursor-pointer hover:shadow-lg transition-all duration-300 hover:-translate-y-1 flex flex-col h-full border-muted/60"
            @click="goToDetail(c.case_uuid)"
          >
            <CardHeader class="pb-3">
              <div class="flex justify-between items-start mb-2">
                <span class="font-mono text-xs text-muted-foreground">#{{ c.case_uuid.slice(0, 8) }}</span>
                <Badge :class="getStatusBadgeClass(c.case_status)">
                  {{ getStatusText(c.case_status) }}
                </Badge>
              </div>
              <CardTitle class="text-lg line-clamp-1 group-hover:text-primary transition-colors">
                {{ c.title }}
              </CardTitle>
            </CardHeader>
            
            <CardContent class="flex-1 pb-4 space-y-4">
              <div class="grid grid-cols-2 gap-2 text-sm">
                <div class="flex items-center gap-2 text-muted-foreground bg-slate-50 p-2 rounded">
                  <Calendar class="w-4 h-4" /> {{ formatDate(c.created_at) }}
                </div>
                <div class="flex items-center gap-2 font-medium text-emerald-600 bg-emerald-50/50 p-2 rounded">
                  <Banknote class="w-4 h-4" /> ¥{{ c.budget_cny }}
                </div>
              </div>

              <div class="space-y-1.5">
                <div class="flex justify-between text-xs text-muted-foreground">
                  <span>进度</span>
                  <span>{{ getProgress(c.case_status) }}%</span>
                </div>
                <Progress :value="getProgress(c.case_status)" class="h-2" />
              </div>
            </CardContent>
            
            <CardFooter class="pt-0 pb-4 border-t bg-slate-50/30 pt-3 mt-auto">
              <Button variant="ghost" class="w-full text-primary hover:text-primary/80 hover:bg-primary/5">
                查看详情 <ArrowRight class="w-4 h-4 ml-2" />
              </Button>
            </CardFooter>
          </Card>
        </div>

        <div v-else class="flex flex-col items-center justify-center py-20 text-center border-2 border-dashed rounded-xl bg-slate-50/50">
          <div class="p-4 bg-white rounded-full shadow-sm mb-4">
            <Briefcase class="w-10 h-10 text-muted-foreground/50" />
          </div>
          <h3 class="text-lg font-medium">暂无承接案件</h3>
          <p class="text-muted-foreground mb-6 max-w-sm">您目前没有正在进行的案件。前往案件池寻找适合您的机会吧。</p>
          <Button @click="$router.push('/case-pool')">前往案件池</Button>
        </div>

      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import Sidebar from '@/components/Sidebar.vue'
import apiClient from '@/utils/api'
import { 
  Card, CardHeader, CardTitle, CardContent, CardFooter,
  Button, Badge, Skeleton, Progress 
} from '@/components/ui'
import { 
  Plus, Calendar, Banknote, ArrowRight, Briefcase 
} from 'lucide-vue-next'

const router = useRouter()
const cases = ref([])
const loading = ref(true)

const loadMyCases = async () => {
  try {
    const res = await apiClient.get('/professional/my-cases')
    cases.value = res.data.cases || []
  } catch (e) {
    console.error('Failed to load cases', e)
  } finally {
    loading.value = false
  }
}

const goToDetail = (id) => router.push(`/case/${id}`)

const getStatusText = (s) => {
  const map = { in_progress: '进行中', completed: '已完成', pending: '待处理' }
  return map[s] || s
}

const getStatusBadgeClass = (s) => {
  const map = {
    in_progress: 'bg-blue-100 text-blue-700 hover:bg-blue-100',
    completed: 'bg-emerald-100 text-emerald-700 hover:bg-emerald-100',
    pending: 'bg-amber-100 text-amber-700 hover:bg-amber-100'
  }
  return map[s] || ''
}

const getProgress = (s) => {
  if (s === 'completed') return 100
  if (s === 'in_progress') return 50
  return 0
}

const formatDate = (d) => new Date(d).toLocaleDateString('zh-CN')

onMounted(loadMyCases)
</script>