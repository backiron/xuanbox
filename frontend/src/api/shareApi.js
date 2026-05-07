import { http } from './http'

export const shareApi = {
  list(mode = 'created') {
    return http.get('/shares', { params: { mode } })
  },
  create(payload) {
    return http.post('/shares', payload)
  },
  update(id, payload) {
    return http.patch(`/shares/${id}`, payload)
  },
  remove(id) {
    return http.delete(`/shares/${id}`)
  },
  publicMetadata(token) {
    return http.get(`/public-share/${token}`)
  },
  verifyPassword(token, password) {
    return http.post(`/public-share/${token}/verify-password`, { password })
  },
  publicDownload(token, password) {
    return http.get(`/public-share/${token}/download`, {
      params: password ? { password } : {},
      responseType: 'blob'
    })
  }
}
