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

export const importantDocApi = {
  status() {
    return http.get('/important-docs/status')
  },
  setup(pin) {
    return http.post('/important-docs/setup', { pin })
  },
  unlock(pin) {
    return http.post('/important-docs/unlock', { pin })
  },
  list(unlockToken) {
    return http.get('/important-docs', { headers: { 'X-Vault-Unlock': unlockToken } })
  },
  createFromFile(fileId, payload, unlockToken) {
    return http.post(`/important-docs/from-file/${fileId}`, payload, { headers: { 'X-Vault-Unlock': unlockToken } })
  },
  download(id, unlockToken) {
    return http.get(`/important-docs/${id}/download`, {
      responseType: 'blob',
      headers: { 'X-Vault-Unlock': unlockToken }
    })
  },
  remove(id, unlockToken) {
    return http.delete(`/important-docs/${id}`, { headers: { 'X-Vault-Unlock': unlockToken } })
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
