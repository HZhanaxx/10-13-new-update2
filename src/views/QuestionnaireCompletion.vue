<template>
  <div class="completion-page">
    <div class="completion-container">
      <!-- Loading -->
      <div v-if="loading" class="loading-state">
        <div class="spinner"></div>
        <p>{{ loadingText }}</p>
      </div>

      <!-- Error -->
      <div v-else-if="error" class="error-state">
        <div class="error-icon">⚠️</div>
        <h2>出错了</h2>
        <p>{{ error }}</p>
        <button @click="loadCompletionData" class="btn btn-primary">重试</button>
      </div>

      <!-- Main Content -->
      <template v-else>
        <!-- Success Header -->
        <div class="success-header">
          <div class="success-icon">✓</div>
          <h1>问卷填写完成！</h1>
          <p class="subtitle">您的交通事故法律咨询问卷已完成，请查看以下内容并确认下一步操作</p>
        </div>

        <!-- Summaries Section -->
        <section v-if="summaries && Object.keys(summaries).length > 0" class="section summaries-section">
          <div class="section-header">
            <span class="section-icon">📊</span>
            <h2>AI 分析总结</h2>
          </div>
          <div class="summaries-list">
            <div v-for="(summary, partKey) in summaries" :key="partKey" class="summary-card">
              <div class="summary-header">
                <span class="part-badge">{{ getPartTitle(partKey) }}</span>
              </div>
              <div class="summary-content">
                <p>{{ summary.content || summary }}</p>
              </div>
            </div>
          </div>
        </section>

        <!-- Evidence Section -->
        <section v-if="evidenceList && evidenceList.length > 0" class="section evidence-section">
          <div class="section-header">
            <span class="section-icon">📁</span>
            <h2>已上传证据</h2>
          </div>
          <div class="evidence-list">
            <div v-for="(evidence, idx) in evidenceList" :key="idx" class="evidence-item">
              <span class="evidence-number">{{ evidence.evidenceNumber || `证据${idx + 1}` }}</span>
              <span class="evidence-name">{{ evidence.fileName || evidence.filename }}</span>
            </div>
          </div>
        </section>

        <!-- Case Creation Section -->
        <section class="section case-section">
          <div class="section-header">
            <span class="section-icon">⚖️</span>
            <h2>案件发布</h2>
          </div>
          
          <div v-if="isFinalized && caseUuid" class="case-created-info">
            <div class="case-badge success">✓ 案件已创建</div>
            <p>您的案件已发布到案件池，等待专业律师接单。</p>
            <button @click="viewCase" class="btn btn-primary">
              查看案件详情
            </button>
          </div>

          <div v-else class="case-creation-options">
            <div class="option-card" :class="{ selected: createCase }">
              <label class="option-label">
                <input type="checkbox" v-model="createCase" />
                <div class="option-content">
                  <div class="option-title">
                    <span class="option-icon">👨‍⚖️</span>
                    发布到案件池，寻找专业律师
                  </div>
                  <p class="option-desc">
                    将您的案件发布到案件池，由认证律师查看并接单，提供专业法律服务
                  </p>
                </div>
              </label>
            </div>

            <div v-if="createCase" class="case-details-form">
              <div class="form-group">
                <label>案件标题</label>
                <input 
                  type="text" 
                  v-model="caseTitle" 
                  :placeholder="defaultCaseTitle"
                  class="form-input"
                />
              </div>
              <div class="form-group">
                <label>优先级</label>
                <select v-model="casePriority" class="form-select">
                  <option value="low">低 - 不着急</option>
                  <option value="medium">中 - 正常处理</option>
                  <option value="high">高 - 尽快处理</option>
                  <option value="urgent">紧急 - 立即处理</option>
                </select>
              </div>
            </div>

            <div v-if="shouldCreateCase && !createCase" class="recommendation-hint">
              <span class="hint-icon">💡</span>
              根据您的回答，我们建议您发布案件寻找专业律师帮助
            </div>
          </div>
        </section>

        <!-- Document Generation Section -->
        <section class="section documents-section">
          <div class="section-header">
            <span class="section-icon">📄</span>
            <h2>法律文书生成</h2>
          </div>
          
          <div v-if="generatedDocs.length > 0" class="generated-docs">
            <h3>已生成的文书</h3>
            <div class="docs-list">
              <div v-for="doc in generatedDocs" :key="doc.template_code" class="doc-item">
                <span class="doc-icon">📑</span>
                <span class="doc-name">{{ doc.filename || doc.template_code }}</span>
                <a v-if="doc.download_url" :href="doc.download_url" class="btn btn-sm btn-outline" download>
                  下载
                </a>
                <span v-else-if="doc.error" class="error-text">{{ doc.error }}</span>
              </div>
            </div>
          </div>

          <div class="template-selection">
            <p class="selection-hint">选择需要生成的法律文书模板：</p>
            <div class="templates-grid">
              <label 
                v-for="template in recommendedTemplates" 
                :key="template.code"
                class="template-card"
                :class="{ selected: selectedTemplates.includes(template.code) }"
              >
                <input 
                  type="checkbox" 
                  :value="template.code"
                  v-model="selectedTemplates"
                />
                <div class="template-content">
                  <div class="template-name">{{ template.name }}</div>
                  <div class="template-desc">{{ template.description }}</div>
                  <div class="template-code">编号: {{ template.code }}</div>
                </div>
              </label>
            </div>
          </div>
        </section>

        <!-- Action Buttons -->
        <div class="actions-section">
          <button 
            v-if="!isFinalized"
            @click="finalizeQuestionnaire" 
            class="btn btn-primary btn-large"
            :disabled="isSubmitting"
          >
            <span v-if="isSubmitting">处理中...</span>
            <span v-else>
              {{ createCase ? '确认并发布案件' : '确认完成' }}
            </span>
          </button>
          
          <button @click="goToDashboard" class="btn btn-outline">
            返回仪表板
          </button>
        </div>

        <!-- Finalization Result -->
        <div v-if="finalizationResult" class="finalization-result">
          <div class="result-header" :class="finalizationResult.success ? 'success' : 'error'">
            <span class="result-icon">{{ finalizationResult.success ? '✓' : '⚠️' }}</span>
            <h3>{{ finalizationResult.success ? '操作成功' : '操作失败' }}</h3>
          </div>
          <div class="result-details">
            <p v-if="finalizationResult.answers_saved">
              ✓ 问卷答案已保存 (共 {{ finalizationResult.answers_count }} 题)
            </p>
            <p v-if="finalizationResult.case">
              ✓ 案件已创建: {{ finalizationResult.case.title }}
              <button @click="viewCase" class="btn btn-sm btn-primary">查看案件</button>
            </p>
            <p v-if="finalizationResult.case_error" class="error-text">
              ⚠️ 案件创建失败: {{ finalizationResult.case_error }}
            </p>
            <div v-if="finalizationResult.generated_documents?.length > 0">
              <p>✓ 已生成 {{ finalizationResult.generated_documents.filter(d => d.success).length }} 份文书</p>
            </div>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '@/utils/api'

