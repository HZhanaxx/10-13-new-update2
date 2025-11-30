<template>
  <div class="page-container">
    <Sidebar />
    <div class="main-content">
      <header class="page-header">
        <h1>🛡️ 管理员控制台</h1>
      </header>

      <div class="stats-grid">
        <div class="glass-card stat-card">
          <h3>总用户</h3>
          <div class="number">{{ stats.totalUsers }}</div>
        </div>
        <div class="glass-card stat-card">
          <h3>总案件</h3>
          <div class="number">{{ stats.totalCases }}</div>
        </div>
        <div class="glass-card stat-card">
          <h3>待审核专业人员</h3>
          <div class="number highlight">{{ stats.pendingVerifications }}</div>
        </div>
      </div>

      <h2 class="section-title">快捷管理</h2>
      <div class="action-grid">
        <div class="glass-card action-card" @click="$router.push('/admin/users')">
          <div class="icon">👥</div>
          <h3>用户管理</h3>
          <p>查看、编辑或禁用用户账号</p>
        </div>
        <div class="glass-card action-card" @click="$router.push('/admin/cases')">
          <div class="icon">📊</div>
          <h3>案件监控</h3>
          <p>实时查看全平台案件状态</p>
        </div>
        <div class="glass-card action-card" @click="$router.push('/admin/verifications')">
          <div class="icon">✅</div>
          <h3>认证审核</h3>
          <p>审批律师/专业人员的入驻申请</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import Sidebar from '@/components/Sidebar.vue'
import apiClient from '@/utils/api'

const stats = ref({ totalUsers: '-', totalCases: '-', pendingVerifications: '-' })

onMounted(async () => {
  try {
    const res = await apiClient.get('/admin/stats')
    stats.value = res.data
  } catch (e) {
    console.error('Failed to load stats')
  }
})
</script>

<style scoped>
.stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 24px; margin-bottom: 40px; }
.stat-card { padding: 24px; text-align: center; }
.stat-card h3 { font-size: 14px; color: #718096; margin-bottom: 8px; font-weight: 500; }
.number { font-size: 36px; font-weight: 800; color: #2d3748; }
.number.highlight { color: #e53e3e; }

.section-title { margin-bottom: 20px; font-size: 18px; color: #4a5568; }
.action-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 24px; }
.action-card { padding: 30px; cursor: pointer; transition: all 0.3s; display: flex; flex-direction: column; align-items: center; text-align: center; }
.action-card:hover { transform: translateY(-5px); background: rgba(255,255,255,0.85); }
.action-card .icon { font-size: 40px; margin-bottom: 16px; }
.action-card h3 { font-size: 18px; margin-bottom: 8px; color: #2d3748; }
.action-card p { font-size: 14px; color: #718096; }
</style>