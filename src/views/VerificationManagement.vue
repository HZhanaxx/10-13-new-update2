<template>
  <div class="flex min-h-screen bg-slate-50/50">
    <Sidebar />
    
    <main class="flex-1 p-8 ml-64 overflow-y-auto">
      <div class="max-w-7xl mx-auto space-y-8">
        
        <div class="flex flex-col gap-1">
          <h1 class="text-3xl font-bold tracking-tight text-foreground">认证审核</h1>
          <p class="text-muted-foreground">审批律师和专业人员的入驻申请与资质文件</p>
        </div>

        <div class="grid gap-4 md:grid-cols-3">
          <Card>
            <CardHeader class="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle class="text-sm font-medium">待审核</CardTitle>
              <Clock class="h-4 w-4 text-amber-500" />
            </CardHeader>
            <CardContent>
              <div class="text-2xl font-bold text-amber-600">{{ stats.pending || 0 }}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader class="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle class="text-sm font-medium">已通过</CardTitle>
              <CheckCircle2 class="h-4 w-4 text-emerald-500" />
            </CardHeader>
            <CardContent>
              <div class="text-2xl font-bold text-emerald-600">{{ stats.approved || 0 }}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader class="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle class="text-sm font-medium">已拒绝</CardTitle>
              <XCircle class="h-4 w-4 text-red-500" />
            </CardHeader>
            <CardContent>
              <div class="text-2xl font-bold text-red-600">{{ stats.rejected || 0 }}</div>
            </CardContent>
          </Card>
        </div>

        <Tabs v-model="filter" class="space-y-6">
          <TabsList>
            <TabsTrigger value="pending" @click="loadVerifications('pending')">待审核</TabsTrigger>
            <TabsTrigger value="approved" @click="loadVerifications('approved')">已通过</TabsTrigger>
            <TabsTrigger value="rejected" @click="loadVerifications('rejected')">已拒绝</TabsTrigger>
            <TabsTrigger value="all" @click="loadVerifications(null)">全部</TabsTrigger>
          </TabsList>

          <div v-if="loading" class="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            <Skeleton v-for="i in 6" :key="i" class="h-[200px] rounded-xl" />
          </div>

          <div v-else-if="verifications.length > 0" class="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            <transition-group name="fade">
              <Card 
                v-for="item in verifications" 
                :key="item.request_uuid" 
                class="group cursor-pointer hover:shadow-md transition-all border-l-4"
                :class="getBorderClass(item.status)"
                @click="viewDetail(item)"
              >
                <CardHeader class="pb-3">
                  <div class="flex justify-between items-start">
                    <div class="space-y-1">
                      <CardTitle class="text-base">{{ item.full_name }}</CardTitle>
                      <CardDescription class="line-clamp-1">{{ item.law_firm_name || '个人执业' }}</CardDescription>
                    </div>
                    <Badge :class="getStatusBadgeClass(item.status)">{{ getStatusText(item.status) }}</Badge>
                  </div>
                </CardHeader>
                <CardContent class="pb-3 text-sm space-y-2">
                  <div class="flex items-center text-muted-foreground">
                    <Briefcase class="w-3.5 h-3.5 mr-2" />
                    <span>从业 {{ item.years_of_experience || 0 }} 年</span>
                  </div>
                  <div class="flex items-center text-muted-foreground">
                    <FileText class="w-3.5 h-3.5 mr-2" />
                    <span>执业证号: {{ item.license_number }}</span>
                  </div>
                  <div class="flex flex-wrap gap-1 mt-2">
                    <span v-for="area in parseSpecialtyAreas(item.specialty_areas).slice(0, 3)" :key="area" 
                      class="bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded text-xs">
                      {{ area }}
                    </span>
                    <span v-if="parseSpecialtyAreas(item.specialty_areas).length > 3" class="text-xs text-muted-foreground pt-0.5">...</span>
                  </div>
                </CardContent>
                <CardFooter class="pt-3 border-t bg-slate-50/50 rounded-b-xl flex justify-between text-xs text-muted-foreground">
                  <span>{{ formatDate(item.created_at) }}</span>
                  <span class="flex items-center gap-1" v-if="item.document_count">
                    <Paperclip class="w-3 h-3" /> {{ item.document_count }} 附件
                  </span>
                </CardFooter>
              </Card>
            </transition-group>
          </div>

          <div v-else class="flex flex-col items-center justify-center py-20 text-center border-2 border-dashed rounded-xl bg-slate-50/50">
            <div class="p-4 bg-white rounded-full shadow-sm mb-4">
              <Search class="w-8 h-8 text-muted-foreground/50" />
            </div>
            <h3 class="text-lg font-medium">暂无数据</h3>
            <p class="text-muted-foreground">当前筛选条件下没有认证申请</p>
          </div>
        </Tabs>

      </div>
    </main>

    <Dialog :open="showDetailModal" @close="closeDetailModal">
      <div v-if="selectedVerification" class="space-y-6 max-h-[85vh] overflow-y-auto p-1">
        <div class="flex items-start justify-between">
          <div>
            <h2 class="text-2xl font-bold flex items-center gap-2">
              {{ selectedVerification.full_name }}
              <Badge :class="getStatusBadgeClass(selectedVerification.status)">
                {{ getStatusText(selectedVerification.status) }}
              </Badge>
            </h2>
            <p class="text-muted-foreground mt-1">{{ selectedVerification.law_firm_name || '个人执业' }}</p>
          </div>
          <div class="text-right text-sm text-muted-foreground">
            <p>申请时间: {{ formatDate(selectedVerification.created_at) }}</p>
            <p>执业年限: {{ selectedVerification.years_of_experience }} 年</p>
          </div>
        </div>

        <Separator />

        <div class="grid md:grid-cols-2 gap-6">
          <div class="space-y-4">
            <h3 class="font-semibold flex items-center gap-2 text-sm uppercase tracking-wider text-muted-foreground">
              <User class="w-4 h-4" /> 基本信息
            </h3>
            <div class="space-y-3 text-sm">
              <div class="flex justify-between border-b border-dashed pb-1">
                <span class="text-muted-foreground">执业证号</span>
                <span class="font-mono">{{ selectedVerification.license_number }}</span>
              </div>
              <div class="flex justify-between border-b border-dashed pb-1">
                <span class="text-muted-foreground">所在地</span>
                <span>{{ selectedVerification.province_name }} {{ selectedVerification.city_name }}</span>
              </div>
              <div class="flex justify-between border-b border-dashed pb-1">
                <span class="text-muted-foreground">联系电话</span>
                <span>{{ selectedVerification.phone || '未提供' }}</span>
              </div>
            </div>
          </div>

          <div class="space-y-4">
            <h3 class="font-semibold flex items-center gap-2 text-sm uppercase tracking-wider text-muted-foreground">
              <Banknote class="w-4 h-4" /> 服务定价
            </h3>
            <div class="grid grid-cols-2 gap-3">
              <div class="bg-slate-50 p-3 rounded border text-center">
                <div class="text-xs text-muted-foreground">咨询费</div>
                <div class="font-bold text-emerald-600">¥{{ selectedVerification.consultation_fee_cny || 0 }}</div>
              </div>
              <div class="bg-slate-50 p-3 rounded border text-center">
                <div class="text-xs text-muted-foreground">时薪</div>
                <div class="font-bold text-blue-600">¥{{ selectedVerification.hourly_rate_cny || 0 }}</div>
              </div>
            </div>
          </div>
        </div>

        <div class="space-y-4">
          <div class="space-y-2">
            <h3 class="font-semibold text-sm">专业领域</h3>
            <div class="flex flex-wrap gap-2">
              <Badge v-for="area in parseSpecialtyAreas(selectedVerification.specialty_areas)" :key="area" variant="secondary">
                {{ area }}
              </Badge>
            </div>
          </div>
          
          <div v-if="selectedVerification.education_background" class="space-y-2">
            <h3 class="font-semibold text-sm">教育背景</h3>
            <p class="text-sm bg-slate-50 p-3 rounded border text-slate-700 whitespace-pre-wrap">{{ selectedVerification.education_background }}</p>
          </div>

          <div v-if="selectedVerification.bio" class="space-y-2">
            <h3 class="font-semibold text-sm">个人简介</h3>
            <p class="text-sm bg-slate-50 p-3 rounded border text-slate-700 whitespace-pre-wrap">{{ selectedVerification.bio }}</p>
          </div>
        </div>

        <div class="space-y-3" v-if="selectedVerification.documents?.length">
          <h3 class="font-semibold flex items-center gap-2 text-sm uppercase tracking-wider text-muted-foreground">
            <Paperclip class="w-4 h-4" /> 认证材料
          </h3>
          <div class="grid sm:grid-cols-2 gap-3">
            <div 
              v-for="doc in selectedVerification.documents" 
              :key="doc.document_id"
              class="flex items-center justify-between p-3 border rounded-lg hover:bg-slate-50 transition-colors group cursor-pointer"
              @click="viewDocument(doc)"
            >
              <div class="flex items-center gap-3 overflow-hidden">
                <div class="h-8 w-8 rounded bg-primary/10 flex items-center justify-center text-primary shrink-0">
                  <FileText class="w-4 h-4" />
                </div>
                <div class="min-w-0">
                  <p class="text-sm font-medium truncate">{{ doc.file_name }}</p>
                  <p class="text-xs text-muted-foreground">{{ formatFileSize(doc.file_size) }}</p>
                </div>
              </div>
              <Button variant="ghost" size="icon" class="opacity-0 group-hover:opacity-100">
                <Eye class="w-4 h-4" />
              </Button>
            </div>
          </div>
        </div>

        <div class="flex justify-end gap-3 pt-6 border-t" v-if="selectedVerification.status === 'pending'">
          <Button variant="outline" class="text-red-600 hover:text-red-700 hover:bg-red-50 border-red-200" @click="openRejectModal">
            <XCircle class="w-4 h-4 mr-2" /> 拒绝申请
          </Button>
          <Button class="bg-emerald-600 hover:bg-emerald-700" @click="approveVerification(selectedVerification)">
            <CheckCircle2 class="w-4 h-4 mr-2" /> 通过认证
          </Button>
        </div>
        
        <div v-else-if="selectedVerification.admin_notes" class="bg-slate-100 p-4 rounded-lg border">
          <h4 class="text-sm font-bold text-slate-700 mb-1">审核备注</h4>
          <p class="text-sm text-slate-600">{{ selectedVerification.admin_notes }}</p>
        </div>
      </div>
    </Dialog>

    <Dialog :open="showRejectModal" @close="showRejectModal = false">
      <div class="space-y-4">
        <div class="space-y-2">
          <h3 class="text-lg font-bold text-red-600">拒绝认证申请</h3>
          <p class="text-sm text-muted-foreground">请填写拒绝原因，以便申请人了解并修改资料。</p>
        </div>
        
        <Textarea 
          v-model="rejectNotes" 
          placeholder="例如: 执业证照片不清晰，请重新上传..." 
          rows="4"
          class="resize-none"
        />
        
        <div class="flex justify-end gap-3 pt-2">
          <Button variant="ghost" @click="showRejectModal = false">取消</Button>
          <Button variant="destructive" @click="confirmReject" :disabled="!rejectNotes.trim()">确认拒绝</Button>
        </div>
      </div>
    </Dialog>

    <Dialog :open="showImageViewer" @close="closeImageViewer" class="max-w-4xl p-0 overflow-hidden bg-black/90">
      <div class="relative flex items-center justify-center min-h-[50vh] p-4">
        <img v-if="currentImageUrl" :src="currentImageUrl" :alt="currentImage?.file_name" class="max-w-full max-h-[80vh] object-contain rounded" />
        <Button variant="ghost" size="icon" class="absolute top-2 right-2 text-white hover:bg-white/20" @click="closeImageViewer">
          <X class="w-6 h-6" />
        </Button>
        <Button v-if="currentImageUrl" class="absolute bottom-4 right-4" @click="downloadCurrentImage">
          下载原图
        </Button>
      </div>
    </Dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import Sidebar from '@/components/Sidebar.vue'
