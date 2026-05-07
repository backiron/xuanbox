import { http } from './http'

export const documentApi = {
  list(params = {}) {
    return http.get('/documents', { params })
  },
  reminders(days = 90) {
    return http.get('/documents/reminders', { params: { days } })
  },
  upload(formData, config = {}) {
    return http.post('/documents/upload', formData, config)
  },
  update(id, payload) {
    return http.patch(`/documents/${id}`, payload)
  },
  download(id, password) {
    return http.get(`/documents/${id}/download`, {
      params: password ? { password } : {},
      responseType: 'blob'
    })
  }
}

export const dashboardApi = {
  summary() {
    return http.get('/dashboard')
  }
}
