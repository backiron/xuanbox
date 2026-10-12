import { http } from './http'

export const dropChatApi = {
  me() {
    return http.get('/drop/me')
  },
  renameDevice(deviceId, deviceName) {
    return http.patch(`/drop/devices/${deviceId}`, { device_name: deviceName })
  },
  removeDevice(deviceId) {
    return http.delete(`/drop/devices/${deviceId}`)
  },
  threads() {
    return http.get('/drop/threads')
  },
  openDirect(userId) {
    return http.post('/drop/threads/direct', { user_id: userId })
  },
  messages(threadId, params = {}) {
    return http.get(`/drop/threads/${threadId}/messages`, { params })
  },
  sendText(threadId, payload) {
    return http.post(`/drop/threads/${threadId}/messages`, payload)
  },
  sendFile(threadId, file, { targetDeviceId, clientId, onProgress, signal } = {}) {
    const formData = new FormData()
    formData.append('file', file, file.name)
    if (targetDeviceId) formData.append('target_device_id', targetDeviceId)
    if (clientId) formData.append('client_id', clientId)
    return http.post(`/drop/threads/${threadId}/files`, formData, {
      timeout: 0,
      signal,
      onUploadProgress(event) {
        if (onProgress && event.total) onProgress(event.loaded / event.total)
      }
    })
  },
  startUpload(threadId, payload) {
    return http.post(`/drop/threads/${threadId}/uploads`, payload)
  },
  uploadStatus(uploadId) {
    return http.get(`/drop/uploads/${uploadId}`)
  },
  uploadChunk(uploadId, index, blob, { onProgress, signal } = {}) {
    return http.put(`/drop/uploads/${uploadId}/chunks/${index}`, blob, {
      headers: { 'Content-Type': 'application/octet-stream' },
      timeout: 0,
      signal,
      onUploadProgress(event) {
        if (onProgress) onProgress(event.loaded)
      }
    })
  },
  completeUpload(uploadId) {
    return http.post(`/drop/uploads/${uploadId}/complete`, null, { timeout: 0 })
  },
  cancelUpload(uploadId) {
    return http.delete(`/drop/uploads/${uploadId}`)
  },
  downloadLink(messageId) {
    return http.post(`/drop/messages/${messageId}/download-link`)
  },
  markRead(threadId) {
    return http.post(`/drop/threads/${threadId}/read`)
  },
  download(messageId, onProgress) {
    return http.get(`/drop/messages/${messageId}/download`, {
      responseType: 'blob',
      timeout: 0,
      onDownloadProgress(event) {
        if (onProgress && event.total) onProgress(event.loaded / event.total)
      }
    })
  },
  thumbnail(messageId) {
    return http.get(`/drop/messages/${messageId}/thumbnail`, { responseType: 'blob' })
  },
  save(messageId, payload) {
    return http.post(`/drop/messages/${messageId}/save`, payload)
  },
  remove(messageId) {
    return http.delete(`/drop/messages/${messageId}`)
  },
  contacts() {
    return http.get('/drop/contacts')
  },
  requestContact(identifier) {
    return http.post('/drop/contacts', { identifier })
  },
  acceptContact(contactId) {
    return http.post(`/drop/contacts/${contactId}/accept`)
  },
  declineContact(contactId) {
    return http.post(`/drop/contacts/${contactId}/decline`)
  },
  removeContact(contactId) {
    return http.delete(`/drop/contacts/${contactId}`)
  },
  wsTicket() {
    return http.post('/drop/ws-ticket')
  }
}
