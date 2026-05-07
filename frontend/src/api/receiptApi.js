import { http } from './http'

export const receiptApi = {
  list(params = {}) {
    return http.get('/receipts', { params })
  },
  upload(formData, config = {}) {
    return http.post('/receipts/upload', formData, config)
  },
  update(id, payload) {
    return http.patch(`/receipts/${id}`, payload)
  },
  startOcr(id) {
    return http.post(`/receipts/${id}/ocr`)
  },
  ocrTasks(id) {
    return http.get(`/receipts/${id}/ocr`)
  },
  confirmOcr(id, taskId, payload) {
    return http.post(`/receipts/${id}/ocr/${taskId}/confirm`, payload)
  },
  retryOcr(id, taskId) {
    return http.post(`/receipts/${id}/ocr/${taskId}/retry`)
  }
}
