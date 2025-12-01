<template>
  <div class="flex min-h-screen bg-slate-50/50">
    <Sidebar />
    
    <main class="flex-1 p-8 ml-64 overflow-y-auto">
      <div class="max-w-4xl mx-auto space-y-8">
        
        <div class="flex items-center justify-between">
          <h1 class="text-3xl font-bold tracking-tight text-foreground">个人中心</h1>
          <Button variant="outline" @click="$router.push('/dashboard')">
            <ArrowLeft class="w-4 h-4 mr-2" /> 返回仪表板
          </Button>
        </div>

        <div v-if="isLoading" class="space-y-6">
          <div class="flex items-center space-x-4">
            <Skeleton class="h-20 w-20 rounded-full" />
            <div class="space-y-2">
              <Skeleton class="h-6 w-48" />
              <Skeleton class="h-4 w-32" />
            </div>
          </div>
          <Skeleton class="h-[400px] w-full rounded-xl" />
        </div>

        <div v-else class="space-y-6">
          <Card class="border-none shadow-sm bg-white">
            <CardContent class="p-6">
              <div class="flex flex-col md:flex-row items-center gap-6">
                <Avatar class="h-24 w-24 border-4 border-slate-50">
                  <div class="bg-primary/10 text-primary h-full w-full flex items-center justify-center text-3xl font-bold">
                    {{ profile.full_name?.[0] || profile.username?.[0] || 'U' }}
                  </div>
                </Avatar>
                <div class="space-y-1 text-center md:text-left flex-1">
                  <h2 class="text-2xl font-bold">{{ profile.full_name || '未设置姓名' }}</h2>
                  <div class="flex flex-wrap items-center justify-center md:justify-start gap-3 text-sm text-muted-foreground">
                    <span class="flex items-center gap-1">
                      <Phone class="w-3.5 h-3.5" /> {{ profile.phone || '无手机号' }}
                    </span>
                    <span class="flex items-center gap-1">
                      <Mail class="w-3.5 h-3.5" /> {{ profile.email || '未绑定邮箱' }}
                    </span>
                    <span class="flex items-center gap-1">
                      <Calendar class="w-3.5 h-3.5" /> 注册于 {{ formatDate(profile.created_at) }}
                    </span>
                  </div>
                </div>
                <div>
                  <Badge :variant="profile.role === 'professional' ? 'default' : 'secondary'" class="px-4 py-1 text-sm capitalize">
                    {{ getRoleText(profile.role) }}
                  </Badge>
                </div>
              </div>
            </CardContent>
          </Card>

          <Tabs default-value="general" class="w-full">
            <TabsList class="w-full justify-start border-b rounded-none h-auto p-0 bg-transparent mb-6">
              <TabsTrigger value="general" class="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent px-4 pb-3 pt-2">
                基本信息
              </TabsTrigger>
              <TabsTrigger value="security" class="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent px-4 pb-3 pt-2">
                安全设置
              </TabsTrigger>
              <TabsTrigger 
                v-if="profile.role === 'professional'" 
                value="professional" 
                class="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent px-4 pb-3 pt-2"
              >
                专业认证
              </TabsTrigger>
            </TabsList>

            <TabsContent value="general" class="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle>编辑个人资料</CardTitle>
                  <CardDescription>更新您的基本联系信息</CardDescription>
                </CardHeader>
                <CardContent>
                  <form @submit.prevent="saveBasicInfo" class="space-y-4">
                    <div class="grid md:grid-cols-2 gap-6">
                      <div class="space-y-2">
                        <Label for="fullName">姓名</Label>
                        <Input id="fullName" v-model="editForm.full_name" placeholder="请输入您的姓名" />
                      </div>
                      <div class="space-y-2">
                        <Label for="nickname">昵称</Label>
                        <Input id="nickname" v-model="editForm.nickname" placeholder="请输入昵称" />
                      </div>
                      <div class="space-y-2">
                        <Label for="email">邮箱地址</Label>
                        <Input id="email" type="email" v-model="editForm.email" placeholder="example@email.com" />
                      </div>
                      <div class="space-y-2">
                        <Label for="phone">手机号</Label>
                        <Input id="phone" v-model="profile.phone" disabled class="bg-slate-50 text-muted-foreground" />
                      </div>
                    </div>
                    
                    <div class="space-y-2">
                      <Label for="bio">个人简介</Label>
                      <Textarea id="bio" v-model="editForm.description" placeholder="写一句话介绍自己..." rows="4" class="resize-none" />
                    </div>

                    <div class="flex justify-end pt-4">
                      <Button type="submit" :loading="isSaving">保存更改</Button>
                    </div>
                  </form>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="security" class="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle>修改密码</CardTitle>
                  <CardDescription>定期修改密码以保护您的账户安全</CardDescription>
                </CardHeader>
                <CardContent>
                  <form @submit.prevent="changePassword" class="space-y-4 max-w-md">
                    <div class="space-y-2">
                      <Label for="current_password">当前密码</Label>
                      <Input id="current_password" type="password" v-model="passwordForm.current_password" required />
                    </div>
                    <div class="space-y-2">
                      <Label for="new_password">新密码</Label>
                      <Input id="new_password" type="password" v-model="passwordForm.new_password" minlength="8" required />
                      <p class="text-[0.8rem] text-muted-foreground">密码长度至少为 8 个字符</p>
                    </div>
                    <div class="space-y-2">
                      <Label for="confirm_password">确认新密码</Label>
                      <Input id="confirm_password" type="password" v-model="passwordForm.confirm_password" required />
                    </div>
                    <div class="pt-4">
                      <Button type="submit" :loading="isSaving" variant="secondary">更新密码</Button>
                    </div>
                  </form>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="professional" v-if="profile.role === 'professional'">
              <Card>
                <CardHeader>
                  <div class="flex items-center justify-between">
                    <div>
                      <CardTitle>认证状态</CardTitle>
                      <CardDescription>查看您的专业认证详情</CardDescription>
                    </div>
                    <Badge :class="getVerificationBadgeClass(verificationStatus)">
                      {{ getVerificationStatusText(verificationStatus) }}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent class="space-y-6">
                  <Alert v-if="verificationStatus === 'pending'" class="bg-amber-50 text-amber-900 border-amber-200">
                    <AlertCircle class="h-4 w-4" />
                    <div class="ml-2">
                      <h3 class="font-medium">尚未认证</h3>
                      <p class="text-sm mt-1">您还未提交认证信息，完成认证后才能开始接单。</p>
                      <Button size="sm" class="mt-3 bg-amber-600 hover:bg-amber-700 text-white" @click="showVerificationDialog = true">
                        立即认证
                      </Button>
                    </div>
                  </Alert>

                  <Alert v-else-if="verificationStatus === 'submitted'" class="bg-blue-50 text-blue-900 border-blue-200">
                    <Clock class="h-4 w-4" />
                    <div class="ml-2">
                      <h3 class="font-medium">审核中</h3>
                      <p class="text-sm mt-1">您的资料正在审核中，请耐心等待。</p>
                    </div>
                  </Alert>

                  <div v-else-if="verificationStatus === 'approved'" class="grid gap-6">
                    <div class="grid md:grid-cols-2 gap-4">
                      <div class="p-4 bg-slate-50 rounded-lg space-y-1">
                        <span class="text-xs text-muted-foreground uppercase tracking-wider">专业领域</span>
                        <p class="font-medium">{{ verificationData.specialization }}</p>
                      </div>
                      <div class="p-4 bg-slate-50 rounded-lg space-y-1">
                        <span class="text-xs text-muted-foreground uppercase tracking-wider">执业证号</span>
                        <p class="font-mono">{{ verificationData.license_number }}</p>
                      </div>
                      <div class="p-4 bg-slate-50 rounded-lg space-y-1">
                        <span class="text-xs text-muted-foreground uppercase tracking-wider">工作单位</span>
                        <p class="font-medium">{{ verificationData.organization }}</p>
                      </div>
                      <div class="p-4 bg-slate-50 rounded-lg space-y-1">
                        <span class="text-xs text-muted-foreground uppercase tracking-wider">从业年限</span>
                        <p class="font-medium">{{ verificationData.years_experience }} 年</p>
                      </div>
                    </div>
                    
                    <div v-if="verificationData.bio" class="p-4 bg-slate-50 rounded-lg space-y-1">
                      <span class="text-xs text-muted-foreground uppercase tracking-wider">个人简介</span>
                      <p class="text-sm leading-relaxed text-muted-foreground">{{ verificationData.bio }}</p>
                    </div>

                    <div class="flex justify-end">
                      <Button variant="outline" @click="$router.push('/professional/profile')">
                        管理详细资料
                      </Button>
                    </div>
                  </div>

                  <Alert v-else-if="verificationStatus === 'rejected'" variant="destructive">
                    <XCircle class="h-4 w-4" />
                    <div class="ml-2">
                      <h3 class="font-medium">认证未通过</h3>
                      <p class="text-sm mt-1">原因: {{ verificationData.rejection_reason || '未提供原因' }}</p>
                      <Button variant="outline" size="sm" class="mt-3 border-red-200 hover:bg-red-50 text-red-700" @click="showVerificationDialog = true">
                        重新提交
                      </Button>
                    </div>
                  </Alert>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </main>

    <Dialog :open="showVerificationDialog" @close="showVerificationDialog = false">
      <div class="space-y-6">
        <div>
          <h2 class="text-lg font-bold">提交专业认证</h2>
          <p class="text-sm text-muted-foreground">请填写真实的执业信息</p>
        </div>
        
        <form @submit.prevent="submitVerification" class="space-y-4">
          <div class="space-y-2">
            <Label>专业领域 <span class="text-red-500">*</span></Label>
            <Select v-model="verificationForm.specialization" required>
              <option value="" disabled>请选择</option>
              <option value="律师">律师</option>
              <option value="法律顾问">法律顾问</option>
              <option value="调解员">调解员</option>
              <option value="仲裁员">仲裁员</option>
              <option value="其他">其他</option>
            </Select>
          </div>
          
          <div class="grid grid-cols-2 gap-4">
            <div class="space-y-2">
              <Label>执业证号 <span class="text-red-500">*</span></Label>
              <Input v-model="verificationForm.license_number" placeholder="请输入证号" required />
            </div>
            <div class="space-y-2">
              <Label>从业年限 <span class="text-red-500">*</span></Label>
              <Input type="number" v-model.number="verificationForm.years_experience" min="0" placeholder="0" required />
            </div>
          </div>

          <div class="space-y-2">
            <Label>工作单位 <span class="text-red-500">*</span></Label>
            <Input v-model="verificationForm.organization" placeholder="律所/公司名称" required />
          </div>

          <div class="space-y-2">
            <Label>个人简介</Label>
            <Textarea v-model="verificationForm.bio" placeholder="简要介绍您的经历..." rows="3" />
          </div>

          <div class="flex justify-end gap-3 pt-4">
            <Button type="button" variant="ghost" @click="showVerificationDialog = false">取消</Button>
            <Button type="submit" :loading="isSaving">提交申请</Button>
          </div>
        </form>
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
  Card, CardHeader, CardTitle, CardDescription, CardContent, 
  Button, Input, Label, Textarea, Avatar, Badge, Tabs, TabsList, TabsTrigger, TabsContent,
  Skeleton, Dialog, Alert, Select
} from '@/components/ui'
import { 
  ArrowLeft, Phone, Mail, Calendar, ShieldCheck, 
  AlertCircle, Clock, XCircle 
} from 'lucide-vue-next'

