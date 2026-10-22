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
  purge(id) {
    return http.delete(`/files/${id}/purge`)
  },
  restore(id) {
    return http.post(`/files/${id}/restore`)
  },
  trash() {
    return http.get('/trash')
  },
  download(id, onDownloadProgress) {
    return http.get(`/files/${id}/download`, { responseType: 'blob', timeout: 600000, onDownloadProgress })
  },
  createMarkdown(payload) {
    return http.post('/files/markdown', payload)
  },
  readMarkdown(id) {
    return http.get(`/files/${id}/markdown`)
  },
  saveMarkdown(id, payload) {
    return http.put(`/files/${id}/markdown`, payload)
  }
}

export function isMarkdownFile(file) {
  return ['md', 'markdown'].includes((file?.file_ext || '').toLowerCase())
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
  update(id, payload) {
    return http.patch(`/tags/${id}`, payload)
  },
  links(params = {}) {
    return http.get('/tags/links', { params })
  },
  attach(id, payload) {
    return http.post(`/tags/${id}/attach`, payload)
  }
}

export const intelligenceApi = {
  file(fileId) {
    return http.get(`/intelligence/files/${fileId}`)
  },
  retry(fileId) {
    return http.post(`/intelligence/files/${fileId}/retry`)
  },
  updateProfile(fileId, payload) {
    return http.patch(`/intelligence/files/${fileId}/profile`, payload)
  }
}
