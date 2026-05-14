import { http } from './http'

export const adminApi = {
  bundle() {
    return http.get('/admin')
  },
  updateUser(id, payload) {
    return http.patch(`/admin/users/${id}`, payload)
  },
  createBackup() {
    return http.post('/admin/backups')
  },
  createMessage(payload) {
    return http.post('/admin/messages', payload)
  },
  archiveMessage(id) {
    return http.delete(`/admin/messages/${id}`)
  },
  updateSystemSettings(payload) {
    return http.patch('/admin/system-settings', payload)
  },
  worker() {
    return http.get('/admin/worker')
  },
  plans() {
    return http.get('/admin/plans')
  }
}
