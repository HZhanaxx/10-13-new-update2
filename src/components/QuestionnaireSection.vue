<template>
  <div class="questionnaire-section">
    <div class="section-header">
      <h2>📋 智能问卷</h2>
      <p>通过填写详细问卷,帮助律师更好地了解您的案件</p>
    </div>

    <!-- 问卷模板列表 -->
    <div class="questionnaire-templates">
      <div 
        v-for="template in templates" 
        :key="template.id"
        class="template-card"
        @click="startQuestionnaire(template.id)"
      >
        <div class="template-icon">{{ template.icon }}</div>
        <div class="template-info">
          <h3>{{ template.name }}</h3>
          <p>{{ template.description }}</p>
          <span class="template-duration">⏱️ 预计 {{ template.duration }} 分钟</span>
        </div>
        <button class="btn-start">开始填写 →</button>
      </div>
    </div>

    <!-- 进行中的问卷 -->
    <div v-if="activeSessions.length > 0" class="active-sessions">
      <h3>进行中的问卷</h3>
      <div class="session-list">
        <div 
          v-for="session in activeSessions" 
          :key="session.session_id"
          class="session-card"
          @click="resumeSession(session.session_id)"
        >
          <div class="session-info">
            <h4>{{ getTemplateName(session.template_type) }}</h4>
            <div class="session-meta">
              <span>📅 {{ formatDate(session.created_at) }}</span>
              <span>📊 步骤 {{ session.current_step }}</span>
            </div>
          </div>
          <button class="btn-resume">继续填写</button>
        </div>
      </div>
    </div>

    <!-- 已完成的问卷 -->
    <div v-if="completedSubmissions.length > 0" class="completed-submissions">
      <h3>已提交的问卷</h3>
      <div class="submission-list">
        <div 
          v-for="submission in completedSubmissions" 
          :key="submission.submission_id"
          class="submission-card"
        >
          <div class="submission-info">
            <h4>{{ getTemplateName(submission.template_type) }}</h4>
            <span class="submission-id">编号: {{ submission.submission_id }}</span>
            <div class="submission-meta">
              <span>📅 {{ formatDate(submission.completed_at) }}</span>
              <span :class="['status-badge', `status-${submission.status}`]">
                {{ getStatusText(submission.status) }}
              </span>
            </div>
          </div>
          <button class="btn-view" @click="viewSubmission(submission.submission_id)">
            查看详情
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import apiClient from '@/utils/api'

const router = useRouter()

// 问卷模板配置
const templates = ref([
  {
    id: 1,
    name: '交通事故问卷',
    description: '详细记录交通事故情况，包括时间、地点、责任认定等',
    icon: '🚗',
    duration: 10
  },
  {
    id: 2,
    name: '劳动纠纷问卷',
    description: '记录劳动合同、工资待遇、工作环境等相关信息',
    icon: '💼',
    duration: 15
  },
  {
    id: 3,
    name: '合同纠纷问卷',
    description: '详细记录合同签订、履行、违约等情况',
    icon: '📄',
    duration: 12
  },
  {
    id: 4,
    name: '通用法律咨询',
    description: '记录您的法律问题和相关背景信息',
    icon: '⚖️',
    duration: 8
  }
])

// 进行中的问卷会话
const activeSessions = ref([])

// 已完成的提交
const completedSubmissions = ref([])

// 加载用户的问卷数据
const loadQuestionnaireData = async () => {
  try {
    // 加载进行中的会话
    const sessionsResponse = await apiClient.get('/questionnaire/sessions', {
      params: { status_filter: 'in_progress' }
    })
    activeSessions.value = sessionsResponse.data || []

    // 加载已完成的提交
    const submissionsResponse = await apiClient.get('/questionnaire/submissions', {
      params: { limit: 5 }
    })
    completedSubmissions.value = submissionsResponse.data || []
  } catch (error) {
    console.error('Failed to load questionnaire data:', error)
  }
}

