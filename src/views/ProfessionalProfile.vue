<template>
  <div class="flex min-h-screen bg-slate-50/50">
    <Sidebar />
    
    <main class="flex-1 p-8 ml-64 overflow-y-auto">
      <div v-if="loading" class="max-w-4xl mx-auto space-y-6">
        <Skeleton class="h-32 w-full rounded-xl" />
        <Skeleton class="h-[500px] w-full rounded-xl" />
      </div>

      <div v-else class="max-w-4xl mx-auto space-y-6">
        <div class="flex items-center gap-4">
          <Button variant="ghost" size="icon" @click="$router.go(-1)">
            <ArrowLeft class="w-5 h-5" />
          </Button>
          <h1 class="text-3xl font-bold tracking-tight">专业资料</h1>
        </div>

        <Alert v-if="verificationStatus" :class="getAlertClass(verificationStatus.status)">
          <div class="flex items-start gap-3">
            <component :is="getStatusIcon(verificationStatus.status)" class="w-5 h-5 mt-0.5" />
            <div>
              <h3 class="font-medium text-base">{{ getStatusTitle(verificationStatus.status) }}</h3>
              <p class="text-sm opacity-90 mt-1">{{ getStatusMessage(verificationStatus.status) }}</p>
            </div>
          </div>
        </Alert>

        <Card class="overflow-hidden">
          <CardHeader class="border-b bg-slate-50/50 pb-4">
            <div class="flex items-center justify-between">
              <div class="space-y-1">
                <CardTitle>个人信息管理</CardTitle>
                <CardDescription>管理您的公开展示信息与执业资质</CardDescription>
              </div>
              <Button v-if="!editing && professionalInfo" @click="startEdit" size="sm">
                <Edit3 class="w-4 h-4 mr-2" /> 编辑资料
              </Button>
            </div>
          </CardHeader>

          <CardContent class="p-0">
            <Tabs default-value="info" class="w-full">
              <div class="px-6 pt-4">
                <TabsList class="w-full justify-start border-b rounded-none h-auto p-0 bg-transparent">
                  <TabsTrigger value="info" class="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent px-4 pb-3 pt-2">
                    基本资料
                  </TabsTrigger>
                  <TabsTrigger value="verification" class="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent px-4 pb-3 pt-2">
                    认证信息
                  </TabsTrigger>
                </TabsList>
              </div>

              <TabsContent value="info" class="p-6">
                <div v-if="!editing && professionalInfo" class="space-y-8 animate-in fade-in duration-300">
                  <div class="grid md:grid-cols-2 gap-8">
                    <div class="space-y-4">
                      <h3 class="font-medium text-sm text-muted-foreground uppercase tracking-wider">基本信息</h3>
                      <div class="space-y-3">
                        <div class="flex justify-between border-b border-dashed pb-2">
                          <span class="text-muted-foreground">姓名</span>
                          <span class="font-medium">{{ professionalInfo.full_name || '-' }}</span>
                        </div>
                        <div class="flex justify-between border-b border-dashed pb-2">
                          <span class="text-muted-foreground">执业证号</span>
                          <span class="font-mono">{{ professionalInfo.license_number || '-' }}</span>
                        </div>
                        <div class="flex justify-between border-b border-dashed pb-2">
                          <span class="text-muted-foreground">所在律所</span>
                          <span>{{ professionalInfo.law_firm_name || '-' }}</span>
                        </div>
                        <div class="flex justify-between border-b border-dashed pb-2">
                          <span class="text-muted-foreground">从业年限</span>
                          <span>{{ professionalInfo.years_of_experience || 0 }} 年</span>
                        </div>
                        <div class="flex justify-between border-b border-dashed pb-2">
                          <span class="text-muted-foreground">所在地</span>
                          <span>{{ formatLocation(professionalInfo.province_name, professionalInfo.city_name) }}</span>
                        </div>
                      </div>
                    </div>

                    <div class="space-y-4">
                      <h3 class="font-medium text-sm text-muted-foreground uppercase tracking-wider">服务定价</h3>
                      <div class="grid grid-cols-2 gap-4">
                        <div class="bg-slate-50 p-4 rounded-xl border text-center">
                          <div class="text-muted-foreground text-xs mb-1">咨询费 (次)</div>
                          <div class="text-xl font-bold text-emerald-600">¥{{ professionalInfo.consultation_fee_cny || 0 }}</div>
                        </div>
                        <div class="bg-slate-50 p-4 rounded-xl border text-center">
                          <div class="text-muted-foreground text-xs mb-1">时薪</div>
                          <div class="text-xl font-bold text-blue-600">¥{{ professionalInfo.hourly_rate_cny || 0 }}</div>
                        </div>
                      </div>
                    </div>
                  </div>

                  <Separator />

                  <div class="space-y-4">
                    <h3 class="font-medium text-sm text-muted-foreground uppercase tracking-wider">专业领域</h3>
                    <div class="flex flex-wrap gap-2">
                      <Badge v-for="area in parseSpecialtyAreas(professionalInfo.specialty_areas)" :key="area" variant="secondary" class="px-3 py-1">
                        {{ area }}
                      </Badge>
                      <span v-if="!professionalInfo.specialty_areas" class="text-sm text-muted-foreground">未设置</span>
                    </div>
                  </div>

                  <div class="grid md:grid-cols-2 gap-8">
                    <div class="space-y-2">
                      <h3 class="font-medium text-sm text-muted-foreground uppercase tracking-wider">教育背景</h3>
                      <p class="text-sm leading-relaxed whitespace-pre-wrap bg-slate-50 p-3 rounded-lg border">{{ professionalInfo.education_background || '未设置' }}</p>
                    </div>
                    <div class="space-y-2">
                      <h3 class="font-medium text-sm text-muted-foreground uppercase tracking-wider">个人简介</h3>
                      <p class="text-sm leading-relaxed whitespace-pre-wrap bg-slate-50 p-3 rounded-lg border">{{ professionalInfo.bio || '未设置' }}</p>
                    </div>
                  </div>
                </div>

                <form v-else-if="editing" @submit.prevent="saveChanges" class="space-y-6">
                  <div class="grid md:grid-cols-2 gap-6">
                    <div class="space-y-2">
                      <Label>姓名 <span class="text-red-500">*</span></Label>
                      <Input v-model="editForm.full_name" required />
                    </div>
                    <div class="space-y-2">
                      <Label>执业证号 <span class="text-red-500">*</span></Label>
                      <Input v-model="editForm.license_number" required />
                    </div>
                    <div class="space-y-2">
                      <Label>律所名称 <span class="text-red-500">*</span></Label>
                      <Input v-model="editForm.law_firm_name" required />
                    </div>
                    <div class="space-y-2">
                      <Label>从业年限</Label>
                      <Input v-model.number="editForm.years_of_experience" type="number" min="0" />
                    </div>
                    <div class="space-y-2">
                      <Label>省份</Label>
                      <Input v-model="editForm.province_name" />
                    </div>
                    <div class="space-y-2">
                      <Label>城市</Label>
                      <Input v-model="editForm.city_name" />
                    </div>
                  </div>

                  <div class="space-y-3">
                    <Label>专业领域 (多选)</Label>
                    <div class="grid grid-cols-2 sm:grid-cols-4 gap-2">
                      <div v-for="area in availableSpecialties" :key="area" 
                        class="flex items-center space-x-2 border p-2 rounded cursor-pointer hover:bg-slate-50"
                        :class="editForm.specialty_areas.includes(area) ? 'border-primary bg-primary/5 ring-1 ring-primary' : ''"
                        @click="toggleSpecialty(area)"
                      >
                        <div class="h-4 w-4 rounded border flex items-center justify-center" :class="editForm.specialty_areas.includes(area) ? 'bg-primary border-primary' : 'bg-white'">
                          <Check v-if="editForm.specialty_areas.includes(area)" class="w-3 h-3 text-white" />
                        </div>
                        <span class="text-xs">{{ area }}</span>
                      </div>
                    </div>
                  </div>

                  <div class="grid md:grid-cols-2 gap-6">
                    <div class="space-y-2">
                      <Label>咨询费用 (CNY)</Label>
                      <Input v-model.number="editForm.consultation_fee_cny" type="number" step="0.01" />
                    </div>
                    <div class="space-y-2">
                      <Label>时薪 (CNY)</Label>
                      <Input v-model.number="editForm.hourly_rate_cny" type="number" step="0.01" />
                    </div>
                  </div>

                  <div class="space-y-2">
                    <Label>教育背景</Label>
                    <Textarea v-model="editForm.education_background" rows="3" />
                  </div>

                  <div class="space-y-2">
                    <Label>个人简介</Label>
                    <Textarea v-model="editForm.bio" rows="5" />
                  </div>

                  <Alert class="bg-blue-50 text-blue-800 border-blue-200">
                    <AlertCircle class="w-4 h-4" />
                    <div class="ml-2 text-sm">
                      注意：修改关键信息（如姓名、执业证号）将触发重新审核，期间可能会限制接单功能。
                    </div>
                  </Alert>

                  <div class="flex justify-end gap-3 pt-4 border-t">
                    <Button type="button" variant="outline" @click="cancelEdit">取消</Button>
                    <Button type="submit" :loading="saving">保存并提交审核</Button>
                  </div>
                </form>

                <div v-else class="text-center py-12">
                  <div class="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    <UserX class="w-8 h-8 text-slate-400" />
                  </div>
                  <h3 class="text-lg font-medium">暂无资料</h3>
                  <p class="text-muted-foreground mb-6">您还没有填写专业资料</p>
                  <Button @click="startEdit">立即完善</Button>
                </div>
              </TabsContent>

              <TabsContent value="verification" class="p-6">
                <div class="space-y-6">
                  <div class="grid md:grid-cols-3 gap-6">
                    <Card class="bg-slate-50 border shadow-none">
                      <CardHeader class="pb-2">
                        <CardTitle class="text-sm font-medium text-muted-foreground">当前状态</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <Badge :class="getVerificationBadgeClass(professionalInfo?.is_verified)">
                          {{ professionalInfo?.is_verified ? '已认证' : '未认证' }}
                        </Badge>
                      </CardContent>
                    </Card>
                    <Card class="bg-slate-50 border shadow-none">
                      <CardHeader class="pb-2">
                        <CardTitle class="text-sm font-medium text-muted-foreground">认证时间</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div class="text-lg font-medium">{{ formatDate(professionalInfo?.verified_at) }}</div>
                      </CardContent>
                    </Card>
                    <Card class="bg-slate-50 border shadow-none">
                      <CardHeader class="pb-2">
                        <CardTitle class="text-sm font-medium text-muted-foreground">账户状态</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div class="text-lg font-medium capitalize">{{ professionalInfo?.account_status || 'Unknown' }}</div>
                      </CardContent>
                    </Card>
                  </div>
                  
                  <div class="p-4 rounded-lg border bg-white">
                    <h3 class="font-medium mb-2 flex items-center gap-2">
                      <ShieldCheck class="w-4 h-4 text-emerald-600" />
                      认证说明
                    </h3>
                    <ul class="list-disc list-inside text-sm text-muted-foreground space-y-1 ml-1">
                      <li>已认证的专业人员可以无限制访问案件池。</li>
                      <li>所有的修改记录都会被系统存档。</li>
                      <li>如需注销认证，请联系管理员。</li>
                    </ul>
                  </div>
                </div>
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>
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
  Card, CardHeader, CardTitle, CardDescription, CardContent,
  Button, Badge, Skeleton, Alert, Input, Label, Textarea, 
  Tabs, TabsList, TabsTrigger, TabsContent, Separator
} from '@/components/ui'
import { 
  ArrowLeft, Edit3, ShieldAlert, CheckCircle2, Clock, 
  ShieldCheck, AlertCircle, UserX, Check 
} from 'lucide-vue-next'