const router = useRouter()
const authStore = useAuthStore()

// State
const isLoading = ref(true)
const isSaving = ref(false)
const showVerificationDialog = ref(false)

const profile = ref({})
const verificationStatus = ref('pending')
const verificationData = ref({})

const editForm = ref({ full_name: '', nickname: '', email: '', description: '' })
const passwordForm = ref({ current_password: '', new_password: '', confirm_password: '' })
const verificationForm = ref({ specialization: '', license_number: '', organization: '', years_experience: 0, bio: '' })

// Methods
const loadProfile = async () => {
  isLoading.value = true
  try {
    const response = await apiClient.get('/profile/me')
    profile.value = response.data
    
    // Populate edit form
    editForm.value = {
      full_name: profile.value.full_name || '',
      nickname: profile.value.nickname || '',
      email: profile.value.email || '', // Assuming email might be in profile response for display
      description: profile.value.description || ''
    }
    
    // If professional, load status
    if (profile.value.role === 'professional') {
      await loadVerificationStatus()
    }
  } catch (error) {
    console.error('Failed to load profile:', error)
  } finally {
    isLoading.value = false
  }
}

const loadVerificationStatus = async () => {
  try {
    const response = await apiClient.get('/professional/verification-status')
    verificationStatus.value = response.data.status
    verificationData.value = response.data.data || {}
  } catch (error) { /* ignore */ }
}

