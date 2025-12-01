<template>
  <div class="flex min-h-screen bg-slate-50/50">
    <Sidebar />
    
    <main class="flex-1 p-8 ml-64 overflow-y-auto">
      <div class="max-w-4xl mx-auto space-y-8">
        
        <div class="space-y-1">
          <h1 class="text-3xl font-bold tracking-tight text-foreground">专业认证</h1>
          <p class="text-muted-foreground">提交执业资质，解锁完整平台功能</p>
        </div>

        <div v-if="loading" class="space-y-6">
          <Skeleton class="h-32 w-full rounded-xl" />
          <Skeleton class="h-[600px] w-full rounded-xl" />
        </div>

        <div v-else-if="verificationStatus" class="animate-in fade-in slide-in-from-bottom-4 duration-500">
          <Card class="border-t-4 shadow-md" :class="getStatusBorderClass(verificationStatus.status)">
            <CardHeader class="pb-4">
              <div class="flex items-center gap-4">
                <div :class="['p-3 rounded-full', getStatusIconBg(verificationStatus.status)]">
                  <component :is="getStatusIcon(verificationStatus.status)" class="w-8 h-8" :class="getStatusIconColor(verificationStatus.status)" />
                </div>
                <div class="space-y-1">
                  <CardTitle class="text-xl">{{ getStatusTitle(verificationStatus.status) }}</CardTitle>
                  <CardDescription class="text-base">
                    {{ getStatusDescription(verificationStatus.status) }}
                  </CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent class="bg-slate-50/50 border-t pt-6">
              <div class="grid md:grid-cols-2 gap-6 text-sm">
                <div class="space-y-4">
                  <div>
                    <span class="text-muted-foreground block mb-1">申请时间</span>
                    <span class="font-medium">{{ formatDate(verificationStatus.created_at) }}</span>
                  </div>
                  <div>
                    <span class="text-muted-foreground block mb-1">执业证号</span>
                    <span class="font-mono bg-white px-2 py-1 rounded border">{{ verificationStatus.license_number }}</span>
                  </div>
                </div>
                <div class="space-y-4">
                  <div>
                    <span class="text-muted-foreground block mb-1">所属律所</span>
                    <span class="font-medium">{{ verificationStatus.law_firm_name || '未填写' }}</span>
                  </div>
                  <div v-if="verificationStatus.reviewed_at">
                    <span class="text-muted-foreground block mb-1">审核时间</span>
                    <span class="font-medium">{{ formatDate(verificationStatus.reviewed_at) }}</span>
                  </div>
                </div>
              </div>

              <Alert v-if="verificationStatus.status === 'rejected'" variant="destructive" class="mt-6 bg-red-50 border-red-200 text-red-900">
                <AlertCircle class="h-4 w-4" />
                <div class="ml-2">
                  <h3 class="font-medium mb-1">审核未通过原因</h3>
                  <p>{{ verificationStatus.admin_notes || '未提供具体原因，请检查资料后重试。' }}</p>
                </div>
              </Alert>
            </CardContent>
            <CardFooter class="justify-end pt-6 border-t bg-white" v-if="verificationStatus.status === 'approved'">
              <Button @click="$router.push('/case-pool')" class="bg-emerald-600 hover:bg-emerald-700">
                前往案件池接单 <ArrowRight class="ml-2 w-4 h-4" />
              </Button>
            </CardFooter>
            <CardFooter class="justify-end pt-6 border-t bg-white" v-if="verificationStatus.status === 'rejected'">
              <Button @click="retryVerification">重新申请认证</Button>
            </CardFooter>
          </Card>
        </div>

        <div v-else class="animate-in fade-in slide-in-from-bottom-4 duration-500">
          
          <Alert class="mb-6 bg-blue-50 text-blue-900 border-blue-200">
            <Info class="h-4 w-4 text-blue-600" />
            <div class="ml-2">
              <h3 class="font-medium">为什么需要认证？</h3>
              <ul class="mt-1 list-disc list-inside text-sm opacity-90 space-y-0.5">
                <li>提高客户信任度，获得更多订单</li>
                <li>访问完整案件池，接收更多案件推送</li>
                <li>展示专业资质，提升个人品牌曝光</li>
              </ul>
            </div>
          </Alert>

          <form @submit.prevent="submitVerification">
            <Card class="border-0 shadow-lg">
              <CardHeader>
                <CardTitle>填写认证信息</CardTitle>
                <CardDescription>请确保填写的信息真实有效，我们将严格保护您的隐私。</CardDescription>
              </CardHeader>
              
              <CardContent class="space-y-8">
                <div class="space-y-4">
                  <h3 class="text-sm font-medium text-muted-foreground uppercase tracking-wider flex items-center gap-2">
                    <User class="w-4 h-4" /> 基本信息
                  </h3>
                  <div class="grid md:grid-cols-2 gap-6">
                    <div class="space-y-2">
                      <Label for="full_name">真实姓名 <span class="text-red-500">*</span></Label>
                      <Input id="full_name" v-model="form.full_name" placeholder="请输入姓名" required />
                    </div>
                    <div class="space-y-2">
                      <Label for="license">执业证号 <span class="text-red-500">*</span></Label>
                      <Input id="license" v-model="form.license_number" placeholder="请输入执业证号" required />
                    </div>
                    <div class="space-y-2 md:col-span-2">
                      <Label for="firm">所属律所</Label>
                      <Input id="firm" v-model="form.law_firm_name" placeholder="请输入律所全称" />
                    </div>
                  </div>
                </div>

                <Separator />

                <div class="space-y-4">
                  <h3 class="text-sm font-medium text-muted-foreground uppercase tracking-wider flex items-center gap-2">
                    <Briefcase class="w-4 h-4" /> 专业能力
                  </h3>
                  
                  <div class="space-y-2">
                    <Label>专业领域 (多选)</Label>
                    <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
                      <div 
                        v-for="area in specialtyOptions" 
                        :key="area" 
                        class="flex items-center space-x-2 border p-3 rounded-lg cursor-pointer transition-all hover:bg-slate-50"
                        :class="form.specialty_areas.includes(area) ? 'border-primary bg-primary/5 ring-1 ring-primary' : 'border-input'"
                        @click="toggleSpecialty(area)"
                      >
                        <div class="h-4 w-4 rounded border flex items-center justify-center shrink-0" 
                             :class="form.specialty_areas.includes(area) ? 'bg-primary border-primary' : 'bg-white border-input'">
                          <Check v-if="form.specialty_areas.includes(area)" class="w-3 h-3 text-white" />
                        </div>
                        <span class="text-sm font-medium">{{ area }}</span>
                      </div>
                    </div>
                  </div>

                  <div class="grid md:grid-cols-2 gap-6">
                    <div class="space-y-2">
                      <Label>执业年限</Label>
                      <div class="relative">
                        <Input type="number" v-model.number="form.years_of_experience" placeholder="0" min="0" class="pr-8" />
                        <span class="absolute right-3 top-2.5 text-sm text-muted-foreground">年</span>
                      </div>
                    </div>
                    <div class="space-y-2">
                      <Label>教育背景</Label>
                      <Input v-model="form.education_background" placeholder="例如: 北京大学 法学硕士" />
                    </div>
                  </div>

                  <div class="space-y-2">
                    <Label>个人简介</Label>
                    <Textarea 
                      v-model="form.bio" 
                      placeholder="请简要介绍您的从业经历、擅长领域及成功案例..." 
                      rows="4" 
                      class="resize-none"
                    />
                  </div>
                </div>

                <Separator />

                <div class="space-y-4">
                  <h3 class="text-sm font-medium text-muted-foreground uppercase tracking-wider flex items-center gap-2">
                    <MapPin class="w-4 h-4" /> 服务设置
                  </h3>
                  
                  <div class="grid md:grid-cols-2 gap-6">
                    <div class="space-y-2">
                      <Label>所在省份</Label>
                      <Input v-model="form.province_name" placeholder="例如: 北京市" />
                    </div>
                    <div class="space-y-2">
                      <Label>所在城市</Label>
                      <Input v-model="form.city_name" placeholder="例如: 朝阳区" />
                    </div>
                    <div class="space-y-2">
                      <Label>咨询费 (元/次)</Label>
                      <Input type="number" v-model.number="form.consultation_fee_cny" placeholder="0.00" min="0" step="0.01" />
                    </div>
                    <div class="space-y-2">
                      <Label>时薪 (元/小时)</Label>
                      <Input type="number" v-model.number="form.hourly_rate_cny" placeholder="0.00" min="0" step="0.01" />
                    </div>
                  </div>
                </div>

                <Separator />

                <div class="space-y-4">
                  <h3 class="text-sm font-medium text-muted-foreground uppercase tracking-wider flex items-center gap-2">
                    <FileText class="w-4 h-4" /> 资质证明
                  </h3>
                  
                  <div 
                    class="border-2 border-dashed rounded-xl p-8 text-center cursor-pointer hover:bg-slate-50 transition-colors group"
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
                    <div class="w-12 h-12 bg-primary/10 rounded-full flex items-center justify-center mx-auto mb-3 group-hover:bg-primary/20 transition-colors">
                      <UploadCloud class="w-6 h-6 text-primary" />
                    </div>
                    <p class="font-medium text-foreground">点击上传证明文件</p>
                    <p class="text-sm text-muted-foreground mt-1">请上传执业证、学历证等扫描件 (支持 PDF/JPG/PNG, 最大10MB)</p>
                  </div>

                  <div v-if="selectedFiles.length > 0" class="space-y-2">
                    <div v-for="(file, index) in selectedFiles" :key="index" class="flex items-center justify-between p-3 bg-slate-50 rounded-lg border">
                      <div class="flex items-center gap-3 overflow-hidden">
                        <div class="w-8 h-8 bg-white rounded border flex items-center justify-center shrink-0">
                          <FileText class="w-4 h-4 text-slate-500" />
                        </div>
                        <div class="min-w-0">
                          <p class="text-sm font-medium truncate">{{ file.name }}</p>
                          <p class="text-xs text-muted-foreground">{{ formatFileSize(file.size) }}</p>
                        </div>
                      </div>
                      <Button variant="ghost" size="icon" class="text-muted-foreground hover:text-destructive" @click="removeFile(index)">
                        <X class="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                </div>

                <div class="flex items-start gap-2 pt-2">
                  <div class="flex items-center h-5">
                    <input 
                      id="terms" 
                      type="checkbox" 
                      v-model="agreedToTerms" 
                      class="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
                    />
                  </div>
                  <label for="terms" class="text-sm text-muted-foreground">
                    我已阅读并同意 <a href="#" class="text-primary hover:underline" @click.prevent="showTerms">《专业人士服务协议》</a>，保证所填信息真实有效。
                  </label>
                </div>

              </CardContent>
              
              <CardFooter class="flex justify-end gap-4 border-t bg-slate-50/50 p-6 rounded-b-xl">
                <Button variant="outline" type="button" @click="$router.push('/professional')">取消</Button>
                <Button type="submit" size="lg" :loading="submitting" :disabled="!agreedToTerms">提交认证申请</Button>
              </CardFooter>
            </Card>
          </form>
        </div>

      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import Sidebar from '@/components/Sidebar.vue'
