<template>
  <div class="flex min-h-screen bg-slate-50/50">
    <Sidebar />
    
    <main class="flex-1 p-8 ml-64 overflow-y-auto">
      <div class="max-w-5xl mx-auto space-y-6">
        
        <div class="flex items-center gap-4">
          <Button variant="outline" size="icon" class="h-9 w-9 rounded-full bg-white shadow-sm" @click="$router.go(-1)">
            <ArrowLeft class="h-4 w-4" />
          </Button>
          <div class="space-y-1">
            <h1 class="text-2xl font-bold tracking-tight text-foreground flex items-center gap-3">
              案件详情
              <Badge v-if="caseData" :class="getStatusBadgeClass(caseData.case_status)">
                {{ getStatusText(caseData.case_status) }}
              </Badge>
            </h1>
            <p v-if="caseData" class="text-sm text-muted-foreground flex items-center gap-2">
              <span class="font-mono">#{{ caseData.case_uuid.slice(0, 8) }}</span>
              <span>•</span>
              <span>{{ formatDate(caseData.created_at) }}</span>
            </p>
          </div>
        </div>

        <div v-if="isLoading" class="grid gap-6 md:grid-cols-3">
          <div class="md:col-span-2 space-y-6">
            <Skeleton class="h-[200px] w-full rounded-xl" />
            <Skeleton class="h-[300px] w-full rounded-xl" />
          </div>
          <div class="space-y-6">
            <Skeleton class="h-[150px] w-full rounded-xl" />
            <Skeleton class="h-[100px] w-full rounded-xl" />
          </div>
        </div>

        <div v-else-if="caseData" class="grid gap-6 md:grid-cols-3 items-start">
          
          <div class="md:col-span-2 space-y-6">
            
            <Card class="shadow-sm border-0">
              <CardHeader>
                <div class="flex justify-between items-start">
                  <div class="space-y-1">
                    <CardTitle class="text-xl">{{ caseData.title }}</CardTitle>
                    <div class="flex items-center gap-2 text-sm text-muted-foreground">
                      <Folder class="h-4 w-4" /> {{ caseData.case_category }}
                      <span v-if="caseData.location" class="flex items-center gap-1 ml-2">
                        <MapPin class="h-3.5 w-3.5" /> {{ caseData.location }}
                      </span>
                    </div>
                  </div>
                  <div class="text-xl font-bold text-emerald-600 bg-emerald-50 px-3 py-1 rounded-lg">
                    ¥{{ caseData.budget_cny ? Number(caseData.budget_cny).toLocaleString() : '面议' }}
                  </div>
                </div>
              </CardHeader>
              <Separator />
              <CardContent class="pt-6 space-y-8">
                <div class="space-y-3">
                  <h3 class="font-medium text-foreground flex items-center gap-2 text-base">
                    <div class="p-1.5 bg-blue-50 rounded-md"><FileText class="h-4 w-4 text-blue-600" /></div>
                    案件描述
                  </h3>
                  <p class="text-sm text-muted-foreground leading-relaxed whitespace-pre-wrap pl-10">
                    {{ caseData.description }}
                  </p>
                </div>
                
                <div v-if="caseData.requirements" class="space-y-3">
                  <h3 class="font-medium text-foreground flex items-center gap-2 text-base">
                    <div class="p-1.5 bg-amber-50 rounded-md"><ClipboardList class="h-4 w-4 text-amber-600" /></div>
                    具体要求
                  </h3>
                  <p class="text-sm text-muted-foreground leading-relaxed whitespace-pre-wrap pl-10">
                    {{ caseData.requirements }}
                  </p>
                </div>
              </CardContent>
            </Card>

            <Card class="shadow-sm border-0">
              <CardHeader>
                <CardTitle class="text-lg flex items-center gap-2">
                  <Clock class="h-5 w-5 text-muted-foreground" /> 案件进度
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div class="relative pl-6 border-l-2 border-slate-100 space-y-8 ml-2 py-2">
                  <div v-for="(item, index) in timeline" :key="index" class="relative">
                    <div class="absolute -left-[31px] top-1 h-4 w-4 rounded-full border-2 border-white ring-4 ring-slate-50 transition-colors duration-300" 
                         :class="index === timeline.length - 1 ? 'bg-primary' : 'bg-slate-300'"></div>
                    <div class="space-y-1">
                      <p class="text-xs text-muted-foreground font-medium">{{ formatDateTime(item.timestamp) }}</p>
                      <p class="text-sm font-semibold text-foreground">{{ item.title }}</p>
                      <p v-if="item.description" class="text-xs text-muted-foreground">{{ item.description }}</p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          <div class="space-y-6">
            
            <Card class="border-l-4 border-l-primary shadow-md border-y-0 border-r-0">
              <CardHeader class="pb-3">
                <CardTitle class="text-base">操作</CardTitle>
              </CardHeader>
              <CardContent class="space-y-3">
                <template v-if="authStore.userRole === 'user'">
                  <Button 
                    v-if="caseData.case_status === 'pending'"
                    variant="destructive" 
                    class="w-full" 
                    @click="cancelCase"
                  >
                    取消案件
                  </Button>
                  <Button 
                    v-if="caseData.case_status === 'completed'"
                    class="w-full" 
                    @click="showRatingModal = true"
                  >
                    评价服务
                  </Button>
                  <div v-if="!['pending', 'completed'].includes(caseData.case_status)" class="text-sm text-center text-muted-foreground py-2 bg-slate-50 rounded">
                    当前状态无法执行操作
                  </div>
                </template>

                <template v-if="authStore.userRole === 'professional'">
                  <Button 
                    v-if="caseData.case_status === 'pending'"
                    class="w-full" 
                    @click="acceptCase"
                  >
                    接受案件
                  </Button>
                  <Button 
                    v-if="caseData.case_status === 'in_progress'"
                    class="w-full bg-emerald-600 hover:bg-emerald-700 text-white" 
                    @click="completeCase"
                  >
                    标记完成
                  </Button>
                  <div v-if="['completed', 'cancelled'].includes(caseData.case_status)" class="text-sm text-center text-muted-foreground py-2 bg-slate-50 rounded">
                    案件已结束
                  </div>
                </template>
              </CardContent>
            </Card>

            <Card class="shadow-sm border-0">
              <CardHeader class="pb-3">
                <CardTitle class="text-base">相关人员</CardTitle>
              </CardHeader>
              <CardContent class="space-y-6">
                <div v-if="authStore.userRole === 'professional' && caseData.client_info">
                  <div class="flex items-center gap-3 mb-4">
                    <Avatar class="h-10 w-10 border">
                      <div class="bg-slate-100 text-slate-600 h-full w-full flex items-center justify-center font-bold">
                        {{ caseData.client_info.name?.[0] || '客' }}
                      </div>
                    </Avatar>
                    <div>
                      <p class="text-sm font-medium">客户信息</p>
                      <p class="text-xs text-muted-foreground">{{ caseData.client_info.name }}</p>
                    </div>
                  </div>
                  <div class="space-y-2 text-sm bg-slate-50 p-3 rounded-lg border">
                    <div class="flex justify-between items-center">
                      <span class="text-muted-foreground text-xs">电话</span>
                      <span class="font-mono">{{ caseData.client_info.phone }}</span>
                    </div>
                    <div v-if="caseData.client_info.email" class="flex justify-between items-center">
                      <span class="text-muted-foreground text-xs">邮箱</span>
                      <span class="truncate max-w-[140px]" :title="caseData.client_info.email">{{ caseData.client_info.email }}</span>
                    </div>
                  </div>
                </div>

                <div v-if="authStore.userRole === 'user'">
                  <div v-if="caseData.professional_info">
                    <div class="flex items-center gap-3 mb-4">
                      <Avatar class="h-10 w-10 border">
                        <div class="bg-primary/10 text-primary h-full w-full flex items-center justify-center font-bold">
                          {{ caseData.professional_info.name?.[0] || '律' }}
                        </div>
                      </Avatar>
                      <div>
                        <p class="text-sm font-medium">承接律师</p>
                        <p class="text-xs text-muted-foreground">{{ caseData.professional_info.name }}</p>
                      </div>
                    </div>
                    <div class="space-y-2 text-sm bg-slate-50 p-3 rounded-lg border">
                      <div class="flex justify-between">
                        <span class="text-muted-foreground text-xs">专业领域</span>
                        <span>{{ caseData.professional_info.specialization || '未填写' }}</span>
                      </div>
                      <div class="flex justify-between">
                        <span class="text-muted-foreground text-xs">所属律所</span>
                        <span class="truncate max-w-[140px]">{{ caseData.professional_info.organization || '未填写' }}</span>
                      </div>
                      <div class="flex justify-between">
                        <span class="text-muted-foreground text-xs">从业年限</span>
                        <span>{{ caseData.professional_info.years_experience || 0 }} 年</span>
                      </div>
                    </div>
                  </div>
                  <div v-else class="text-center py-8 bg-slate-50 rounded-lg border border-dashed">
                    <UserX class="h-8 w-8 mx-auto text-muted-foreground/30 mb-2" />
                    <p class="text-xs text-muted-foreground">暂无律师接单</p>
                  </div>
                </div>
              </CardContent>
            </Card>

          </div>
        </div>

        <div v-else class="flex flex-col items-center justify-center py-20 text-center">
          <div class="bg-red-50 p-4 rounded-full mb-4">
            <AlertCircle class="h-8 w-8 text-red-500" />
          </div>
          <h2 class="text-xl font-semibold mb-2">无法加载案件详情</h2>
          <p class="text-muted-foreground mb-6">该案件可能不存在或您没有权限查看</p>
          <Button @click="$router.push('/dashboard')">返回首页</Button>
        </div>
      </div>
    </main>

    <Dialog :open="showRatingModal" @close="showRatingModal = false">
      <div class="space-y-6">
        <div class="text-center space-y-2">
          <h2 class="text-xl font-bold">服务评价</h2>
          <p class="text-sm text-muted-foreground">请对律师的服务进行评价，这将帮助我们提升服务质量</p>
        </div>
        
        <div class="flex justify-center gap-3 py-6 bg-slate-50 rounded-xl">
          <button 
            v-for="star in 5" 
            :key="star"
            class="text-4xl focus:outline-none transition-all duration-200 hover:scale-110 active:scale-95"
            :class="star <= rating ? 'text-amber-400 drop-shadow-sm' : 'text-slate-200'"
            @click="rating = star"
          >
            ★
          </button>
        </div>

        <div class="space-y-2">
          <Label>评价内容</Label>
          <Textarea 
            v-model="ratingComment" 
            placeholder="请分享您的服务体验..." 
            rows="4" 
            class="resize-none"
          />
        </div>

        <div class="flex justify-end gap-3 pt-2">
          <Button variant="ghost" @click="showRatingModal = false">取消</Button>
          <Button @click="submitRating" :disabled="rating === 0">提交评价</Button>
        </div>
      </div>
    </Dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import Sidebar from '@/components/Sidebar.vue'
