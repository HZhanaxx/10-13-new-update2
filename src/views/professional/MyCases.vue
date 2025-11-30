<template>
  <div class="page-container">
    <Sidebar />
    <div class="main-content">
      <header class="page-header">
        <h1>💼 我的承接案件</h1>
      </header>

      <div v-if="loading" class="loading-container">加载中...</div>

      <div v-else-if="cases.length > 0" class="cases-grid">
        <transition-group name="list">
          <div class="glass-card case-card" v-for="c in cases" :key="c.case_uuid" @click="goToDetail(c.case_uuid)">
            <div class="card-top">
              <span class="case-id">#{{ c.case_uuid.slice(0, 8) }}</span>
              <span class="status-pill" :class="c.case_status">{{ getStatusText(c.case_status) }}</span>
            </div>
            
            <h3>{{ c.title }}</h3>
            
            <div class="case-info">
              <p>📅 发布: {{ formatDate(c.created_at) }}</p>
              <p>💰 预算: <span class="price">¥{{ c.budget_cny }}</span></p>
            </div>

            <div class="progress-container">
              <div class="progress-bar">
                <div class="progress-fill" :style="{ width: getProgress(c.case_status) }"></div>
              </div>
            </div>

            <div class="card-footer">
              <button class="btn btn-secondary btn-sm" @click.stop="goToDetail(c.case_uuid)">查看详情</button>
            </div>
          </div>
        </transition-group>
      </div>

      <div v-else class="empty-glass">
        <h3>暂无承接案件</h3>
        <p>前往案件池寻找适合您的案件吧</p>
        <button class="btn btn-primary" @click="$router.push('/case-pool')">去接单</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import Sidebar from '@/components/Sidebar.vue'
import apiClient from '@/utils/api'

const router = useRouter()
const cases = ref([])
const loading = ref(true)

const loadMyCases = async () => {
  try {
    const res = await apiClient.get('/professional/my-cases')
    cases.value = res.data.cases || []
  } catch (e) {
    console.error('Failed to load cases', e)
  } finally {
    loading.value = false
  }
}

const goToDetail = (id) => router.push(`/case/${id}`)

const getStatusText = (s) => {
  const map = { in_progress: '进行中', completed: '已完成' }
  return map[s] || s
}

const getProgress = (s) => {
  if (s === 'completed') return '100%'
  if (s === 'in_progress') return '50%'
  return '0%'
}

const formatDate = (d) => new Date(d).toLocaleDateString('zh-CN')

onMounted(loadMyCases)
</script>

<style scoped>
.cases-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 30px; }
.case-card { padding: 24px; display: flex; flex-direction: column; cursor: pointer; position: relative; overflow: hidden; }
.case-card::before { content: ''; position: absolute; top: 0; left: 0; width: 4px; height: 100%; background: linear-gradient(to bottom, #667eea, #764ba2); opacity: 0; transition: opacity 0.3s; }
.case-card:hover::before { opacity: 1; }
.case-card:hover { transform: translateY(-5px); box-shadow: 0 15px 30px rgba(0,0,0,0.1); }

.card-top { display: flex; justify-content: space-between; margin-bottom: 16px; font-size: 12px; color: #a0aec0; }
.status-pill { padding: 4px 10px; border-radius: 20px; font-weight: 600; font-size: 11px; }
.status-pill.in_progress { background: #ebf8ff; color: #4299e1; }
.status-pill.completed { background: #f0fff4; color: #48bb78; }

h3 { font-size: 18px; font-weight: 700; color: #2d3748; margin-bottom: 12px; line-height: 1.4; }

.case-info { font-size: 14px; color: #718096; margin-bottom: 24px; }
.price { color: #48bb78; font-weight: 600; }

.progress-container { margin-bottom: 24px; }
.progress-bar { height: 6px; background: #edf2f7; border-radius: 3px; overflow: hidden; }
.progress-fill { height: 100%; background: linear-gradient(90deg, #667eea, #764ba2); transition: width 1s ease; }

.card-footer { margin-top: auto; }
.btn-sm { width: 100%; font-size: 13px; padding: 8px; }

.empty-glass { text-align: center; padding: 60px; background: rgba(255,255,255,0.5); border-radius: 16px; backdrop-filter: blur(5px); }
.empty-glass h3 { font-size: 20px; color: #4a5568; margin-bottom: 10px; }
.empty-glass p { color: #a0aec0; margin-bottom: 20px; }
</style>