import { http } from './http'

export const noteApi = {
  list(q) {
    return http.get('/notes', { params: q ? { q } : {} })
  },
  create(body = '') {
    return http.post('/notes', { body })
  },
  get(id) {
    return http.get(`/notes/${id}`)
  },
  update(id, payload) {
    return http.patch(`/notes/${id}`, payload)
  },
  remove(id) {
    return http.delete(`/notes/${id}`)
  },
  addImage(id, file) {
    const form = new FormData()
    form.append('file', file)
    return http.post(`/notes/${id}/images`, form, { timeout: 120000 })
  },
  image(id, imageId) {
    return http.get(`/notes/${id}/images/${imageId}`, { responseType: 'blob' })
  }
}