import apiClient from '@/utils/api'
import { 
  Card, CardHeader, CardTitle, CardContent, 
  Button, Badge, Skeleton, Dialog, Separator, Avatar, Textarea, Label
} from '@/components/ui'
import { 
  ArrowLeft, Clock, FileText, MapPin, Folder, 
  ClipboardList, UserX, AlertCircle 
} from 'lucide-vue-next'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

// State
const isLoading = ref(false)
const caseData = ref(null)
const timeline = ref([])
const showRatingModal = ref(false)
const rating = ref(0)
const ratingComment = ref('')

const loadCaseDetail = async () => {
  isLoading.value = true
  try {
    const caseId = route.params.id
    const response = await apiClient.get(`/cases/${caseId}`)
    caseData.value = response.data
    timeline.value = buildTimeline(caseData.value)
  } catch (error) {
    console.error('Failed to load case detail:', error)
    caseData.value = null
  } finally {
    isLoading.value = false
  }
}

const buildTimeline = (caseItem) => {
  const events = []
  if (caseItem.created_at) {
    events.push({
      timestamp: caseItem.created_at,
      title: '案件创建',
      description: '案件已发布到案件池'
    })
  }
  
  if (caseItem.accepted_at) {
    events.push({
      timestamp: caseItem.accepted_at,
      title: '律师接单',
      description: `${caseItem.professional_info?.name || '律师'} 已接受此案件`
    })
  }
  
  if (caseItem.completed_at) {
    events.push({
      timestamp: caseItem.completed_at,
      title: '案件完成',
      description: '案件已标记为完成'
    })
  }
  
  // Sort descending for timeline (newest first) usually, but ascending looks better for "history"
  return events.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp))
}

