import { http } from './http'

export const messageApi = {
  list(params = {}) {
    return http.get('/messages', { params })
  },
  unreadCount() {
    return http.get('/messages/unread-count')
  },
  markRead(id) {
    return http.post(`/messages/${id}/read`)
  }
}
