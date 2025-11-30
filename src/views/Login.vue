<template>
  <div class="login-container">
    <div class="glass-card login-box">
      <div class="logo-area">
        <div class="logo-circle">⚖️</div>
        <h1>法律助手</h1>
        <p>您的专业法律服务平台</p>
      </div>

      <div class="tabs">
        <button 
          :class="{ active: mode === 'login' }" 
          @click="mode = 'login'"
        >登录</button>
        <button 
          :class="{ active: mode === 'register' }" 
          @click="mode = 'register'"
        >注册</button>
      </div>

      <form v-if="mode === 'login'" @submit.prevent="handleLogin" class="auth-form">
        <div class="form-group">
          <input 
            v-model="loginForm.username" 
            type="text" 
            class="input" 
            placeholder="用户名 / 手机号" 
            required 
          />
        </div>
        <div class="form-group">
          <input 
            v-model="loginForm.password" 
            type="password" 
            class="input" 
            placeholder="密码" 
            required 
          />
        </div>
        <button type="submit" class="btn btn-primary full-width" :disabled="isLoading">
          {{ isLoading ? '登录中...' : '立即登录' }}
        </button>
      </form>

      <form v-if="mode === 'register'" @submit.prevent="handleRegister" class="auth-form">
        <div class="form-group">
          <input 
            v-model="regForm.username" 
            type="text" 
            class="input" 
            placeholder="用户名" 
            required 
          />
        </div>
        <div class="form-group">
          <input 
            v-model="regForm.phone" 
            type="tel" 
            class="input" 
            placeholder="手机号" 
            required 
          />
        </div>
        <div class="form-group">
          <select v-model="regForm.role" class="input">
            <option value="user">普通用户</option>
            <option value="professional">法律专业人士</option>
            <option value="admin">管理员 (测试用)</option>
          </select>
        </div>
        <div class="form-group">
          <input 
            v-model="regForm.password" 
            type="password" 
            class="input" 
            placeholder="设置密码 (至少8位)" 
            required 
          />
        </div>
        <button type="submit" class="btn btn-primary full-width" :disabled="isLoading">
          {{ isLoading ? '注册中...' : '注册并自动登录' }}
        </button>
      </form>

      <p v-if="msg" :class="['message', msgType]">{{ msg }}</p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import apiClient from '@/utils/api'

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

<style scoped>
.login-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  /* No background here, using global animated bg */
}

.login-box {
  width: 100%;
  max-width: 420px;
  padding: 40px;
  text-align: center;
  animation: fadeInUp 0.5s ease-out;
}

.logo-circle {
  width: 60px;
  height: 60px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 50%;
  font-size: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 16px;
  box-shadow: 0 10px 20px rgba(102, 126, 234, 0.3);
}

h1 { font-size: 24px; color: #2d3748; margin-bottom: 8px; }
p { color: #718096; font-size: 14px; margin-bottom: 32px; }

.tabs {
  display: flex;
  border-bottom: 2px solid rgba(0,0,0,0.05);
  margin-bottom: 24px;
}

.tabs button {
  flex: 1;
  background: none;
  border: none;
  padding: 12px;
  font-size: 16px;
  color: #a0aec0;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.3s;
}

.tabs button.active {
  color: #667eea;
  border-bottom: 2px solid #667eea;
  margin-bottom: -2px;
}

.form-group { margin-bottom: 20px; }
.full-width { width: 100%; padding: 12px; font-size: 16px; }

.message { margin-top: 16px; font-size: 14px; padding: 8px; border-radius: 8px; }
.message.error { background: #fff5f5; color: #e53e3e; }
.message.success { background: #f0fff4; color: #38a169; }

@keyframes fadeInUp { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
</style>