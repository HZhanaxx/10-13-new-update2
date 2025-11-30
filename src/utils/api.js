import axios from 'axios'
import DOMPurify from 'dompurify'
import { useAuthStore } from '@/stores/auth'
import router from '@/router'

// Create axios instance with security configurations
const apiClient = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
  // Security: prevent CSRF attacks by sending credentials
  withCredentials: true,
})

// Request rate limiting tracker (client-side)
const requestTracker = new Map()
const RATE_LIMIT_WINDOW = 60000 // 1 minute
const MAX_REQUESTS = 60 // 60 requests per minute

// Request interceptor for security
apiClient.interceptors.request.use(
  (config) => {
    // Add JWT token to requests
    const authStore = useAuthStore()
    const token = authStore.token
    
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }

    // Client-side rate limiting check
    const endpoint = config.url
    const now = Date.now()
    
    if (!requestTracker.has(endpoint)) {
      requestTracker.set(endpoint, [])
    }
    
    const requests = requestTracker.get(endpoint)
    const recentRequests = requests.filter(time => now - time < RATE_LIMIT_WINDOW)
    
    if (recentRequests.length >= MAX_REQUESTS) {
      console.warn(`Rate limit exceeded for ${endpoint}`)
      return Promise.reject(new Error('请求过于频繁，请稍后再试'))
    }
    
    recentRequests.push(now)
    requestTracker.set(endpoint, recentRequests)

    // CRITICAL: Don't sanitize or modify FormData!
    const isFormData = config.data instanceof FormData
    
    // Only sanitize JSON data, NOT FormData
    if (!isFormData && config.data && typeof config.data === 'object') {
      config.data = sanitizeObject(config.data)
    }
    
    // CRITICAL: Remove Content-Type header for FormData
    // Let browser set it with proper boundary
    if (isFormData) {
      delete config.headers['Content-Type']
    }

    // Add request timestamp for replay attack prevention
    config.headers['X-Request-Time'] = Date.now().toString()

    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor for security and error handling
apiClient.interceptors.response.use(
  (response) => {
    // Skip sanitization for Blob responses (file downloads/views)
    if (response.data instanceof Blob) {
      console.log('🔵 Axios interceptor: Blob response detected', {
        size: response.data.size,
        type: response.data.type,
        url: response.config.url
      })
      return response
    }
    
    // Sanitize response data to prevent XSS
    if (response.data && typeof response.data === 'object') {
      response.data = sanitizeObject(response.data)
    }
    return response
  },
  async (error) => {
    const originalRequest = error.config

    // Handle 401 Unauthorized - SIMPLE: just logout, no refresh attempts
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true
      
      // Don't try to refresh - just check if we should logout
      const isAuthEndpoint = originalRequest.url?.includes('/auth/')
      
      if (!isAuthEndpoint) {
        // Non-auth endpoint returned 401 = token expired, logout
        const authStore = useAuthStore()
        authStore.clearAuth()
        router.push('/login')
      }
      
      return Promise.reject(error)
    }

    // Handle 403 Forbidden
    if (error.response?.status === 403) {
      console.error('Access denied:', error.response.data)
      router.push('/unauthorized')
    }

    // Handle 429 Too Many Requests
    if (error.response?.status === 429) {
      console.error('Rate limit exceeded')
      return Promise.reject(new Error('请求过于频繁，请稍后再试'))
    }

    // Handle network errors
    if (!error.response) {
      console.error('Network error:', error)
      return Promise.reject(new Error('网络连接失败，请检查您的网络'))
    }

    return Promise.reject(error)
  }
)

// Sanitize object recursively to prevent XSS
function sanitizeObject(obj) {
  if (typeof obj !== 'object' || obj === null) {
    if (typeof obj === 'string') {
      return DOMPurify.sanitize(obj, { 
        ALLOWED_TAGS: [],
        ALLOWED_ATTR: []
      })
    }
    return obj
  }

  if (Array.isArray(obj)) {
    return obj.map(item => sanitizeObject(item))
  }

  const sanitized = {}
  for (const key in obj) {
    if (Object.prototype.hasOwnProperty.call(obj, key)) {
      sanitized[key] = sanitizeObject(obj[key])
    }
  }
  return sanitized
}

// Security utilities
export const security = {
  // Validate email format
  isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    return emailRegex.test(email)
  },

  // Validate phone number (Chinese format)
  isValidPhone(phone) {
    const phoneRegex = /^1[3-9]\d{9}$/
    return phoneRegex.test(phone)
  },

  // Validate password strength
  isStrongPassword(password) {
    // At least 8 characters, 1 uppercase, 1 lowercase, 1 number, 1 special char
    const strongPasswordRegex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$/
    return strongPasswordRegex.test(password)
  },

  // Sanitize HTML input
  sanitizeHtml(html) {
    return DOMPurify.sanitize(html, {
      ALLOWED_TAGS: ['b', 'i', 'u', 'strong', 'em', 'br', 'p'],
      ALLOWED_ATTR: []
    })
  },

  // Sanitize plain text (remove all HTML)
  sanitizeText(text) {
    return DOMPurify.sanitize(text, {
      ALLOWED_TAGS: [],
      ALLOWED_ATTR: []
    })
  },

  // Generate CSRF token (for additional protection)
  generateCSRFToken() {
    const array = new Uint8Array(32)
    crypto.getRandomValues(array)
    return Array.from(array, byte => byte.toString(16).padStart(2, '0')).join('')
  },

  // Validate UUID format
  isValidUUID(uuid) {
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i
    return uuidRegex.test(uuid)
  },

  // Prevent clickjacking
  preventClickjacking() {
    if (window.top !== window.self) {
      window.top.location = window.self.location
    }
  }
}

// Initialize clickjacking protection
security.preventClickjacking()

export default apiClient