const saveBasicInfo = async () => {
  isSaving.value = true
  try {
    await apiClient.put('/profile/me', editForm.value)
    await loadProfile()
    alert('个人资料已更新')
  } catch (error) {
    alert('保存失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    isSaving.value = false
  }
}

const changePassword = async () => {
  if (passwordForm.value.new_password !== passwordForm.value.confirm_password) {
    alert('两次输入的新密码不一致')
    return
  }
  isSaving.value = true
  try {
    await apiClient.post('/auth/password/change', {
      old_password: passwordForm.value.current_password,
      new_password: passwordForm.value.new_password
    })
    passwordForm.value = { current_password: '', new_password: '', confirm_password: '' }
    alert('密码修改成功')
  } catch (error) {
    alert('修改失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    isSaving.value = false
  }
}

const submitVerification = async () => {
  isSaving.value = true
  try {
    await apiClient.post('/professional/verification', verificationForm.value)
    showVerificationDialog.value = false
    await loadVerificationStatus()
    alert('提交成功，请等待审核')
  } catch (error) {
    alert('提交失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    isSaving.value = false
  }
}

// Helpers
const getRoleText = (role) => ({ user: '普通用户', professional: '专业人员', admin: '管理员' }[role] || role)
const formatDate = (d) => d ? new Date(d).toLocaleDateString('zh-CN') : '-'

const getVerificationStatusText = (s) => ({
  pending: '未认证', submitted: '审核中', approved: '已认证', rejected: '未通过'
}[s] || s)

const getVerificationBadgeClass = (s) => ({
  pending: 'bg-slate-500', submitted: 'bg-blue-500', approved: 'bg-emerald-500', rejected: 'bg-red-500'
}[s] || 'bg-slate-500')

onMounted(loadProfile)
</script>