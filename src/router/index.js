import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

// Lazy Load All Components
const Login = () => import('@/views/Login.vue')
const Dashboard = () => import('@/views/Dashboard.vue')
const NewCase = () => import('@/views/NewCase.vue')
const LangGraphQuestionnaire = () => import('@/views/LangGraphQuestionnaire.vue')
const QuestionnaireCompletion = () => import('@/views/QuestionnaireCompletion.vue')
const CaseDetail = () => import('@/views/CaseDetail.vue')
const Profile = () => import('@/views/Profile.vue')

// Professional Views
const ProfessionalDashboard = () => import('@/views/ProfessionalDashboard.vue')
const ProfessionalVerification = () => import('@/views/ProfessionalVerification.vue')
const ProfessionalProfile = () => import('@/views/ProfessionalProfile.vue')
const CasePool = () => import('@/views/CasePool.vue')
const MyCases = () => import('@/views/professional/MyCases.vue')

// Admin Views
const AdminDashboard = () => import('@/views/AdminDashboard.vue')
const UserManagement = () => import('@/views/admin/UserManagement.vue')
const CaseMonitoring = () => import('@/views/admin/CaseMonitoring.vue')
const VerificationManagement = () => import('@/views/VerificationManagement.vue')

// Error Pages
const NotFound = () => import('@/views/NotFound.vue')
const Unauthorized = () => import('@/views/Unauthorized.vue')

const routes = [
  { path: '/', redirect: '/login' },
  
  // Auth
  {
    path: '/login',
    name: 'Login',
    component: Login,
    meta: { requiresAuth: false, title: '登录 - 智能法律助手' }
  },

  // User Routes
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: Dashboard,
    meta: { requiresAuth: true, roles: ['user'], title: '我的案件 - 智能法律助手' }
  },
  {
    path: '/cases/new',
    name: 'NewCase',
    component: NewCase,
    meta: { requiresAuth: true, roles: ['user'], title: '新建案件 - 智能法律助手' }
  },
  {
    path: '/questionnaire/:sessionId',
    name: 'Questionnaire',
    component: LangGraphQuestionnaire,
    meta: { requiresAuth: true, roles: ['user'], title: '智能咨询 - 智能法律助手' },
    props: true
  },
  {
    path: '/questionnaire/:sessionId/complete',
    name: 'QuestionnaireCompletion',
    component: QuestionnaireCompletion,
    meta: { requiresAuth: true, roles: ['user'], title: '问卷完成 - 智能法律助手' },
    props: true
  },
  {
    path: '/case/:id',
    name: 'CaseDetail',
    component: CaseDetail,
    meta: { requiresAuth: true, title: '案件详情 - 智能法律助手' },
    props: true
  },
  {
    path: '/profile',
    name: 'Profile',
    component: Profile,
    meta: { requiresAuth: true, title: '个人资料 - 智能法律助手' }
  },

  // Professional Routes
  {
    path: '/professional',
    name: 'ProfessionalDashboard',
    component: ProfessionalDashboard,
    meta: { requiresAuth: true, roles: ['professional'], title: '工作台 - 智能法律助手' }
  },
  {
    path: '/professional/verification',
    name: 'ProfessionalVerification',
    component: ProfessionalVerification,
    meta: { requiresAuth: true, roles: ['professional'], title: '专业认证 - 智能法律助手' }
  },
  {
    path: '/professional/profile',
    name: 'ProfessionalProfile',
    component: ProfessionalProfile,
    meta: { requiresAuth: true, roles: ['professional'], title: '专业资料 - 智能法律助手' }
  },
  {
    path: '/professional/my-cases',
    name: 'MyCases',
    component: MyCases,
    meta: { requiresAuth: true, roles: ['professional'], title: '我的案件 - 智能法律助手' }
  },
  {
    path: '/case-pool',
    name: 'CasePool',
    component: CasePool,
    meta: { requiresAuth: true, roles: ['professional'], title: '案件池 - 智能法律助手' }
  },

  // Admin Routes
  {
    path: '/admin',
    name: 'AdminDashboard',
    component: AdminDashboard,
    meta: { requiresAuth: true, roles: ['admin'], title: '管理面板 - 智能法律助手' }
  },
  {
    path: '/admin/users',
    name: 'UserManagement',
    component: UserManagement,
    meta: { requiresAuth: true, roles: ['admin'], title: '用户管理 - 智能法律助手' }
  },
  {
    path: '/admin/cases',
    name: 'CaseMonitoring',
    component: CaseMonitoring,
    meta: { requiresAuth: true, roles: ['admin'], title: '案件监控 - 智能法律助手' }
  },
  {
    path: '/admin/verifications',
    name: 'VerificationManagement',
    component: VerificationManagement,
    meta: { requiresAuth: true, roles: ['admin'], title: '认证审核 - 智能法律助手' }
  },

  // Error Pages
  {
    path: '/unauthorized',
    name: 'Unauthorized',
    component: Unauthorized,
    meta: { title: '无权访问 - 智能法律助手' }
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: NotFound,
    meta: { title: '页面未找到 - 智能法律助手' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(to, from, savedPosition) {
    return savedPosition || { top: 0 }
  }
})

// Navigation Guards
router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()
  document.title = to.meta.title || '智能法律助手'

  if (to.meta.requiresAuth) {
    if (!authStore.isAuthenticated) {
      await authStore.init()
      if (!authStore.isAuthenticated) {
        return next({ name: 'Login', query: { redirect: to.fullPath } })
      }
    }

    if (to.meta.roles && !to.meta.roles.includes(authStore.userRole)) {
      return next({ name: 'Unauthorized' })
    }
  }

  if (to.name === 'Login' && authStore.isAuthenticated) {
    const role = authStore.userRole
    if (role === 'admin') return next({ name: 'AdminDashboard' })
    if (role === 'professional') return next({ name: 'ProfessionalDashboard' })
    return next({ name: 'Dashboard' })
  }

  next()
})

export default router