import apiClient from '@/utils/api'
import { 
  Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter,
  Button, Badge, Skeleton, Dialog, Textarea, Tabs, TabsList, TabsTrigger, Separator, Alert
} from '@/components/ui'
import { 
  Clock, CheckCircle2, XCircle, FileText, Briefcase, 
  Search, Paperclip, Eye, User, Banknote, AlertCircle, X
} from 'lucide-vue-next'

const filter = ref('pending')
const loading = ref(true)
const verifications = ref([])
const stats = ref({})
const showDetailModal = ref(false)
const selectedVerification = ref(null)
const showRejectModal = ref(false)
const rejectNotes = ref('')
const verificationToReject = ref(null)

// Image Viewer State
const showImageViewer = ref(false)
const currentImage = ref(null)
const currentImageUrl = ref(null)

const loadStats = async () => {
  try {
    const res = await apiClient.get('/admin/verifications/stats')
    stats.value = res.data
  } catch (e) { console.error(e) }
}

const loadVerifications = async (status = null) => {
  loading.value = true
  // If clicked from tab, update filter ref if needed, but 'status' arg overrides
  const queryStatus = status === null ? null : (status || filter.value)
  if (status === 'all') queryStatus = null; // handle 'all' explicitly if needed

  try {
    const params = {}
    if (status && status !== 'all') params.status_filter = status
    else if (filter.value && filter.value !== 'all' && !status) params.status_filter = filter.value

    const res = await apiClient.get('/admin/verifications', { params })
    verifications.value = res.data
  } catch (e) { console.error(e) } 
  finally { loading.value = false }
}

