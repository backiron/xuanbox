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
  }
}