const router = useRouter()
const authStore = useAuthStore()

// State
const loading = ref(true)
const editing = ref(false)
const saving = ref(false)
const professionalInfo = ref(null)
const verificationStatus = ref(null)
const customSpecialty = ref('')

const availableSpecialties = ['刑事辩护', '民事诉讼', '商事诉讼', '行政诉讼', '劳动争议', '婚姻家庭', '房产纠纷', '合同纠纷', '知识产权', '交通事故', '医疗纠纷']

const editForm = ref({
  full_name: '', license_number: '', law_firm_name: '', specialty_areas: [],
  years_of_experience: 0, education_background: '', bio: '',
  consultation_fee_cny: 0, hourly_rate_cny: 0, city_name: '', province_name: ''
})

// Methods
const loadProfessionalInfo = async () => {
  try {
    const res = await apiClient.get('/professional/profile')
    professionalInfo.value = res.data
  } catch (error) {
    if (error.response?.status === 404) professionalInfo.value = null
  }
}

const loadVerificationStatus = async () => {
  try {
    const res = await apiClient.get('/professional/verification-status')
    verificationStatus.value = res.data
  } catch (error) { /* ignore */ }
}

const startEdit = () => {
  const info = professionalInfo.value
  editForm.value = {
    full_name: info.full_name || '',
    license_number: info.license_number || '',
    law_firm_name: info.law_firm_name || '',
    specialty_areas: parseSpecialtyAreas(info.specialty_areas),
    years_of_experience: info.years_of_experience || 0,
    education_background: info.education_background || '',
    bio: info.bio || '',
    consultation_fee_cny: info.consultation_fee_cny || 0,
    hourly_rate_cny: info.hourly_rate_cny || 0,
    city_name: info.city_name || '',
    province_name: info.province_name || ''
  }
  editing.value = true
}

