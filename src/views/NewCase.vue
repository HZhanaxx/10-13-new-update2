<template>
  <div class="page-container">
    <Sidebar />
    <div class="main-content">
      <div class="content-wrapper">
        <header class="page-header">
          <button class="btn btn-secondary btn-icon" @click="$router.go(-1)">
             ← 返回
          </button>
          <h1>新建案件</h1>
        </header>

        <div class="glass-card form-card">
          <form @submit.prevent="submitCase">
            <div class="form-section">
              <div class="section-title">
                <span class="icon">📝</span>
                <h3>基本信息</h3>
              </div>
              
              <div class="form-group">
                <label>案件标题</label>
                <input v-model="form.title" type="text" class="input" placeholder="例如：房屋租赁合同违约纠纷" required />
              </div>
              
              <div class="form-row">
                <div class="form-group">
                  <label>案件类别</label>
                  <select v-model="form.case_category" class="input" required>
                    <option value="">请选择类别</option>
                    <option value="民事诉讼">民事诉讼</option>
                    <option value="刑事诉讼">刑事诉讼</option>
                    <option value="劳动纠纷">劳动纠纷</option>
                    <option value="合同纠纷">合同纠纷</option>
                    <option value="知识产权">知识产权</option>
                  </select>
                </div>
                <div class="form-group">
                  <label>预算 (人民币)</label>
                  <input v-model.number="form.budget_cny" type="number" class="input" placeholder="0" min="0" />
                </div>
              </div>

               <div class="form-group">
                <label>优先级</label>
                <select v-model="form.priority" class="input">
                  <option value="low">低</option>
                  <option value="medium">中</option>
                  <option value="high">高</option>
                  <option value="urgent">紧急</option>
                </select>
              </div>
            </div>

            <div class="form-section">
              <div class="section-title">
                <span class="icon">📄</span>
                <h3>详细描述</h3>
              </div>
              <div class="form-group">
                <label>案件详情</label>
                <textarea v-model="form.description" class="input textarea" rows="6" placeholder="请详细描述案件的经过、时间、地点及相关人员..." required></textarea>
              </div>
            </div>

            <div class="form-actions">
              <button type="button" class="btn btn-secondary" @click="$router.push('/dashboard')">取消</button>
              <button type="submit" class="btn btn-primary" :disabled="isSubmitting">
                {{ isSubmitting ? '提交中...' : '发布案件' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import Sidebar from '@/components/Sidebar.vue'
import apiClient from '@/utils/api'

const router = useRouter()
const isSubmitting = ref(false)

const form = ref({
  title: '',
  case_category: '',
  budget_cny: null,
  priority: 'medium',
  description: ''
})

const submitCase = async () => {
  isSubmitting.value = true
  try {
    // This connects to your DB via your API
    await apiClient.post('/cases/', form.value)
    alert('案件发布成功！')
    router.push('/dashboard')
  } catch (error) {
    console.error('Submit failed:', error)
    alert('提交失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    isSubmitting.value = false
  }
}
</script>

<style scoped>
.content-wrapper { max-width: 800px; margin: 0 auto; animation: slideUp 0.6s cubic-bezier(0.16, 1, 0.3, 1); }
.page-header { margin-bottom: 32px; display: flex; align-items: center; gap: 16px; }
.page-header h1 { font-size: 28px; font-weight: 700; color: #2d3748; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }

.form-card { padding: 40px; }
.form-section { margin-bottom: 40px; }
.section-title { display: flex; align-items: center; gap: 10px; margin-bottom: 24px; }
.section-title .icon { font-size: 24px; background: #f3f4f6; padding: 8px; border-radius: 8px; }
.section-title h3 { font-size: 18px; color: #4a5568; font-weight: 600; }

.form-group { margin-bottom: 24px; }
.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
label { display: block; margin-bottom: 8px; font-weight: 500; color: #4a5568; font-size: 14px; }
.textarea { resize: vertical; min-height: 120px; }
.form-actions { display: flex; justify-content: flex-end; gap: 16px; margin-top: 40px; padding-top: 24px; border-top: 1px solid rgba(0,0,0,0.05); }

@keyframes slideUp { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
</style>