<template>
  <div class="flex min-h-screen bg-slate-50/50">
    <Sidebar />
    
    <main class="flex-1 p-8 ml-64 overflow-y-auto">
      <div class="max-w-6xl mx-auto space-y-8">
        
        <div class="flex items-center justify-between">
          <div class="space-y-1">
            <h1 class="text-3xl font-bold tracking-tight text-foreground">管理员控制台</h1>
            <p class="text-muted-foreground">系统概览与核心管理功能</p>
          </div>
          <div class="text-sm text-muted-foreground bg-white px-3 py-1 rounded-full border shadow-sm">
            {{ currentDate }}
          </div>
        </div>

        <div class="grid gap-4 md:grid-cols-3">
          <Card class="hover:shadow-md transition-shadow">
            <CardHeader class="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle class="text-sm font-medium">总用户数</CardTitle>
              <div class="h-8 w-8 rounded-lg bg-blue-100 flex items-center justify-center">
                <Users class="h-4 w-4 text-blue-600" />
              </div>
            </CardHeader>
            <CardContent>
              <div v-if="loading" class="space-y-2">
                <Skeleton class="h-8 w-20" />
                <Skeleton class="h-4 w-32" />
              </div>
              <div v-else>
                <div class="text-2xl font-bold">{{ stats.totalUsers }}</div>
                <p class="text-xs text-muted-foreground mt-1">平台注册用户总数</p>
              </div>
            </CardContent>
          </Card>

          <Card class="hover:shadow-md transition-shadow">
            <CardHeader class="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle class="text-sm font-medium">案件总数</CardTitle>
              <div class="h-8 w-8 rounded-lg bg-emerald-100 flex items-center justify-center">
                <FileText class="h-4 w-4 text-emerald-600" />
              </div>
            </CardHeader>
            <CardContent>
              <div v-if="loading" class="space-y-2">
                <Skeleton class="h-8 w-20" />
                <Skeleton class="h-4 w-32" />
              </div>
              <div v-else>
                <div class="text-2xl font-bold">{{ stats.totalCases }}</div>
                <p class="text-xs text-muted-foreground mt-1">全平台累计案件</p>
              </div>
            </CardContent>
          </Card>

          <Card class="hover:shadow-md transition-shadow cursor-pointer border-l-4 border-l-amber-500" @click="$router.push('/admin/verifications')">
            <CardHeader class="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle class="text-sm font-medium">待审核认证</CardTitle>
              <div class="h-8 w-8 rounded-lg bg-amber-100 flex items-center justify-center">
                <ShieldAlert class="h-4 w-4 text-amber-600" />
              </div>
            </CardHeader>
            <CardContent>
              <div v-if="loading" class="space-y-2">
                <Skeleton class="h-8 w-20" />
                <Skeleton class="h-4 w-32" />
              </div>
              <div v-else>
                <div class="text-2xl font-bold text-amber-600">{{ stats.pendingVerifications }}</div>
                <p class="text-xs text-muted-foreground mt-1">需要立即处理的申请</p>
              </div>
            </CardContent>
          </Card>
        </div>

        <Separator />

        <div>
          <h2 class="text-lg font-semibold mb-4">快捷管理</h2>
          <div class="grid gap-6 md:grid-cols-3">
            
            <Card 
              class="group cursor-pointer hover:border-primary/50 hover:shadow-lg transition-all duration-300"
              @click="$router.push('/admin/users')"
            >
              <CardHeader>
                <div class="mb-2 w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center group-hover:bg-primary/10 transition-colors">
                  <UserCog class="w-6 h-6 text-slate-600 group-hover:text-primary" />
                </div>
                <CardTitle>用户管理</CardTitle>
                <CardDescription>查看、编辑或禁用用户账号，管理权限设置</CardDescription>
              </CardHeader>
              <CardContent>
                <div class="flex items-center text-sm font-medium text-primary opacity-0 group-hover:opacity-100 transition-opacity transform translate-x-[-10px] group-hover:translate-x-0 duration-300">
                  进入管理 <ArrowRight class="ml-1 h-4 w-4" />
                </div>
              </CardContent>
            </Card>

            <Card 
              class="group cursor-pointer hover:border-primary/50 hover:shadow-lg transition-all duration-300"
              @click="$router.push('/admin/cases')"
            >
              <CardHeader>
                <div class="mb-2 w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center group-hover:bg-primary/10 transition-colors">
                  <Activity class="w-6 h-6 text-slate-600 group-hover:text-primary" />
                </div>
                <CardTitle>案件监控</CardTitle>
                <CardDescription>实时查看全平台案件状态，监控服务质量</CardDescription>
              </CardHeader>
              <CardContent>
                <div class="flex items-center text-sm font-medium text-primary opacity-0 group-hover:opacity-100 transition-opacity transform translate-x-[-10px] group-hover:translate-x-0 duration-300">
                  查看监控 <ArrowRight class="ml-1 h-4 w-4" />
                </div>
              </CardContent>
            </Card>

            <Card 
              class="group cursor-pointer hover:border-primary/50 hover:shadow-lg transition-all duration-300"
              @click="$router.push('/admin/verifications')"
            >
              <CardHeader>
                <div class="mb-2 w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center group-hover:bg-primary/10 transition-colors">
                  <ShieldCheck class="w-6 h-6 text-slate-600 group-hover:text-primary" />
                </div>
                <CardTitle>认证审核</CardTitle>
                <CardDescription>审批律师/专业人员的入驻申请与资质文件</CardDescription>
              </CardHeader>
              <CardContent>
                <div class="flex items-center text-sm font-medium text-primary opacity-0 group-hover:opacity-100 transition-opacity transform translate-x-[-10px] group-hover:translate-x-0 duration-300">
                  开始审核 <ArrowRight class="ml-1 h-4 w-4" />
                </div>
              </CardContent>
            </Card>

          </div>
        </div>

      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import Sidebar from '@/components/Sidebar.vue'
import apiClient from '@/utils/api'
import { 
  Card, CardHeader, CardTitle, CardContent, CardDescription,
  Skeleton, Separator 
} from '@/components/ui'
import { 
  Users, FileText, ShieldAlert, UserCog, 
  Activity, ShieldCheck, ArrowRight 
} from 'lucide-vue-next'

const loading = ref(true)
const stats = ref({ 
  totalUsers: 0, 
  totalCases: 0, 
  pendingVerifications: 0 
})

const currentDate = computed(() => {
  return new Date().toLocaleDateString('zh-CN', { 
    weekday: 'long', 
    year: 'numeric', 
    month: 'long', 
    day: 'numeric' 
  })
})

onMounted(async () => {
  try {
    const res = await apiClient.get('/admin/stats')
    // Ensure we handle the response correctly based on API shape
    stats.value = res.data || { totalUsers: 0, totalCases: 0, pendingVerifications: 0 }
  } catch (e) {
    console.error('Failed to load stats:', e)
  } finally {
    // Add a small delay to prevent flickering if api is too fast, gives smoother feel
    setTimeout(() => {
      loading.value = false
    }, 300)
  }
})
</script>