const route = useRoute()
const router = useRouter()

// State
const loading = ref(true)
const loadingText = ref('加载问卷数据...')
const error = ref('')
const isSubmitting = ref(false)

const sessionId = ref('')
const isFinalized = ref(false)
const caseUuid = ref(null)
const shouldCreateCase = ref(false)
const answers = ref({})
const summaries = ref({})
const evidenceList = ref([])
const recommendedTemplates = ref([])
const generatedDocs = ref([])

// Form state
const createCase = ref(false)
const caseTitle = ref('')
const casePriority = ref('medium')
const selectedTemplates = ref([])

const finalizationResult = ref(null)

// Computed
const defaultCaseTitle = computed(() => {
  const accidentType = answers.value?.q2?.value || '交通事故'
  const date = new Date().toISOString().slice(0, 10).replace(/-/g, '')
  return `${accidentType}案件 - ${date}`
})

// Methods
const loadCompletionData = async () => {
  loading.value = true
  error.value = ''
  
  try {
    sessionId.value = route.params.sessionId
    
    const response = await api.get(`/workflow/questionnaire/session/${sessionId.value}/completion-data`)
    const data = response.data
    
    if (data.success) {
      isFinalized.value = data.is_finalized
      caseUuid.value = data.case_uuid
      shouldCreateCase.value = data.should_create_case
      answers.value = data.answers || {}
      summaries.value = data.summaries || {}
      evidenceList.value = data.evidence_list || []
      recommendedTemplates.value = data.recommended_templates || []
      
      // Pre-select create case if should_create_case is true
      if (shouldCreateCase.value && !isFinalized.value) {
        createCase.value = true
      }
      
      // Pre-select recommended templates
      if (recommendedTemplates.value.length > 0 && !isFinalized.value) {
        selectedTemplates.value = recommendedTemplates.value
          .filter(t => t.priority === 1)
          .map(t => t.code)
      }
    } else {
      error.value = data.message || '无法加载数据'
    }
  } catch (err) {
    console.error('Load completion data error:', err)
    error.value = err.response?.data?.detail || err.message || '加载失败'
  } finally {
    loading.value = false
  }
}

