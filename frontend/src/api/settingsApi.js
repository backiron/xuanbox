import { http } from './http'

export const settingsApi = {
  updateProfile(payload) {
    return http.patch('/settings/profile', payload)
  },
  uploadAvatar(file) {
    const formData = new FormData()
    formData.append('file', file)
    return http.post('/settings/avatar', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },
  avatarUrl(cacheKey = '') {
    return `/api/v1/settings/avatar${cacheKey ? `?v=${cacheKey}` : ''}`
  },
  storage() {
    return http.get('/settings/storage')
  }
}
