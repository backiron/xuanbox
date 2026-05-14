import { http } from './http'

export const inviteApi = {
  list() {
    return http.get('/invites')
  },
  create(payload) {
    return http.post('/invites', payload)
  }
}
