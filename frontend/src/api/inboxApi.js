import { http } from './http'

export const inboxApi = {
  list(params = {}) {
    return http.get('/inbox', { params })
  },
  upload(formData, config = {}) {
    return http.post('/inbox/upload', formData, config)
  },
  resolve(id, action) {
    return http.post(`/inbox/${id}/resolve`, { action })
  }
}
