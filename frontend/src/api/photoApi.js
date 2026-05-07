import { http } from './http'

export const photoApi = {
  list() {
    return http.get('/photos')
  },
  upload(formData) {
    return http.post('/photos/upload', formData)
  },
  thumbnailUrl(photoId) {
    return `/api/v1/photos/${photoId}/thumbnail`
  },
  thumbnailBlob(photoId) {
    return http.get(`/photos/${photoId}/thumbnail`, { responseType: 'blob' })
  },
  previewUrl(photoId) {
    return `/api/v1/photos/${photoId}/preview`
  }
}