import apiClient from '@/utils/api'
import { 
  Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter,
  Button, Input, Label, Textarea, Separator, Skeleton, Alert 
} from '@/components/ui'
import { 
  Check, User, Briefcase, MapPin, FileText, UploadCloud, 
  X, Info, Clock, CheckCircle2, AlertCircle, ArrowRight 
} from 'lucide-vue-next'

const router = useRouter()
const authStore = useAuthStore()

// State
const loading = ref(true)
const submitting = ref(false)
const verificationStatus = ref(null)
const agreedToTerms = ref(false)
const fileInput = ref(null)
const selectedFiles = ref([])

const form = ref({
  full_name: '', license_number: '', law_firm_name: '', specialty_areas: [],
  years_of_experience: null, education_background: '', bio: '',
  consultation_fee_cny: null, hourly_rate_cny: null,
  city_name: '', province_name: ''
})

const specialtyOptions = ['劳动纠纷', '合同纠纷', '债务纠纷', '交通事故', '医疗纠纷', '房产纠纷', '知识产权', '婚姻家庭', '刑事辩护', '行政诉讼', '公司法务', '其他']

// Methods
const checkVerificationStatus = async () => {
  try {
    const response = await apiClient.get('/verification/my-request')
    if (response.data.status !== 'none') {
      verificationStatus.value = response.data
    }
  } catch (error) {
    console.error('Failed to check status:', error)
  } finally {
    loading.value = false
  }
}