// 开始新问卷
const startQuestionnaire = async (templateType) => {
  try {
    const response = await apiClient.post('/questionnaire/sessions/start', {
      template_type: templateType,
      metadata: {
        started_from: 'dashboard'
      }
    })

    const sessionId = response.data.session_id

    // 跳转到问卷页面
    router.push(`/questionnaire/${sessionId}`)
  } catch (error) {
    console.error('Failed to start questionnaire:', error)
    alert('启动问卷失败，请稍后重试')
  }
}

// 继续填写问卷
const resumeSession = (sessionId) => {
  router.push(`/questionnaire/${sessionId}`)
}

// 查看提交详情
const viewSubmission = (submissionId) => {
  router.push(`/questionnaire/submission/${submissionId}`)
}

// 获取模板名称
const getTemplateName = (templateType) => {
  const template = templates.value.find(t => t.id === templateType)
  return template ? template.name : '未知问卷'
}

// 获取状态文本
const getStatusText = (status) => {
  const statusMap = {
    'pending': '待审核',
    'reviewing': '审核中',
    'completed': '已完成',
    'rejected': '已拒绝'
  }
  return statusMap[status] || status
}

// 格式化日期
const formatDate = (dateString) => {
  const date = new Date(dateString)
  return date.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// 初始化
onMounted(() => {
  loadQuestionnaireData()
})
</script>

<style scoped>
.questionnaire-section {
  margin-top: 32px;
}

.section-header {
  margin-bottom: 24px;
}

.section-header h2 {
  font-size: 20px;
  color: #2d2d2d;
  margin-bottom: 8px;
}

.section-header p {
  color: #666;
  font-size: 14px;
}

.questionnaire-templates {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
  margin-bottom: 32px;
}

.template-card {
  background: white;
  border: 2px solid #e5e5e5;
  border-radius: 12px;
  padding: 20px;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.template-card:hover {
  border-color: #667eea;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.15);
  transform: translateY(-2px);
}

.template-icon {
  font-size: 32px;
  text-align: center;
  margin-bottom: 8px;
}

.template-info h3 {
  font-size: 16px;
  color: #2d2d2d;
  margin-bottom: 8px;
}

.template-info p {
  font-size: 14px;
  color: #666;
  margin-bottom: 8px;
  line-height: 1.5;
}

.template-duration {
  font-size: 13px;
  color: #999;
}

.btn-start {
  background: #667eea;
  color: white;
  border: none;
  padding: 10px 16px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
  margin-top: auto;
}

.btn-start:hover {
  background: #5568d3;
}

.active-sessions,
.completed-submissions {
  margin-top: 32px;
}

.active-sessions h3,
.completed-submissions h3 {
  font-size: 18px;
  color: #2d2d2d;
  margin-bottom: 16px;
}

.session-list,
.submission-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.session-card,
.submission-card {
  background: white;
  border: 1px solid #e5e5e5;
  border-radius: 8px;
  padding: 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  transition: all 0.2s;
}

.session-card:hover,
.submission-card:hover {
  border-color: #667eea;
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.1);
}

.session-info,
.submission-info {
  flex: 1;
}

.session-info h4,
.submission-info h4 {
  font-size: 16px;
  color: #2d2d2d;
  margin-bottom: 8px;
}

.submission-id {
  font-size: 12px;
  color: #999;
  display: block;
  margin-bottom: 8px;
}

.session-meta,
.submission-meta {
  display: flex;
  gap: 16px;
  font-size: 13px;
  color: #666;
}

.btn-resume,
.btn-view {
  background: #f5f5f5;
  color: #667eea;
  border: 1px solid #e5e5e5;
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}

.btn-resume:hover,
.btn-view:hover {
  background: #667eea;
  color: white;
  border-color: #667eea;
}

.status-badge {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
}

.status-pending {
  background: #fff3cd;
  color: #856404;
}

.status-reviewing {
  background: #d1ecf1;
  color: #0c5460;
}

.status-completed {
  background: #d4edda;
  color: #155724;
}

.status-rejected {
  background: #f8d7da;
  color: #721c24;
}

@media (max-width: 768px) {
  .questionnaire-templates {
    grid-template-columns: 1fr;
  }

  .session-card,
  .submission-card {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }

  .btn-resume,
  .btn-view {
    width: 100%;
  }
}
</style>
