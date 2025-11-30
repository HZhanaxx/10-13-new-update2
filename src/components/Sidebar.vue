<script setup>
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { cn } from '@/lib/utils'
import { 
  Scale, 
  LayoutDashboard, 
  FileText, 
  Users, 
  Settings, 
  LogOut,
  Briefcase,
  CheckCircle,
  UserCog,
  ClipboardList,
  FolderOpen,
  User
} from 'lucide-vue-next'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const userRole = computed(() => authStore.userRole)
const userName = computed(() => authStore.userName || '用户')

const userMenuItems = [
  { path: '/dashboard', label: '我的案件', icon: LayoutDashboard },
  { path: '/cases/new', label: '新建案件', icon: FileText },
  { path: '/profile', label: '个人资料', icon: User },
]

const professionalMenuItems = [
  { path: '/professional', label: '工作台', icon: LayoutDashboard },
  { path: '/case-pool', label: '案件池', icon: FolderOpen },
  { path: '/professional/my-cases', label: '我的案件', icon: Briefcase },
  { path: '/professional/verification', label: '专业认证', icon: CheckCircle },
  { path: '/professional/profile', label: '专业资料', icon: UserCog },
]

const adminMenuItems = [
  { path: '/admin', label: '管理面板', icon: LayoutDashboard },
  { path: '/admin/users', label: '用户管理', icon: Users },
  { path: '/admin/cases', label: '案件监控', icon: ClipboardList },
  { path: '/admin/verifications', label: '认证审核', icon: CheckCircle },
]

const menuItems = computed(() => {
  if (userRole.value === 'admin') return adminMenuItems
  if (userRole.value === 'professional') return professionalMenuItems
  return userMenuItems
})

const isActive = (path) => route.path === path

const logout = () => {
  authStore.clearAuth()
  router.push('/login')
}
</script>

<template>
  <aside class="fixed left-0 top-0 h-full w-64 bg-white border-r border-border flex flex-col z-40">
    <!-- Logo -->
    <div class="p-6 border-b border-border">
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-accent flex items-center justify-center">
          <Scale class="w-5 h-5 text-white" />
        </div>
        <div>
          <h1 class="font-bold text-foreground">智能法律助手</h1>
          <p class="text-xs text-muted-foreground">Legal Assistant</p>
        </div>
      </div>
    </div>

    <!-- User Info -->
    <div class="p-4 border-b border-border">
      <div class="flex items-center gap-3">
        <div class="w-9 h-9 rounded-full bg-primary/10 flex items-center justify-center">
          <User class="w-4 h-4 text-primary" />
        </div>
        <div class="flex-1 min-w-0">
          <p class="font-medium text-sm text-foreground truncate">{{ userName }}</p>
          <p class="text-xs text-muted-foreground capitalize">{{ userRole }}</p>
        </div>
      </div>
    </div>

    <!-- Navigation -->
    <nav class="flex-1 p-4 space-y-1 overflow-y-auto">
      <router-link
        v-for="item in menuItems"
        :key="item.path"
        :to="item.path"
        :class="cn(
          'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
          isActive(item.path)
            ? 'bg-primary text-primary-foreground'
            : 'text-muted-foreground hover:bg-muted hover:text-foreground'
        )"
      >
        <component :is="item.icon" class="w-4 h-4" />
        {{ item.label }}
      </router-link>
    </nav>

    <!-- Logout -->
    <div class="p-4 border-t border-border">
      <button
        @click="logout"
        class="flex items-center gap-3 w-full px-3 py-2.5 rounded-lg text-sm font-medium text-muted-foreground hover:bg-destructive/10 hover:text-destructive transition-colors"
      >
        <LogOut class="w-4 h-4" />
        退出登录
      </button>
    </div>
  </aside>
</template>
