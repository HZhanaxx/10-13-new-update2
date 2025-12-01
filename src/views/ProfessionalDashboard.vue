<template>
  <div class="flex min-h-screen bg-slate-50/50">
    <Sidebar />
    
    <main class="flex-1 p-8 ml-64 overflow-y-auto">
      <div v-if="loading" class="grid gap-6">
        <Skeleton class="h-20 w-full" />
        <div class="grid gap-4 md:grid-cols-4">
          <Skeleton v-for="i in 4" :key="i" class="h-32" />
        </div>
        <Skeleton class="h-[400px] w-full" />
      </div>

      <div v-else class="max-w-6xl mx-auto space-y-8">
        
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div class="space-y-1">
            <h1 class="text-3xl font-bold tracking-tight text-foreground">专业工作台</h1>
            <p class="text-muted-foreground">高效处理您的法律案件与服务</p>
          </div>
          
          <div>
            <Badge v-if="isVerified" class="bg-emerald-500 hover:bg-emerald-600 text-sm px-3 py-1">
              <CheckCircle2 class="w-3.5 h-3.5 mr-1.5" /> 已认证
            </Badge>
            <Badge v-else-if="verificationStatus === 'pending'" variant="secondary" class="bg-amber-100 text-amber-700 text-sm px-3 py-1">
              <Clock class="w-3.5 h-3.5 mr-1.5" /> 审核中
            </Badge>
            <Badge v-else variant="outline" class="text-slate-500">
              未认证
            </Badge>
          </div>
        </div>

        <Card v-if="!isVerified" class="border-l-4 border-l-amber-500 bg-amber-50/40 shadow-sm">
          <CardContent class="flex flex-col sm:flex-row items-start sm:items-center gap-4 py-6">
            <div class="p-3 bg-amber-100 rounded-full text-amber-600 shrink-0">
              <ShieldAlert class="w-6 h-6" />
            </div>
            <div class="space-y-1 flex-1">
              <h3 class="font-semibold text-lg text-amber-900" v-if="verificationStatus === 'pending'">认证申请审核中</h3>
              <h3 class="font-semibold text-lg text-amber-900" v-else>需要完成专业认证</h3>
              
              <p class="text-sm text-amber-800/80" v-if="verificationStatus === 'pending'">
                管理员正在审核您的资质，通常需要 1-3 个工作日。审核通过后即可开始接单。
              </p>
              <p class="text-sm text-amber-800/80" v-else>
                为了保障服务质量，请先完成身份与资质认证。认证后即可访问案件池并接收订单。
              </p>
            </div>
            <Button v-if="verificationStatus !== 'pending'" @click="showVerificationModal = true" class="whitespace-nowrap">
              立即申请认证
            </Button>
          </CardContent>
        </Card>

        <div v-if="isVerified" class="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Card>
            <CardHeader class="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle class="text-sm font-medium">进行中案件</CardTitle>
              <Briefcase class="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div class="text-2xl font-bold">{{ stats.in_progress_cases || 0 }}</div>
              <p class="text-xs text-muted-foreground mt-1">当前承接的任务</p>
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader class="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle class="text-sm font-medium">已完成</CardTitle>
              <CheckCircle2 class="h-4 w-4 text-emerald-500" />
            </CardHeader>
            <CardContent>
              <div class="text-2xl font-bold">{{ stats.completed_cases || 0 }}</div>
              <p class="text-xs text-muted-foreground mt-1">累计完成服务</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader class="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle class="text-sm font-medium">总收入</CardTitle>
              <Banknote class="h-4 w-4 text-emerald-600" />
            </CardHeader>
            <CardContent>
              <div class="text-2xl font-bold">¥{{ formatCurrency(stats.total_earnings) }}</div>
              <p class="text-xs text-muted-foreground mt-1">平台累计收益</p>
            </CardContent>
          </Card>

          <Card class="bg-primary text-primary-foreground border-primary shadow-md cursor-pointer hover:bg-primary/90 transition-colors" @click="$router.push('/case-pool')">
            <CardHeader class="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle class="text-sm font-medium text-primary-foreground/90">案件池</CardTitle>
              <ArrowUpRight class="h-4 w-4 text-primary-foreground" />
            </CardHeader>
            <CardContent>
              <div class="text-2xl font-bold">去接单</div>
              <p class="text-xs text-primary-foreground/80 mt-1">浏览并申请新案件</p>
            </CardContent>
          </Card>
        </div>

        <div v-if="isVerified" class="space-y-4">
          <div class="flex items-center justify-between">
            <h2 class="text-xl font-semibold tracking-tight">最近案件</h2>
            <Button variant="ghost" size="sm" @click="$router.push('/professional/my-cases')">
              查看全部 <ArrowUpRight class="w-4 h-4 ml-1" />
            </Button>
          </div>

          <div v-if="recentCases.length > 0" class="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            <Card 
              v-for="c in recentCases" 
              :key="c.case_uuid" 
              class="cursor-pointer hover:shadow-lg transition-all duration-300 hover:-translate-y-1 group border-muted/60"
              @click="$router.push(`/case/${c.case_uuid}`)"
            >
              <CardHeader class="pb-3">
                <div class="flex justify-between items-start mb-1">
                  <Badge variant="outline" class="font-normal">{{ c.case_category }}</Badge>
                  <div class="flex items-center gap-1.5 text-[10px] uppercase font-bold tracking-wider" :class="getStatusColor(c.case_status)">
                    <div class="w-1.5 h-1.5 rounded-full bg-current"></div>
                    {{ getCaseStatusText(c.case_status) }}
                  </div>
                </div>
                <CardTitle class="text-base line-clamp-1 group-hover:text-primary transition-colors">
                  {{ c.title }}
                </CardTitle>
              </CardHeader>
              <CardContent class="pb-3">
                <p class="text-sm text-muted-foreground line-clamp-2 min-h-[40px]">
                  {{ c.description }}
                </p>
              </CardContent>
              <CardFooter class="pt-3 border-t bg-slate-50/50 rounded-b-xl text-sm font-medium text-emerald-600 flex justify-between items-center">
                <span>预算: ¥{{ c.budget_cny }}</span>
                <span class="text-xs text-muted-foreground font-normal">{{ formatDate(c.created_at) }}</span>
              </CardFooter>
            </Card>
          </div>

          <Card v-else class="flex flex-col items-center justify-center py-16 text-center border-dashed">
            <div class="p-4 bg-muted/50 rounded-full mb-4">
              <Briefcase class="w-8 h-8 text-muted-foreground/50" />
            </div>
            <h3 class="text-lg font-medium">暂无正在进行的案件</h3>
            <p class="text-muted-foreground mt-1 mb-6">您目前没有正在处理的案件，去案件池看看吧。</p>
            <Button @click="$router.push('/case-pool')">前往接单</Button>
          </Card>
        </div>

      </div>
    </main>

    <Dialog :open="showVerificationModal" @close="closeVerificationModal">
      <div class="max-h-[85vh] overflow-y-auto px-1">
        <div class="space-y-6">
          <div class="text-center space-y-2 pt-2">
            <h2 class="text-2xl font-bold">申请专业认证</h2>
            <p class="text-sm text-muted-foreground">请填写真实有效的执业信息</p>
          </div>

          <form @submit.prevent="submitVerification" class="space-y-6">
            <div class="grid grid-cols-2 gap-4">
              <div class="space-y-2">
                <Label>真实姓名 <span class="text-red-500">*</span></Label>
                <Input v-model="verificationForm.full_name" placeholder="请输入姓名" required />
              </div>
              <div class="space-y-2">
                <Label>执业证号 <span class="text-red-500">*</span></Label>
                <Input v-model="verificationForm.license_number" placeholder="请输入证号" required />
              </div>
            </div>

            <div class="space-y-2">
              <Label>所属律所</Label>
              <Input v-model="verificationForm.law_firm_name" placeholder="请输入律所全称" />
            </div>

            <div class="space-y-3">
              <Label>专业领域 (多选) <span class="text-red-500">*</span></Label>
              <div class="grid grid-cols-2 sm:grid-cols-3 gap-2">
                <div 
                  v-for="area in specialtyOptions" 
                  :key="area" 
                  class="flex items-center space-x-2 border p-2.5 rounded-lg cursor-pointer transition-all hover:bg-slate-50"
                  :class="verificationForm.specialty_areas.includes(area) ? 'border-primary bg-primary/5 ring-1 ring-primary' : 'border-input'"
                  @click="toggleSpecialty(area)"
                >
                  <div class="flex items-center justify-center w-4 h-4 rounded border"
                    :class="verificationForm.specialty_areas.includes(area) ? 'bg-primary border-primary' : 'border-input bg-white'"
                  >
                    <Check v-if="verificationForm.specialty_areas.includes(area)" class="w-3 h-3 text-white" />
                  </div>
                  <span class="text-xs font-medium">{{ area }}</span>
                </div>
              </div>
              <p v-if="specialtyError" class="text-xs text-red-500 mt-1">{{ specialtyError }}</p>
            </div>

            <div class="grid grid-cols-2 gap-4">
              <div class="space-y-2">
                <Label>从业年限</Label>
                <Input type="number" v-model.number="verificationForm.years_of_experience" placeholder="0" min="0" />
              </div>
              <div class="space-y-2">
                <Label>时薪 (CNY)</Label>
                <Input type="number" v-model.number="verificationForm.hourly_rate_cny" placeholder="0.00" min="0" step="0.01" />
              </div>
            </div>

            <div class="space-y-2">
              <Label>个人简介</Label>
              <Textarea 
                v-model="verificationForm.bio" 
                placeholder="请简要介绍您的从业经历和擅长领域..." 
                rows="3" 
                class="resize-none"
              />
            </div>

            <div class="space-y-2">
              <Label>证明文件 <span class="text-red-500">*</span></Label>
              <div 
                class="border-2 border-dashed rounded-xl p-6 text-center cursor-pointer hover:bg-slate-50 transition-colors group relative"
                @click="$refs.fileInput.click()"
              >
                <input 
                  type="file" 
                  ref="fileInput" 
                  multiple 
                  accept=".pdf,.jpg,.jpeg,.png" 
                  class="hidden" 
                  @change="handleFileSelect"
                >
                <div class="flex flex-col items-center gap-2">
                  <div class="p-3 bg-primary/10 rounded-full group-hover:bg-primary/20 transition-colors">
                    <UploadCloud class="w-6 h-6 text-primary" />
                  </div>
                  <div class="text-sm">
                    <span class="font-semibold text-primary">点击上传</span> 或拖拽文件至此
                  </div>
                  <p class="text-xs text-muted-foreground">支持 PDF, JPG, PNG (最大 10MB)</p>
                </div>
              </div>

              <div v-if="selectedFiles.length > 0" class="grid gap-2 mt-2">
                <div v-for="(f, i) in selectedFiles" :key="i" class="flex items-center justify-between p-2 bg-slate-50 border rounded-lg text-sm">
                  <div class="flex items-center gap-2 overflow-hidden">
                    <FileText class="w-4 h-4 text-muted-foreground shrink-0" />
                    <span class="truncate">{{ f.name }}</span>
                  </div>
                  <Button variant="ghost" size="icon" class="h-6 w-6 text-muted-foreground hover:text-red-500" @click.stop="removeFile(i)">
                    <X class="w-3 h-3" />
                  </Button>
                </div>
              </div>
              <p v-if="fileError" class="text-xs text-red-500 mt-1">{{ fileError }}</p>
            </div>

            <div class="flex justify-end gap-3 pt-4 border-t">
              <Button variant="ghost" type="button" @click="closeVerificationModal">取消</Button>
              <Button type="submit" :loading="submitting">提交申请</Button>
            </div>
          </form>
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
  Card, CardHeader, CardTitle, CardContent, CardFooter,
  Button, Badge, Skeleton, Dialog, Input, Label, Textarea 
} from '@/components/ui'
import { 
  ShieldAlert, CheckCircle2, Clock, Briefcase, 
  ArrowUpRight, UploadCloud, Check, FileText, X, Banknote
} from 'lucide-vue-next'

