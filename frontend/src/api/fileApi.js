import { http } from './http'

export const fileApi = {
  list(params = {}) {
    return http.get('/files', { params })
  },
  upload(formData, config = {}) {
    return http.post('/files/upload', formData, config)
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
  },
  download(id) {
    return http.get(`/files/${id}/download`, { responseType: 'blob' })
  }
}

export const folderApi = {
  list(params = {}) {
    return http.get('/folders', { params })
  },
  create(payload) {
    return http.post('/folders', payload)
  },
  update(id, payload) {
    return http.patch(`/folders/${id}`, payload)
  },
  remove(id) {
    return http.delete(`/folders/${id}`)
  }
}

export const tagApi = {
  list() {
    return http.get('/tags')
  },
  create(payload) {
    return http.post('/tags', payload)
  },
  links(params = {}) {
    return http.get('/tags/links', { params })
  },
  attach(id, payload) {
    return http.post(`/tags/${id}/attach`, payload)
  }
}