const viewDetail = async (item) => {
  try {
    const res = await apiClient.get(`/admin/verifications/${item.request_uuid}`)
    selectedVerification.value = res.data
    showDetailModal.value = true
  } catch (e) { alert('加载详情失败') }
}

const closeDetailModal = () => {
  showDetailModal.value = false
  selectedVerification.value = null
}

const approveVerification = async (v) => {
  if (!confirm(`确认通过 ${v.full_name} 的认证?`)) return
  try {
    await apiClient.post(`/admin/verifications/${v.request_uuid}/approve`, {
      status: 'approved', admin_notes: '认证通过'
    })
    closeDetailModal()
    await Promise.all([loadStats(), loadVerifications()])
  } catch (e) { alert('操作失败') }
}

const openRejectModal = () => {
  verificationToReject.value = selectedVerification.value
  rejectNotes.value = ''
  showRejectModal.value = true
  // closeDetailModal() // Keep detail open or close it? Let's keep detail modal in background logically but dialog implies modal-on-modal. 
  // Radix-vue dialogs stack well usually.
}

const confirmReject = async () => {
  try {
    await apiClient.post(`/admin/verifications/${verificationToReject.value.request_uuid}/reject`, {
      status: 'rejected', admin_notes: rejectNotes.value
    })
    showRejectModal.value = false
    closeDetailModal()
    await Promise.all([loadStats(), loadVerifications()])
  } catch (e) { alert('操作失败') }
}