const router = useRouter()
const authStore = useAuthStore()

// State
const loading = ref(true)
const isVerified = ref(false)
const verificationStatus = ref(null)
const stats = ref({})
const recentCases = ref([])
const showVerificationModal = ref(false)
const submitting = ref(false)
const specialtyError = ref('')
const fileError = ref('')
const selectedFiles = ref([])
const fileInput = ref(null)

const verificationForm = ref({
  full_name: '', 
  license_number: '', 
  law_firm_name: '', 
  specialty_areas: [],
  years_of_experience: null,
  education_background: '',
  bio: '',
  consultation_fee_cny: null,
  hourly_rate_cny: null,
  city_name: '',
  province_name: ''
})

const specialtyOptions = ['劳动纠纷', '合同纠纷', '债务纠纷', '交通事故', '医疗纠纷', '房产纠纷', '知识产权', '婚姻家庭', '刑事辩护']

// Methods
const toggleSpecialty = (area) => {
  const idx = verificationForm.value.specialty_areas.indexOf(area)
  if (idx === -1) verificationForm.value.specialty_areas.push(area)
  else verificationForm.value.specialty_areas.splice(idx, 1)
}

const handleFileSelect = (event) => {
  const files = Array.from(event.target.files)
  if (selectedFiles.value.length + files.length > 5) {
    fileError.value = '最多只能上传5个文件'
    return
  }
  selectedFiles.value = [...selectedFiles.value, ...files]
  fileError.value = ''
}