const cancelEdit = () => { editing.value = false }

const toggleSpecialty = (area) => {
  const idx = editForm.value.specialty_areas.indexOf(area)
  if(idx === -1) editForm.value.specialty_areas.push(area)
  else editForm.value.specialty_areas.splice(idx, 1)
}

const saveChanges = async () => {
  saving.value = true
  try {
    await apiClient.post('/verification/update', {
      ...editForm.value,
      specialty_areas: JSON.stringify(editForm.value.specialty_areas)
    })
    alert('修改已提交！资料将在管理员审核后更新。')
    editing.value = false
    await loadVerificationStatus()
  } catch (error) {
    alert(error.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

// Helpers
const parseSpecialtyAreas = (areas) => {
  if (!areas) return []
  if (Array.isArray(areas)) return areas
  try { return JSON.parse(areas) } catch (e) { return [] }
}

const formatLocation = (p, c) => (!p && !c) ? '-' : `${p || ''} ${c || ''}`.trim()
const formatDate = (d) => d ? new Date(d).toLocaleDateString('zh-CN') : '-'

const getAlertClass = (status) => {
  const map = {
    pending: 'bg-amber-50 text-amber-900 border-amber-200',
    approved: 'bg-emerald-50 text-emerald-900 border-emerald-200',
    rejected: 'bg-red-50 text-red-900 border-red-200'
  }
  return map[status] || 'bg-slate-50'
}

const getStatusIcon = (status) => {
  const map = { pending: Clock, approved: CheckCircle2, rejected: AlertCircle }
  return map[status] || ShieldAlert
}

const getStatusTitle = (status) => {
  const map = { pending: '审核中', approved: '认证已通过', rejected: '认证未通过' }
  return map[status] || '未知状态'
}

const getStatusMessage = (status) => {
  const map = {
    pending: '您的资料正在审核中，请耐心等待',
    approved: '您已通过专业认证，可以接受案件了',
    rejected: '您的认证申请被拒绝，请查看详情并重新提交'
  }
  return map[status] || ''
}

const getVerificationBadgeClass = (verified) => verified ? 'bg-emerald-500 hover:bg-emerald-600' : 'bg-slate-500 hover:bg-slate-600'

onMounted(async () => {
  await Promise.all([loadProfessionalInfo(), loadVerificationStatus()])
  loading.value = false
})
</script>