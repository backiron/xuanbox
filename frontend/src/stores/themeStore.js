import { defineStore } from 'pinia'

export const useThemeStore = defineStore('theme', {
  state: () => ({
    mode: localStorage.getItem('xb_theme') || 'dark'
  }),
  actions: {
    setMode(mode) {
      this.mode = mode === 'light' ? 'light' : 'dark'
      localStorage.setItem('xb_theme', this.mode)
      document.documentElement.dataset.theme = this.mode
    },
    toggle() {
      this.setMode(this.mode === 'dark' ? 'light' : 'dark')
    },
    hydrate() {
      document.documentElement.dataset.theme = this.mode
    }
  }
})