const removeFile = (index) => {
  selectedFiles.value.splice(index, 1)
}

const formatCurrency = (val) => Number(val).toLocaleString('zh-CN', { minimumFractionDigits: 2 })

const formatDate = (dateStr) => {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleDateString('zh-CN')
}

const getStatusColor = (status) => {
  const map = { 
    in_progress: 'text-blue-600 bg-blue-50', 
    completed: 'text-emerald-600 bg-emerald-50',
    pending: 'text-amber-600 bg-amber-50' 
  }
  return map[status] || 'text-slate-600 bg-slate-50'
}

const getCaseStatusText = (s) => {
  const map = {
    pending: '待处理',
    in_progress: '进行中',
    completed: '已完成'
  }
  return map[s] || s
}

// API Calls
const checkVerification = async () => {
  try {
    const res = await apiClient.get('/professional/verification-status')
    isVerified.value = res.data.is_verified
    verificationStatus.value = res.data.status
    
    if (!isVerified.value) {
      try {
        const reqRes = await apiClient.get('/verification/my-request')
        if (reqRes.data.status === 'pending') verificationStatus.value = 'pending'
      } catch (e) { /* ignore */ }
    }
  } catch (e) {
    console.error('Check verification failed', e)
  }
}

const loadStats = async () => {
  try {
    const res = await apiClient.get('/professional/stats')
    stats.value = res.data
  } catch (e) { console.error(e) }
}

