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
  saveItem(itemId, payload) {
    return http.post(`/drop/items/${itemId}/save`, payload)
  },
  publicUpload(token, formData, config = {}) {
    return http.post(`/drop/public/${token}/upload`, formData, config)
  }
}