const finalizeQuestionnaire = async () => {
  isSubmitting.value = true
  finalizationResult.value = null
  
  try {
    const response = await api.post('/workflow/questionnaire/finalize', {
      session_id: sessionId.value,
      create_case: createCase.value,
      case_title: caseTitle.value || defaultCaseTitle.value,
      case_priority: casePriority.value,
      selected_templates: selectedTemplates.value
    })
    
    finalizationResult.value = response.data
    
    if (response.data.success) {
      isFinalized.value = true
      
      if (response.data.case) {
        caseUuid.value = response.data.case.case_uuid
      }
      
      if (response.data.generated_documents) {
        generatedDocs.value = response.data.generated_documents
      }
    }
  } catch (err) {
    console.error('Finalize error:', err)
    finalizationResult.value = {
      success: false,
      error: err.response?.data?.detail || err.message
    }
  } finally {
    isSubmitting.value = false
  }
}

const viewCase = () => {
  if (caseUuid.value) {
    router.push(`/case/${caseUuid.value}`)
  }
}

const goToDashboard = () => {
  router.push('/dashboard')
}

const getPartTitle = (partKey) => {
  const titles = {
    'part1': '第一部分：基本信息',
    'part2': '第二部分：事故详情',
    'part3': '第三部分：赔偿诉求'
  }
  return titles[partKey] || partKey
}

onMounted(loadCompletionData)
</script>

<style scoped>
.completion-page {
  min-height: 100vh;
  background: linear-gradient(135deg, #f5f7fa 0%, #e4e8eb 100%);
  padding: 40px 20px;
}

.completion-container {
  max-width: 900px;
  margin: 0 auto;
}

/* Loading & Error States */
.loading-state, .error-state {
  text-align: center;
  padding: 80px 20px;
  background: white;
  border-radius: 16px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.08);
}

.spinner {
  width: 48px;
  height: 48px;
  border: 4px solid #e2e8f0;
  border-top-color: #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 20px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.error-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

/* Success Header */
.success-header {
  text-align: center;
  padding: 40px;
  background: white;
  border-radius: 16px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.08);
  margin-bottom: 24px;
}

.success-icon {
  width: 80px;
  height: 80px;
  background: linear-gradient(135deg, #48bb78 0%, #38a169 100%);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 40px;
  margin: 0 auto 20px;
}

.success-header h1 {
  font-size: 28px;
  color: #1a202c;
  margin: 0 0 12px;
}

.subtitle {
  color: #718096;
  font-size: 16px;
  margin: 0;
}

/* Sections */
.section {
  background: white;
  border-radius: 16px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.08);
  padding: 24px;
  margin-bottom: 24px;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid #e2e8f0;
}

.section-icon {
  font-size: 24px;
}

.section-header h2 {
  font-size: 20px;
  color: #2d3748;
  margin: 0;
}

/* Summaries */
.summaries-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.summary-card {
  background: #f7fafc;
  border-radius: 12px;
  padding: 16px;
  border-left: 4px solid #667eea;
}

.summary-header {
  margin-bottom: 12px;
}

.part-badge {
  background: #667eea;
  color: white;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;
}

.summary-content p {
  color: #4a5568;
  line-height: 1.6;
  margin: 0;
}

/* Evidence */
.evidence-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.evidence-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: #f7fafc;
  border-radius: 8px;
}

.evidence-number {
  background: #667eea;
  color: white;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
}

.evidence-name {
  color: #4a5568;
}

/* Case Section */
.case-created-info {
  text-align: center;
  padding: 20px;
}

.case-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  border-radius: 20px;
  font-weight: 600;
  margin-bottom: 12px;
}

