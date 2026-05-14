import { http } from './http'

export const authApi = {
  bootstrapOwner(payload) {
    return http.post('/auth/bootstrap-owner', payload)
  },
  registerByInvite(payload) {
    return http.post('/auth/register-by-invite', payload)
  },
  register(payload) {
    return http.post('/auth/register', payload)
  },
  registrationSettings() {
    return http.get('/auth/registration-settings')
  },
  login(payload) {
    return http.post('/auth/login', payload)
  },
  adminLogin(payload) {
    return http.post('/auth/admin-login', payload)
  },
  logout(refreshToken) {
    return http.post('/auth/logout', refreshToken ? { refresh_token: refreshToken } : null)
  },
  logoutAllDevices() {
    return http.post('/auth/logout-all-devices')
  },
  changePassword(payload) {
    return http.post('/auth/change-password', payload)
  },
  me() {
    return http.get('/auth/me')
  }
}
