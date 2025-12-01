<template>
  <div class="flex min-h-screen bg-slate-50/50">
    <Sidebar />
    
    <main class="flex-1 p-8 ml-64 overflow-y-auto">
      <div class="max-w-6xl mx-auto space-y-6">
        
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div class="space-y-1">
            <h1 class="text-3xl font-bold tracking-tight text-foreground">用户管理</h1>
            <p class="text-muted-foreground">查看、编辑或禁用系统用户账号</p>
          </div>
          <div class="relative w-full sm:w-72">
            <Search class="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              v-model="searchQuery"
              type="text"
              placeholder="搜索姓名或邮箱..."
              class="pl-9 bg-white"
            />
          </div>
        </div>

        <Card class="border shadow-sm">
          <CardHeader class="p-4 border-b bg-slate-50/50 flex flex-row items-center justify-between">
            <CardTitle class="text-base font-medium">用户列表 ({{ filteredUsers.length }})</CardTitle>
            <Button variant="outline" size="sm" class="h-8" @click="loadUsers">
              <RefreshCcw class="h-3.5 w-3.5 mr-2" /> 刷新
            </Button>
          </CardHeader>
          
          <CardContent class="p-0">
            <div v-if="isLoading" class="p-6 space-y-4">
              <div v-for="i in 5" :key="i" class="flex items-center space-x-4">
                <Skeleton class="h-10 w-10 rounded-full" />
                <div class="space-y-2 flex-1">
                  <Skeleton class="h-4 w-1/4" />
                  <Skeleton class="h-4 w-1/3" />
                </div>
              </div>
            </div>

            <div v-else class="relative w-full overflow-auto">
              <table class="w-full text-sm text-left">
                <thead class="text-xs text-muted-foreground uppercase bg-slate-50 border-b">
                  <tr>
                    <th class="px-6 py-3 font-medium">用户信息</th>
                    <th class="px-6 py-3 font-medium">角色</th>
                    <th class="px-6 py-3 font-medium">状态</th>
                    <th class="px-6 py-3 font-medium">注册日期</th>
                    <th class="px-6 py-3 font-medium text-right">操作</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-border">
                  <tr v-if="filteredUsers.length === 0">
                    <td colspan="5" class="px-6 py-12 text-center text-muted-foreground">
                      未找到匹配的用户
                    </td>
                  </tr>
                  
                  <tr v-for="user in filteredUsers" :key="user.id" class="bg-white hover:bg-slate-50/50 transition-colors">
                    <td class="px-6 py-4">
                      <div class="flex items-center gap-3">
                        <Avatar class="h-9 w-9 border">
                          <div class="bg-indigo-100 text-indigo-600 h-full w-full flex items-center justify-center font-bold text-xs">
                            {{ user.username ? user.username.charAt(0).toUpperCase() : 'U' }}
                          </div>
                        </Avatar>
                        <div>
                          <div class="font-medium text-foreground">{{ user.username || '未命名' }}</div>
                          <div class="text-xs text-muted-foreground">{{ user.email || user.phone || '无联系方式' }}</div>
                        </div>
                      </div>
                    </td>
                    <td class="px-6 py-4">
                      <Badge variant="outline" :class="getRoleBadgeClass(user.role)">
                        {{ getRoleName(user.role) }}
                      </Badge>
                    </td>
                    <td class="px-6 py-4">
                      <div class="flex items-center gap-2">
                        <span class="relative flex h-2 w-2">
                          <span v-if="user.is_active" class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                          <span class="relative inline-flex rounded-full h-2 w-2" :class="user.is_active ? 'bg-emerald-500' : 'bg-slate-300'"></span>
                        </span>
                        <span :class="user.is_active ? 'text-emerald-700' : 'text-slate-500'">
                          {{ user.is_active ? '活跃' : '禁用' }}
                        </span>
                      </div>
                    </td>
                    <td class="px-6 py-4 text-muted-foreground font-mono text-xs">
                      {{ formatDate(user.created_at) }}
                    </td>
                    <td class="px-6 py-4 text-right">
                      <div class="flex justify-end gap-2">
                        <Button variant="ghost" size="sm" @click="editUser(user)">编辑</Button>
                        <Button 
                          variant="ghost" 
                          size="sm" 
                          :class="user.is_active ? 'text-red-600 hover:text-red-700 hover:bg-red-50' : 'text-emerald-600 hover:text-emerald-700 hover:bg-emerald-50'"
                          @click="toggleStatus(user)"
                        >
                          {{ user.is_active ? '禁用' : '启用' }}
                        </Button>
                      </div>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>

      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import Sidebar from '@/components/Sidebar.vue'
import apiClient from '@/utils/api'
import { 
  Card, CardHeader, CardTitle, CardContent,
  Button, Input, Badge, Skeleton, Avatar
} from '@/components/ui'
import { Search, RefreshCcw } from 'lucide-vue-next'

const users = ref([])
const isLoading = ref(true)
const searchQuery = ref('')

const loadUsers = async () => {
  isLoading.value = true
  try {
    const response = await apiClient.get('/admin/users')
    users.value = response.data.users || response.data
  } catch (error) {
    console.error('Failed to load users:', error)
  } finally {
    isLoading.value = false
  }
}

const filteredUsers = computed(() => {
  if (!searchQuery.value) return users.value
  const query = searchQuery.value.toLowerCase()
  return users.value.filter(u => 
    (u.username && u.username.toLowerCase().includes(query)) ||
    (u.email && u.email.toLowerCase().includes(query)) ||
    (u.phone && u.phone.includes(query))
  )
})

const getRoleName = (role) => {
  const map = { admin: '管理员', professional: '专业人员', user: '普通用户' }
  return map[role] || role
}

const getRoleBadgeClass = (role) => {
  const map = {
    admin: 'bg-purple-50 text-purple-700 border-purple-200',
    professional: 'bg-blue-50 text-blue-700 border-blue-200',
    user: 'bg-slate-50 text-slate-700 border-slate-200'
  }
  return map[role] || ''
}

const formatDate = (date) => new Date(date).toLocaleDateString('zh-CN')

const toggleStatus = async (user) => {
  const action = user.is_active ? '禁用' : '启用'
  if(!confirm(`确定要${action}该用户吗？`)) return
  try {
    await apiClient.post(`/admin/users/${user.id || user.user_uuid}/${user.is_active ? 'deactivate' : 'activate'}`)
    user.is_active = !user.is_active
  } catch (e) {
    alert('操作失败')
  }
}

const editUser = (user) => {
  // Implement edit logic or navigation
  alert('编辑功能开发中')
}

onMounted(loadUsers)
</script>