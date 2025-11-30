<template>
  <div class="page-container">
    <Sidebar />
    <div class="main-content">
      <header class="page-header">
        <h1>📊 案件监控中心</h1>
      </header>

      <div class="stats-grid">
        <div class="glass-card stat-card" v-for="(value, key) in stats" :key="key">
          <div class="stat-icon">{{ getStatIcon(key) }}</div>
          <div class="stat-info">
            <div class="stat-value">{{ value }}</div>
            <div class="stat-label">{{ getStatLabel(key) }}</div>
          </div>
        </div>
      </div>

      <div class="glass-card monitor-section">
        <div class="section-header">
          <h3>最近动态</h3>
          <button class="btn-refresh" @click="loadData">↻ 刷新</button>
        </div>
        
        <div class="monitor-list">
          <transition-group name="list">
            <div v-for="log in recentCases" :key="log.case_uuid" class="monitor-item">
              <div class="monitor-status" :class="getStatusClass(log.case_status)">●</div>
              <div class="monitor-content">
                <div class="monitor-title">{{ log.title }}</div>
                <div class="monitor-meta">
                  <span>{{ formatDate(log.updated_at || log.created_at) }}</span>
                  <span v-if="log.professional_name"> · 负责人: {{ log.professional_name }}</span>
                  <span v-else> · 待接单</span>
                </div>
              </div>
              <div class="monitor-badge">{{ getStatusText(log.case_status) }}</div>
            </div>
          </transition-group>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import Sidebar from '@/components/Sidebar.vue'
import apiClient from '@/utils/api'

const stats = ref({
  total_cases: 0,
  pending: 0,
  in_progress: 0,
  completed: 0
})
const recentCases = ref([])

const loadData = async () => {
  try {
    // 1. Load Stats
    const statRes = await apiClient.get('/admin/stats')
    stats.value = {
        total_cases: statRes.data.totalCases,
        pending: statRes.data.pendingVerifications, // Mapping example, adjust to actual API
        in_progress: statRes.data.totalCases - statRes.data.pendingVerifications, // Simple math example
        completed: 0 // Fetch actual if available
    }

    // 2. Load Cases
    const caseRes = await apiClient.get('/admin/cases')
    recentCases.value = caseRes.data.cases.slice(0, 5) // Show top 5
  } catch (e) {
    console.error('Load monitoring data failed', e)
  }
}

const getStatLabel = (key) => {
  const labels = { total_cases: '总案件数', pending: '待处理', in_progress: '进行中', completed: '已完成' }
  return labels[key] || key
}

const getStatIcon = (key) => {
  const icons = { total_cases: '📁', pending: '⏳', in_progress: '⚡', completed: '✅' }
  return icons[key] || '📋'
}

const getStatusText = (status) => {
  const map = { pending: '待接单', in_progress: '处理中', completed: '已结案', cancelled: '已取消' }
  return map[status] || status
}

const getStatusClass = (status) => {
  if (status === 'in_progress') return 'processing'
  if (status === 'completed') return 'success'
  return 'pending'
}

const formatDate = (d) => new Date(d).toLocaleString('zh-CN')

onMounted(loadData)
</script>

<style scoped>
.stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 24px; margin-bottom: 32px; }
.stat-card { padding: 24px; display: flex; align-items: center; gap: 20px; transition: transform 0.3s; }
.stat-card:hover { transform: translateY(-5px); }
.stat-icon { width: 50px; height: 50px; background: rgba(102, 126, 234, 0.1); border-radius: 12px; display: flex; align-items: center; justify-content: center; font-size: 24px; }
.stat-value { font-size: 28px; font-weight: 800; color: #2d3748; line-height: 1; margin-bottom: 4px; }
.stat-label { font-size: 13px; color: #718096; font-weight: 500; }

.monitor-section { padding: 30px; }
.section-header { display: flex; justify-content: space-between; margin-bottom: 24px; }
.btn-refresh { background: none; border: none; color: #667eea; cursor: pointer; font-size: 14px; }

.monitor-item { display: flex; align-items: center; padding: 16px; border-bottom: 1px solid rgba(0,0,0,0.05); transition: background 0.2s; border-radius: 8px; }
.monitor-item:hover { background: rgba(255,255,255,0.4); }
.monitor-status { margin-right: 16px; font-size: 12px; color: #cbd5e0; }
.monitor-status.processing { color: #4299e1; text-shadow: 0 0 10px rgba(66, 153, 225, 0.5); }
.monitor-status.success { color: #48bb78; }

.monitor-content { flex: 1; }
.monitor-title { font-weight: 600; color: #2d3748; margin-bottom: 4px; }
.monitor-meta { font-size: 12px; color: #a0aec0; }

.monitor-badge { font-size: 12px; font-weight: 600; color: #718096; background: #edf2f7; padding: 4px 10px; border-radius: 12px; }
</style>