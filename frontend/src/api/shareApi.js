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
  archive(id) {
    return http.delete(`/shares/${id}/archive`)
  },
  archiveInactive() {
    return http.post('/shares/archive-inactive')
  },
  publicMetadata(token) {
    return http.get(`/public-share/${token}`)
  },
  verifyPassword(token, password) {
    return http.post(`/public-share/${token}/verify-password`, { password })
  },
  publicDownload(token, accessToken) {
    return http.get(`/public-share/${token}/download`, {
      headers: accessToken ? { 'X-Share-Access': accessToken } : {},
      responseType: 'blob'
    })
  }
}
