import { defineStore } from 'pinia'
import router from '../router'
import { loginApi, meApi } from '../api/auth'
import type { LoginPayload, UserInfo } from '../types'

interface AuthState {
  token: string
  user: UserInfo | null
  loading: boolean
  initialized: boolean
}

export const useAuthStore = defineStore('auth', {
  state: (): AuthState => ({
    token: localStorage.getItem('token') || '',
    user: null,
    loading: false,
    initialized: false,
  }),
  getters: {
    isAuthenticated: (state) => Boolean(state.token),
  },
  actions: {
    async initialize() {
      if (this.initialized) {
        return
      }

      this.initialized = true

      if (this.token) {
        try {
          await this.fetchProfile()
        } catch {
          this.clearAuth()
        }
      }
    },
    async login(payload: LoginPayload) {
      this.loading = true
      try {
        const result = await loginApi(payload)
        this.token = result.access_token
        localStorage.setItem('token', result.access_token)
        await this.fetchProfile()
      } finally {
        this.loading = false
      }
    },
    async fetchProfile() {
      const user = await meApi()
      this.user = user
      return user
    },
    clearAuth() {
      this.token = ''
      this.user = null
      localStorage.removeItem('token')
    },
    async logout() {
      this.clearAuth()
      await router.push('/login')
    },
  },
})
