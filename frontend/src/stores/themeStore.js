import { defineStore } from 'pinia'

export const useThemeStore = defineStore('theme', {
  state: () => ({
    mode: localStorage.getItem('xb_theme') || 'light'
  }),
  actions: {
    toggle() {
      this.mode = this.mode === 'dark' ? 'light' : 'dark'
      localStorage.setItem('xb_theme', this.mode)
      document.documentElement.dataset.theme = this.mode
    },
    hydrate() {
      document.documentElement.dataset.theme = this.mode
    }
  }
})