// Helpers
const parseSpecialtyAreas = (areas) => {
  if (Array.isArray(areas)) return areas
  try { return JSON.parse(areas) } catch { return [] }
}

const formatDate = (d) => d ? new Date(d).toLocaleString('zh-CN', {month:'short', day:'numeric', hour:'2-digit', minute:'2-digit'}) : '-'
const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 B'
  const k = 1024, sizes = ['B', 'KB', 'MB'], i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
}

const getStatusBadgeClass = (s) => ({
  pending: 'bg-amber-100 text-amber-700 hover:bg-amber-100',
  approved: 'bg-emerald-100 text-emerald-700 hover:bg-emerald-100',
  rejected: 'bg-red-100 text-red-700 hover:bg-red-100'
}[s] || 'bg-slate-100')

const getBorderClass = (s) => ({
  pending: 'border-l-amber-400', approved: 'border-l-emerald-500', rejected: 'border-l-red-500'
}[s] || 'border-l-slate-200')

const getStatusText = (s) => ({ pending: '待审核', approved: '已通过', rejected: '已拒绝' }[s] || s)

// Document Viewer Logic
const viewDocument = async (doc) => {
  if (doc.mime_type?.includes('image')) {
    await viewImageInline(doc)
  } else {
    // Download/New Tab for PDF/Docs
    try {
      const res = await apiClient.get(`/admin/verifications/documents/${doc.document_id}`, { responseType: 'blob' })
      const url = window.URL.createObjectURL(res.data)
      window.open(url, '_blank')
      setTimeout(() => window.URL.revokeObjectURL(url), 10000)
    } catch (e) { alert('文件加载失败') }
  }
}

const viewImageInline = async (doc) => {
  try {
    currentImage.value = doc
    const res = await apiClient.get(`/admin/verifications/documents/${doc.document_id}`, { responseType: 'blob' })
    const reader = new FileReader()
    reader.onload = (e) => {
      currentImageUrl.value = e.target.result
      showImageViewer.value = true
    }
    reader.readAsDataURL(res.data)
  } catch (e) { alert('图片加载失败') }
}

const closeImageViewer = () => {
  showImageViewer.value = false
  currentImageUrl.value = null
}

const downloadCurrentImage = () => {
  if (currentImageUrl.value) {
    const a = document.createElement('a')
    a.href = currentImageUrl.value
    a.download = currentImage.value?.file_name || 'download'
    a.click()
  }
}

onMounted(() => {
  loadStats()
  loadVerifications()
})
</script>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.3s ease, transform 0.3s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; transform: translateY(10px); }
</style>