<template>
  <div class="flex min-h-screen items-center justify-center bg-slate-50 p-4">
    <Card class="w-full max-w-md shadow-xl border-0">
      <CardHeader class="space-y-2 text-center pb-6">
        <div class="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-primary/10 mb-2">
          <Scale class="h-7 w-7 text-primary" />
        </div>
        <h1 class="text-2xl font-bold tracking-tight text-foreground">法律助手</h1>
        <p class="text-sm text-muted-foreground">您的专业法律服务平台</p>
      </CardHeader>

      <CardContent>
        <Tabs v-model="mode" class="w-full">
          <TabsList class="grid w-full grid-cols-2 mb-6">
            <TabsTrigger value="login">登录</TabsTrigger>
            <TabsTrigger value="register">注册</TabsTrigger>
          </TabsList>

          <TabsContent value="login">
            <form @submit.prevent="handleLogin" class="space-y-4">
              <div class="space-y-2">
                <Label for="login-username">账号</Label>
                <Input 
                  id="login-username" 
                  v-model="loginForm.username" 
                  placeholder="用户名 / 手机号" 
                  required 
                />
              </div>
              <div class="space-y-2">
                <Label for="login-password">密码</Label>
                <Input 
                  id="login-password" 
                  v-model="loginForm.password" 
                  type="password" 
                  placeholder="请输入密码" 
                  required 
                />
              </div>
              <Button type="submit" class="w-full" size="lg" :loading="isLoading">
                {{ isLoading ? '登录中...' : '立即登录' }}
              </Button>
            </form>
          </TabsContent>

          <TabsContent value="register">
            <form @submit.prevent="handleRegister" class="space-y-4">
              <div class="space-y-2">
                <Label for="reg-username">用户名</Label>
                <Input 
                  id="reg-username" 
                  v-model="regForm.username" 
                  placeholder="设置用户名" 
                  required 
                />
              </div>
              <div class="space-y-2">
                <Label for="reg-phone">手机号</Label>
                <Input 
                  id="reg-phone" 
                  v-model="regForm.phone" 
                  type="tel" 
                  placeholder="请输入手机号" 
                  required 
                />
              </div>
              <div class="space-y-2">
                <Label for="reg-role">账户类型</Label>
                <Select v-model="regForm.role">
                  <option value="user">普通用户</option>
                  <option value="professional">法律专业人士</option>
                  <option value="admin">管理员 (测试用)</option>
                </Select>
              </div>
              <div class="space-y-2">
                <Label for="reg-password">密码</Label>
                <Input 
                  id="reg-password" 
                  v-model="regForm.password" 
                  type="password" 
                  placeholder="设置密码 (至少8位)" 
                  required 
                />
              </div>
              <Button type="submit" class="w-full" size="lg" :loading="isLoading">
                {{ isLoading ? '注册中...' : '注册并自动登录' }}
              </Button>
            </form>
          </TabsContent>
        </Tabs>

        <div v-if="msg" class="mt-6">
          <Alert :variant="msgType === 'error' ? 'destructive' : 'default'">
            {{ msg }}
          </Alert>
        </div>
      </CardContent>
    </Card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import apiClient from '@/utils/api'
import { Scale } from 'lucide-vue-next'
import { 
  Card, CardHeader, CardContent, 
  Tabs, TabsList, TabsTrigger, TabsContent,
  Input, Button, Label, Select, Alert 
} from '@/components/ui'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const mode = ref('login')
const isLoading = ref(false)
const msg = ref('')
const msgType = ref('error')

const loginForm = ref({ username: '', password: '' })
const regForm = ref({ username: '', phone: '', password: '', role: 'user' })

// --- Logic: Handle Login & Redirect ---
const handleLogin = async () => {
  isLoading.value = true
  msg.value = ''
  
  try {
    const isPhone = /^1[3-9]\d{9}$/.test(loginForm.value.username)
    const payload = { password: loginForm.value.password }
    
    if (isPhone) payload.phone = loginForm.value.username
    else payload.username = loginForm.value.username

    const res = await apiClient.post('/auth/login', payload)
    
    if (res.data.token) {
      // 1. Save Token
      authStore.setTokens(res.data.token.access_token, res.data.token.refresh_token)
      authStore.setUser(res.data.user)
      
      // 2. Smart Redirect Logic
      const role = res.data.user.role
      
      // Only follow query redirect if it's safe (not sending admin to user dash)
      if (route.query.redirect && !route.query.redirect.includes('/dashboard')) {
        router.push(route.query.redirect)
      } else {
        // Default redirect based on role
        if (role === 'admin') router.push('/admin')
        else if (role === 'professional') router.push('/professional')
        else router.push('/dashboard')
      }
    }
  } catch (e) {
    msgType.value = 'error'
    msg.value = e.response?.data?.detail || '登录失败，请检查账号密码'
  } finally {
    isLoading.value = false
  }
}

// --- Logic: Handle Register & Auto Login ---
const handleRegister = async () => {
  isLoading.value = true
  msg.value = ''

  try {
    const res = await apiClient.post('/auth/register', regForm.value)
    
    // Check if token came back (Auto Login)
    if (res.data.token) {
      authStore.setTokens(res.data.token.access_token, res.data.token.refresh_token)
      authStore.setUser(res.data.user)
      
      msgType.value = 'success'
      msg.value = '注册成功！正在跳转...'
      
      setTimeout(() => {
        if (res.data.user.role === 'admin') router.push('/admin')
        else if (res.data.user.role === 'professional') router.push('/professional')
        else router.push('/dashboard')
      }, 1500)
    } else {
      // Fallback
      msgType.value = 'success'
      msg.value = '注册成功，请登录'
      mode.value = 'login'
    }
  } catch (e) {
    msgType.value = 'error'
    msg.value = e.response?.data?.detail || '注册失败，请重试'
  } finally {
    isLoading.value = false
  }
}
</script>