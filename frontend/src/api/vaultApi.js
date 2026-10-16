import { http } from './http'

const unlock = (token) => ({ headers: { 'X-Vault-Unlock': token } })

export const vaultApi = {
  status() {
    return http.get('/important-docs/status')
  },
  setup(pin) {
    return http.post('/important-docs/setup', { pin })
  },
  unlock(pin) {
    return http.post('/important-docs/unlock', { pin })
  },
  lock() {
    return http.post('/important-docs/lock')
  },
  changePin(currentPin, newPin) {
    return http.post('/important-docs/change-pin', { current_pin: currentPin, new_pin: newPin })
  },
  resetPin(password, newPin) {
    return http.post('/important-docs/reset-pin', { password, new_pin: newPin })
  },
  list(token) {
    return http.get('/important-docs', unlock(token))
  },
  upload(token, file, onUploadProgress) {
    const form = new FormData()
    form.append('file', file)
    return http.post('/important-docs/upload', form, { ...unlock(token), timeout: 300000, onUploadProgress })
  },
  addFile(token, fileId, title) {
    return http.post(`/important-docs/from-file/${fileId}`, title ? { title } : {}, unlock(token))
  },
  addPhoto(token, photoId) {
    return http.post(`/important-docs/from-photo/${photoId}`, {}, unlock(token))
  },
  content(token, id, download = false) {
    return http.get(`/important-docs/${id}/content`, { ...unlock(token), params: download ? { download: 1 } : {}, responseType: 'blob', timeout: 300000 })
  },
  thumbnail(token, id) {
    return http.get(`/important-docs/${id}/thumbnail`, { ...unlock(token), responseType: 'blob' })
  },
  update(token, id, payload) {
    return http.patch(`/important-docs/${id}`, payload, unlock(token))
  },
  restore(token, id) {
    return http.post(`/important-docs/${id}/restore`, {}, unlock(token))
  },
  remove(token, id) {
    return http.delete(`/important-docs/${id}`, unlock(token))
  },
  resolveInbox(token, itemId) {
    return http.post(`/inbox/${itemId}/resolve`, { action: 'vault' }, unlock(token))
  }
}