const toggleSpecialty = (area) => {
  const idx = form.value.specialty_areas.indexOf(area)
  if (idx === -1) form.value.specialty_areas.push(area)
  else form.value.specialty_areas.splice(idx, 1)
}

const handleFileSelect = (event) => {
  const files = Array.from(event.target.files)
  if (selectedFiles.value.length + files.length > 5) {
    alert('最多只能上传5个文件')
    return
  }
  for (const file of files) {
    if (file.size > 10 * 1024 * 1024) {
      alert(`文件 ${file.name} 超过10MB限制`)
      return
    }
  }
  selectedFiles.value = [...selectedFiles.value, ...files]
}

const removeFile = (index) => {
  selectedFiles.value.splice(index, 1)
}

const submitVerification = async () => {
  if (!form.value.full_name || !form.value.license_number) {
    alert('请填写必填项:姓名和执业证号')
    return
  }
  if (selectedFiles.value.length === 0) {
    alert('请至少上传一个证明文件')
    return
  }
  
  submitting.value = true
  try {
    const formData = new FormData()
    for (const [key, value] of Object.entries(form.value)) {
      if (key === 'specialty_areas') {
        value.forEach(area => formData.append('specialty_areas', area))
      } else if (value !== null && value !== '') {
        formData.append(key, value)
      }
    }
    selectedFiles.value.forEach(file => formData.append('files', file))
    
    await apiClient.post('/verification/request', formData)
    await checkVerification()
  } catch (error) {
    alert(error.response?.data?.detail || '提交失败')
  } finally {
    submitting.value = false
  }
}

