<template>
  <div class="page-container">
    <Sidebar />
    <div class="main-content">
      <header class="page-header">
        <h1>👥 用户管理</h1>
        <div class="header-actions">
          <div class="search-glass">
            <span>🔍</span>
            <input v-model="searchQuery" type="text" placeholder="搜索姓名或邮箱..." />
          </div>
        </div>
      </header>

      <div class="glass-card table-wrapper">
        <div v-if="isLoading" class="loading-state">加载中...</div>
        
        <table v-else-if="filteredUsers.length > 0">
          <thead>
            <tr>
              <th>用户信息</th>
              <th>角色</th>
              <th>状态</th>
              <th>注册日期</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <transition-group name="list">
              <tr v-for="user in filteredUsers" :key="user.id">
                <td>
                  <div class="user-cell">
                    <div class="avatar">{{ user.username ? user.username.charAt(0).toUpperCase() : 'U' }}</div>
                    <div class="user-info">
                      <div class="user-name">{{ user.username || '未命名' }}</div>
                      <div class="user-email">{{ user.email || user.phone }}</div>
                    </div>
                  </div>
                </td>
                <td>
                  <span class="badge" :class="user.role">{{ getRoleName(user.role) }}</span>
                </td>
                <td>
                  <span class="status-dot" :class="{ active: user.is_active }"></span>
                  {{ user.is_active ? '活跃' : '禁用' }}
                </td>
                <td class="date-cell">{{ formatDate(user.created_at) }}</td>
                <td>
                  <button class="btn-text" @click="editUser(user)">编辑</button>
                  <button class="btn-text danger" @click="toggleStatus(user)">
                    {{ user.is_active ? '禁用' : '启用' }}
                  </button>
                </td>
              </tr>
            </transition-group>
          </tbody>
        </table>
        
        <div v-else class="empty-state">
          <p>未找到用户数据</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import Sidebar from '@/components/Sidebar.vue'
import apiClient from '@/utils/api'

const users = ref([])
const isLoading = ref(true)
const searchQuery = ref('')

// Load users from DB
const loadUsers = async () => {
  try {
    // Assuming you have an endpoint like this. If not, check your backend routes.
    // Usually /api/admin/users
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

const formatDate = (date) => new Date(date).toLocaleDateString('zh-CN')

const toggleStatus = async (user) => {
  if(!confirm(`确定要${user.is_active ? '禁用' : '启用'}该用户吗？`)) return
  try {
    // Example endpoint
    await apiClient.post(`/admin/users/${user.id}/toggle-status`)
    user.is_active = !user.is_active
  } catch (e) {
    alert('操作失败')
  }
}

onMounted(loadUsers)
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; }
.search-glass { display: flex; align-items: center; background: rgba(255,255,255,0.8); padding: 8px 16px; border-radius: 20px; border: 1px solid rgba(255,255,255,0.6); box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
.search-glass input { border: none; background: transparent; margin-left: 8px; outline: none; width: 200px; }

.table-wrapper { overflow: hidden; padding: 0; }
table { width: 100%; border-collapse: collapse; }
th { text-align: left; padding: 20px; background: rgba(248,250,252,0.8); color: #64748b; font-weight: 600; font-size: 13px; text-transform: uppercase; }
td { padding: 20px; border-top: 1px solid rgba(0,0,0,0.05); transition: background 0.2s; }
tr:hover td { background: rgba(255,255,255,0.5); }

.user-cell { display: flex; align-items: center; gap: 12px; }
.avatar { width: 40px; height: 40px; background: linear-gradient(135deg, #a5b4fc 0%, #6366f1 100%); color: white; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; box-shadow: 0 4px 6px rgba(99, 102, 241, 0.3); }
.user-name { font-weight: 600; color: #1e293b; }
.user-email { font-size: 12px; color: #64748b; }

.badge { padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; }
.badge.admin { background: #e0e7ff; color: #4338ca; }
.badge.professional { background: #dbeafe; color: #1e40af; }
.badge.user { background: #f1f5f9; color: #475569; }

.status-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: #ef4444; margin-right: 6px; }
.status-dot.active { background: #10b981; box-shadow: 0 0 0 2px rgba(16, 185, 129, 0.2); }

.btn-text { background: none; border: none; color: #6366f1; cursor: pointer; font-weight: 500; margin-right: 12px; }
.btn-text.danger { color: #ef4444; }

.loading-state, .empty-state { padding: 40px; text-align: center; color: #64748b; }
.list-enter-active, .list-leave-active { transition: all 0.5s ease; }
.list-enter-from, .list-leave-to { opacity: 0; transform: translateX(-30px); }
</style>