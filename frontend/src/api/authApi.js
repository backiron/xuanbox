import { http } from './http'

export const authApi = {
  bootstrapOwner(payload) {
    return http.post('/auth/bootstrap-owner', payload)
  },
  login(payload) {
    return http.post('/auth/login', payload)
  },
  me() {
    return http.get('/auth/me')
  }
}
