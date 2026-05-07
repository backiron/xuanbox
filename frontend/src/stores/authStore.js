import { defineStore } from 'pinia'
import { authApi } from '../api/authApi'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null,
    accessToken: localStorage.getItem('xb_access_token'),
    refreshToken: localStorage.getItem('xb_refresh_token')
  }),
  actions: {
    setTokens(tokens) {
      this.accessToken = tokens.access_token
      this.refreshToken = tokens.refresh_token
      localStorage.setItem('xb_access_token', tokens.access_token)
      localStorage.setItem('xb_refresh_token', tokens.refresh_token)
    },
    async login(payload) {
      const response = await authApi.login(payload)
      this.setTokens(response.data.data)
      await this.loadMe()
    },
    async loadMe() {
      if (!this.accessToken) return
      try {
        const response = await authApi.me()
        this.user = response.data.data
        this.accessToken = localStorage.getItem('xb_access_token')
        this.refreshToken = localStorage.getItem('xb_refresh_token')
      } catch (error) {
        this.logoutLocal()
      }
    },
    logoutLocal() {
      this.user = null
      this.accessToken = null
      this.refreshToken = null
      localStorage.removeItem('xb_access_token')
      localStorage.removeItem('xb_refresh_token')
    }
  }
})