const loadRecentCases = async () => {
  try {
    const res = await apiClient.get('/professional/my-cases')
    recentCases.value = (res.data.cases || []).slice(0, 6)
  } catch (e) { console.error(e) }
}

const submitVerification = async () => {
  if (verificationForm.value.specialty_areas.length === 0) {
    specialtyError.value = '请至少选择一个专业领域'
    return
  }
  if (selectedFiles.value.length === 0) {
    fileError.value = '请上传证明文件'
    return
  }

  submitting.value = true
  try {
    const formData = new FormData()
    // Append form fields
    for (const [key, value] of Object.entries(verificationForm.value)) {
      if (key === 'specialty_areas') {
        value.forEach(area => formData.append('specialty_areas', area))
      } else if (value !== null && value !== '') {
        formData.append(key, value)
      }
    }
    // Append files
    selectedFiles.value.forEach(file => formData.append('files', file))

    await apiClient.post('/verification/request', formData)
    
    alert('申请已提交')
    closeVerificationModal()
    await checkVerification()
  } catch (error) {
    alert(error.response?.data?.detail || '提交失败')
  } finally {
    submitting.value = false
  }
}

const closeVerificationModal = () => {
  showVerificationModal.value = false
  selectedFiles.value = []
  verificationForm.value.specialty_areas = []
}

onMounted(async () => {
  if (authStore.userRole !== 'professional') {
    router.push('/dashboard')
    return
  }
  await checkVerification()
  if (isVerified.value) {
    await Promise.all([loadStats(), loadRecentCases()])
  }
  loading.value = false
})
</script>