.case-badge.success {
  background: #c6f6d5;
  color: #276749;
}

.case-creation-options {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.option-card {
  border: 2px solid #e2e8f0;
  border-radius: 12px;
  padding: 20px;
  cursor: pointer;
  transition: all 0.2s;
}

.option-card:hover {
  border-color: #667eea;
}

.option-card.selected {
  border-color: #667eea;
  background: #f0f4ff;
}

.option-label {
  display: flex;
  gap: 16px;
  cursor: pointer;
}

.option-label input {
  width: 20px;
  height: 20px;
  accent-color: #667eea;
}

.option-content {
  flex: 1;
}

.option-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: #2d3748;
  margin-bottom: 8px;
}

.option-desc {
  color: #718096;
  font-size: 14px;
  margin: 0;
}

.case-details-form {
  padding: 20px;
  background: #f7fafc;
  border-radius: 12px;
}

.form-group {
  margin-bottom: 16px;
}

.form-group:last-child {
  margin-bottom: 0;
}

.form-group label {
  display: block;
  font-weight: 600;
  color: #4a5568;
  margin-bottom: 8px;
}

.form-input, .form-select {
  width: 100%;
  padding: 12px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 14px;
}

.form-input:focus, .form-select:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.recommendation-hint {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: #fffbeb;
  border-radius: 8px;
  color: #b7791f;
  font-size: 14px;
}

.hint-icon {
  font-size: 18px;
}

/* Documents Section */
.generated-docs {
  margin-bottom: 24px;
  padding: 16px;
  background: #f0fff4;
  border-radius: 12px;
}

.generated-docs h3 {
  font-size: 16px;
  color: #276749;
  margin: 0 0 12px;
}

.docs-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.doc-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  background: white;
  border-radius: 8px;
}

.doc-icon {
  font-size: 20px;
}

.doc-name {
  flex: 1;
  color: #4a5568;
}

.selection-hint {
  color: #718096;
  margin-bottom: 16px;
}

.templates-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 16px;
}

.template-card {
  border: 2px solid #e2e8f0;
  border-radius: 12px;
  padding: 16px;
  cursor: pointer;
  transition: all 0.2s;
}

.template-card:hover {
  border-color: #667eea;
}

.template-card.selected {
  border-color: #667eea;
  background: #f0f4ff;
}

.template-card input {
  display: none;
}

.template-name {
  font-weight: 600;
  color: #2d3748;
  margin-bottom: 4px;
}

.template-desc {
  color: #718096;
  font-size: 13px;
  margin-bottom: 8px;
}

.template-code {
  color: #a0aec0;
  font-size: 12px;
}

/* Actions */
.actions-section {
  display: flex;
  gap: 16px;
  justify-content: center;
  margin-top: 32px;
}

.btn {
  padding: 12px 24px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  border: none;
}

.btn-primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.btn-outline {
  background: white;
  color: #667eea;
  border: 2px solid #667eea;
}

.btn-outline:hover {
  background: #f7fafc;
}

.btn-large {
  padding: 16px 32px;
  font-size: 16px;
}

.btn-sm {
  padding: 6px 12px;
  font-size: 12px;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Finalization Result */
.finalization-result {
  margin-top: 24px;
  background: white;
  border-radius: 16px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.08);
  overflow: hidden;
}

.result-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 24px;
}

.result-header.success {
  background: #c6f6d5;
  color: #276749;
}

.result-header.error {
  background: #fed7d7;
  color: #c53030;
}

.result-icon {
  font-size: 24px;
}

.result-header h3 {
  margin: 0;
  font-size: 18px;
}

.result-details {
  padding: 20px 24px;
}

.result-details p {
  margin: 0 0 12px;
  color: #4a5568;
  display: flex;
  align-items: center;
  gap: 8px;
}

.error-text {
  color: #c53030;
}

/* Responsive */
@media (max-width: 768px) {
  .completion-page {
    padding: 20px 16px;
  }
  
  .success-header {
    padding: 24px;
  }
  
  .success-header h1 {
    font-size: 24px;
  }
  
  .section {
    padding: 16px;
  }
  
  .templates-grid {
    grid-template-columns: 1fr;
  }
  
  .actions-section {
    flex-direction: column;
  }
  
  .actions-section .btn {
    width: 100%;
  }
}
</style>
