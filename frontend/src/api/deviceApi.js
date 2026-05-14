import { http } from './http'

export const deviceApi = {
  list() {
    return http.get('/devices')
  },
  revoke(id) {
    return http.post(`/settings/devices/${id}/revoke`)
  }
}
