<template>
  <div class="flex min-h-screen bg-slate-50/50">
    <Sidebar />
    
    <main class="flex-1 p-8 ml-64 overflow-y-auto">
      <div class="max-w-3xl mx-auto space-y-6">
        
        <div class="flex items-center gap-2 text-sm text-muted-foreground mb-2">
          <span class="hover:text-primary cursor-pointer transition-colors" @click="$router.push('/dashboard')">首页</span>
          <span>/</span>
          <span class="text-foreground font-medium">新建案件</span>
        </div>

        <div class="flex items-center justify-between">
          <h1 class="text-3xl font-bold tracking-tight text-foreground">发布新案件</h1>
          <Button variant="ghost" @click="$router.go(-1)">取消</Button>
        </div>

        <Card class="border-none shadow-md">
          <CardHeader>
            <div class="flex items-center gap-2">
              <div class="p-2 bg-primary/10 rounded-lg text-primary">
                <FilePlus class="w-5 h-5" />
              </div>
              <div>
                <CardTitle>基本信息</CardTitle>
                <CardDescription>请尽可能详细地描述您的案件情况，以便律师评估。</CardDescription>
              </div>
            </div>
          </CardHeader>
          
          <CardContent>
            <form @submit.prevent="submitCase" class="space-y-6">
              
              <div class="space-y-2">
                <Label for="title">案件标题 <span class="text-red-500">*</span></Label>
                <Input 
                  id="title" 
                  v-model="form.title" 
                  placeholder="例如：房屋租赁合同违约纠纷" 
                  required 
                  class="bg-slate-50 border-slate-200 focus:bg-white transition-colors"
                />
              </div>

              <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div class="space-y-2">
                  <Label for="category">案件类别 <span class="text-red-500">*</span></Label>
                  <Select v-model="form.case_category" id="category">
                    <option value="" disabled>请选择类别</option>
                    <option value="民事诉讼">民事诉讼</option>
                    <option value="刑事诉讼">刑事诉讼</option>
                    <option value="劳动纠纷">劳动纠纷</option>
                    <option value="合同纠纷">合同纠纷</option>
                    <option value="知识产权">知识产权</option>
                    <option value="交通事故">交通事故</option>
                  </Select>
                </div>
                <div class="space-y-2">
                  <Label for="budget">预算 (CNY)</Label>
                  <div class="relative">
                    <span class="absolute left-3 top-2.5 text-muted-foreground font-medium">¥</span>
                    <Input 
                      id="budget" 
                      v-model.number="form.budget_cny" 
                      type="number" 
                      class="pl-8 bg-slate-50 border-slate-200 focus:bg-white" 
                      placeholder="0" 
                      min="0" 
                    />
                  </div>
                </div>
              </div>

              <div class="space-y-3">
                <Label>优先级</Label>
                <div class="grid grid-cols-4 gap-3">
                  <div 
                    v-for="p in priorities" 
                    :key="p.value" 
                    class="flex flex-col items-center justify-center p-3 border rounded-lg cursor-pointer transition-all hover:bg-slate-50"
                    :class="form.priority === p.value ? `border-${p.color}-500 bg-${p.color}-50 ring-1 ring-${p.color}-500` : 'border-slate-200'"
                    @click="form.priority = p.value"
                  >
                    <div :class="`w-2 h-2 rounded-full bg-${p.color}-500 mb-1`"></div>
                    <span class="text-xs font-medium">{{ p.label }}</span>
                  </div>
                </div>
              </div>

              <div class="space-y-2">
                <Label for="desc">案件详情 <span class="text-red-500">*</span></Label>
                <Textarea 
                  id="desc" 
                  v-model="form.description" 
                  rows="8" 
                  placeholder="请详细描述案件的经过、时间、地点及相关人员..." 
                  required 
                  class="bg-slate-50 border-slate-200 focus:bg-white resize-none"
                />
                <p class="text-xs text-muted-foreground text-right">{{ form.description.length }} 字</p>
              </div>

            </form>
          </CardContent>
          
          <CardFooter class="flex justify-end border-t bg-slate-50/50 p-6 rounded-b-xl">
            <Button size="lg" @click="submitCase" :loading="isSubmitting" class="w-full md:w-auto px-8">
              <Send class="w-4 h-4 mr-2" /> 发布案件
            </Button>
          </CardFooter>
        </Card>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import Sidebar from '@/components/Sidebar.vue'
import apiClient from '@/utils/api'
import { 
  Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter,
  Input, Label, Button, Textarea, Select
} from '@/components/ui'
import { FilePlus, Send } from 'lucide-vue-next'

const router = useRouter()
const isSubmitting = ref(false)

const form = ref({
  title: '',
  case_category: '',
  budget_cny: null,
  priority: 'medium',
  description: ''
})

const priorities = [
  { value: 'low', label: '低', color: 'green' },
  { value: 'medium', label: '中', color: 'blue' },
  { value: 'high', label: '高', color: 'orange' },
  { value: 'urgent', label: '紧急', color: 'red' }
]

const submitCase = async () => {
  if (!form.value.title || !form.value.case_category || !form.value.description) {
    alert('请填写所有必填项')
    return
  }

  isSubmitting.value = true
  try {
    await apiClient.post('/cases/', form.value)
    router.push('/dashboard')
  } catch (error) {
    console.error('Submit failed:', error)
    alert('提交失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    isSubmitting.value = false
  }
}
</script>