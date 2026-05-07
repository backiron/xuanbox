import { http } from './http'

export const fileApi = {
  list(params = {}) {
    return http.get('/files', { params })
  },
  upload(formData) {
    return http.post('/files/upload', formData)
  },
  update(id, payload) {
    return http.patch(`/files/${id}`, payload)
  },
  remove(id) {
    return http.delete(`/files/${id}`)
  },
  restore(id) {
    return http.post(`/files/${id}/restore`)
  },
  trash() {
    return http.get('/trash')
  }
}

export const folderApi = {
  list(params = {}) {
    return http.get('/folders', { params })
  },
  create(payload) {
    return http.post('/folders', payload)
  },
  remove(id) {
    return http.delete(`/folders/${id}`)
  }
}
