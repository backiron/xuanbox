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
  }
}