const acceptCase = async () => {
  if (!confirm('确认接受此案件?')) return
  try {
    await apiClient.post(`/professional/cases/${route.params.id}/accept`)
    await loadCaseDetail()
  } catch (error) {
    alert('接受失败: ' + (error.response?.data?.detail || error.message))
  }
}

const completeCase = async () => {
  if (!confirm('确认标记此案件为已完成?')) return
  try {
    await apiClient.post(`/professional/cases/${route.params.id}/complete`)
    await loadCaseDetail()
  } catch (error) {
    alert('操作失败: ' + (error.response?.data?.detail || error.message))
  }
}

const cancelCase = async () => {
  if (!confirm('确认取消此案件? 此操作不可撤销。')) return
  try {
    await apiClient.post(`/cases/${route.params.id}/cancel`)
    router.push('/dashboard')
  } catch (error) {
    alert('取消失败: ' + (error.response?.data?.detail || error.message))
  }
}

const submitRating = async () => {
  try {
    await apiClient.post(`/cases/${route.params.id}/rate`, {
      rating: rating.value,
      comment: ratingComment.value
    })
    showRatingModal.value = false
    await loadCaseDetail()
  } catch (error) {
    alert('评价失败: ' + (error.response?.data?.detail || error.message))
  }
}

const getStatusBadgeClass = (status) => {
  const map = {
    pending: 'bg-amber-100 text-amber-700 hover:bg-amber-100',
    in_progress: 'bg-blue-100 text-blue-700 hover:bg-blue-100',
    completed: 'bg-emerald-100 text-emerald-700 hover:bg-emerald-100',
    cancelled: 'bg-slate-100 text-slate-600 hover:bg-slate-100'
  }
  return map[status] || 'bg-slate-100 text-slate-600'
}

const getStatusText = (status) => {
  const map = {
    pending: '待接单',
    in_progress: '进行中',
    completed: '已完成',
    cancelled: '已取消'
  }
  return map[status] || status
}

const formatDate = (dateString) => {
  if (!dateString) return ''
  return new Date(dateString).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}

const formatDateTime = (dateString) => {
  if (!dateString) return ''
  return new Date(dateString).toLocaleString('zh-CN', { 
    month: 'short', 
    day: 'numeric',
    hour: '2-digit', 
    minute: '2-digit' 
  })
}

onMounted(loadCaseDetail)
</script>