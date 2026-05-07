import { http } from './http'

export const dropApi = {
  sessions() {
    return http.get('/drop/sessions')
  },
  createSession(payload) {
    return http.post('/drop/sessions', payload)
  },
  items(sessionId) {
    return http.get(`/drop/sessions/${sessionId}/items`)
  },
  eventUrl(sessionId) {
    const token = localStorage.getItem('xb_access_token')
    return `/api/v1/drop/sessions/${sessionId}/events?access_token=${encodeURIComponent(token || '')}`
  },
  downloadUrl(itemId) {
    return `/api/v1/drop/items/${itemId}/download`
  },
  downloadItem(itemId) {
    return http.get(`/drop/items/${itemId}/download`, { responseType: 'blob' })
  },
  saveItem(itemId, payload) {
    return http.post(`/drop/items/${itemId}/save`, payload)
  },
  deleteItem(itemId) {
    return http.delete(`/drop/items/${itemId}`)
  },
  publicUpload(token, formData, config = {}) {
    return http.post(`/drop/public/${token}/upload`, formData, config)
  }
}