const retryVerification = () => {
  verificationStatus.value = null
}

const showTerms = () => {
  alert('《专业人士服务协议》\n1. 您保证提交的所有信息真实有效\n2. 您同意遵守平台服务规则...')
}

// Helpers
const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const formatDate = (d) => new Date(d).toLocaleString('zh-CN')

// Status Helpers
const getStatusTitle = (s) => ({ pending: '认证审核中', approved: '认证已通过', rejected: '认证未通过' }[s] || '状态未知')
const getStatusDescription = (s) => ({
  pending: '您的认证申请已提交，管理员正在审核中，请耐心等待。',
  approved: '恭喜！您已完成专业认证，现在可以开始接单了。',
  rejected: '很抱歉，您的认证申请未通过审核。请查看原因并重新提交。'
}[s] || '')
const getStatusIcon = (s) => ({ pending: Clock, approved: CheckCircle2, rejected: AlertCircle }[s])
const getStatusIconBg = (s) => ({ pending: 'bg-amber-100', approved: 'bg-emerald-100', rejected: 'bg-red-100' }[s])
const getStatusIconColor = (s) => ({ pending: 'text-amber-600', approved: 'text-emerald-600', rejected: 'text-red-600' }[s])
const getStatusBorderClass = (s) => ({ pending: 'border-t-amber-500', approved: 'border-t-emerald-500', rejected: 'border-t-red-500' }[s])

onMounted(() => {
  if (authStore.userRole !== 'professional') {
    router.push('/dashboard')
    return
  }
  checkVerificationStatus()
})
</script>