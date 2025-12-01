import { defineStore } from 'pinia'
import apiClient from '@/utils/api'
import Cookies from 'js-cookie'

// Secure token storage configuration
const TOKEN_KEY = 'access_token'
const REFRESH_TOKEN_KEY = 'refresh_token'
const USER_KEY = 'user_info'

// Token storage options with security flags
const COOKIE_OPTIONS = {
  secure: process.env.NODE_ENV === 'production', // HTTPS only in production
  sameSite: 'strict', // CSRF protection
  expires: 7 // 7 days
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: Cookies.get(TOKEN_KEY) || null,
    refreshTokenValue: Cookies.get(REFRESH_TOKEN_KEY) || null,  // RENAMED to avoid collision
    user: JSON.parse(localStorage.getItem(USER_KEY) || 'null'),
    isAuthenticated: false,
    isLoading: false,
  }),

  getters: {
    isAdmin: (state) => state.user?.role === 'admin',
    isProfessional: (state) => state.user?.role === 'professional',
    isUser: (state) => state.user?.role === 'user',
    userRole: (state) => state.user?.role,
    userName: (state) => state.user?.username,
    userEmail: (state) => state.user?.email,
    isVerified: (state) => state.user?.is_verified,
  },

  actions: {
    // Login with phone and verification code
    async login(phone, code) {
      try {
        this.isLoading = true
        const response = await apiClient.post('/auth/login/verify', {
          phone_number: phone,
          verification_code: code
        })

        const { token, user } = response.data
        const { access_token, refresh_token } = token
        
        // Store tokens securely
        this.setTokens(access_token, refresh_token)
        this.setUser(user)
        
        return { success: true, user }
      } catch (error) {
        console.error('Login failed:', error)
        return { 
          success: false, 
          error: error.response?.data?.detail || '登录失败，请重试' 
        }
      } finally {
        this.isLoading = false
      }
    },

    // Send verification code
    async sendVerificationCode(phone) {
      try {
        await apiClient.post('/auth/send-code', {
          phone_number: phone
        })
        return { success: true }
      } catch (error) {
        console.error('Send code failed:', error)
        return { 
          success: false, 
          error: error.response?.data?.detail || '发送验证码失败' 
        }
      }
    },

    // Register new user
    async register(userData) {
      try {
        this.isLoading = true
        const response = await apiClient.post('/auth/register', userData)
        
        const { token, user } = response.data
        const { access_token, refresh_token } = token
        
        // Store tokens securely
        this.setTokens(access_token, refresh_token)
        this.setUser(user)
        
        return { success: true, user }
      } catch (error) {
        console.error('Registration failed:', error)
        return { 
          success: false, 
          error: error.response?.data?.detail || '注册失败，请重试' 
        }
      } finally {
        this.isLoading = false
      }
    },

    // Get current user info
    async fetchUser() {
      try {
        const response = await apiClient.get('/auth/me')
        this.setUser(response.data)
        return { success: true, user: response.data }
      } catch (error) {
        console.error('Fetch user failed:', error)
        this.clearAuth()
        return { success: false }
      }
    },

    // Refresh access token - METHOD NAME FIXED
    async refreshToken() {
      if (!this.refreshTokenValue) {
        throw new Error('No refresh token available')
      }

      try {
        const response = await apiClient.post('/auth/token/refresh', {
          refresh_token: this.refreshTokenValue
        })

        const { access_token } = response.data
        this.setTokens(access_token, this.refreshTokenValue)
        
        return { success: true }
      } catch (error) {
        console.error('Token refresh failed:', error)
        this.clearAuth()
        throw error
      }
    },

    // Logout
    async logout() {
      try {
        if (this.token) {
          await apiClient.post('/auth/logout')
        }
      } catch (error) {
        console.error('Logout API failed:', error)
      } finally {
        this.clearAuth()
      }
    },

    // Set tokens securely
    setTokens(accessToken, refreshToken) {
      this.token = accessToken
      this.refreshTokenValue = refreshToken  // UPDATED
      this.isAuthenticated = true

      // Store in secure cookies
      Cookies.set(TOKEN_KEY, accessToken, COOKIE_OPTIONS)
      if (refreshToken) {
        Cookies.set(REFRESH_TOKEN_KEY, refreshToken, COOKIE_OPTIONS)
      }
    },

    // Set user info
    setUser(user) {
      this.user = user
      this.isAuthenticated = true
      
      // Store user info in localStorage (non-sensitive data only)
      localStorage.setItem(USER_KEY, JSON.stringify(user))
    },

    // Clear authentication
    clearAuth() {
      this.token = null
      this.refreshTokenValue = null  // UPDATED
      this.user = null
      this.isAuthenticated = false

      // Clear all stored data
      Cookies.remove(TOKEN_KEY)
      Cookies.remove(REFRESH_TOKEN_KEY)
      localStorage.removeItem(USER_KEY)
    },

    // Check if token is expired (optional - JWT check)
    isTokenExpired() {
      if (!this.token) return true

      try {
        const payload = JSON.parse(atob(this.token.split('.')[1]))
        const exp = payload.exp * 1000 // Convert to milliseconds
        return Date.now() >= exp
      } catch (error) {
        console.error('Token validation error:', error)
        return true
      }
    },

    // Initialize auth state on app load
    async init() {
      if (this.token && !this.isTokenExpired()) {
        await this.fetchUser()
      } else if (this.token && this.isTokenExpired() && this.refreshTokenValue) {
        try {
          await this.refreshToken()
          await this.fetchUser()
        } catch (error) {
          this.clearAuth()
        }
      } else {
        this.clearAuth()
      }
    }
  }
})
