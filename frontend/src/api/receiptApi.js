import { http } from './http'

export const receiptApi = {
  list(params = {}) {
    return http.get('/receipts', { params })
  },
  upload(formData, config = {}) {
    return http.post('/receipts/upload', formData, config)
  },
  createFromFile(fileId, params = {}) {
    return http.post(`/receipts/from-file/${fileId}`, null, { params })
  },
  update(id, payload) {
    return http.patch(`/receipts/${id}`, payload)
  },
  remove(id) {
    return http.delete(`/receipts/${id}`)
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
