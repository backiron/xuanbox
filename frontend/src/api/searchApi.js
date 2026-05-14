import { http } from './http'

export const searchApi = {
  query(q, params = {}) {
    return http.get('/search', { params: { q, ...params } })
  }
}
