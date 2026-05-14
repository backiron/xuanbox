import { http } from './http'

export const photoApi = {
  list() {
    return http.get('/photos')
  },
  upload(formData, config = {}) {
    return http.post('/photos/upload', formData, config)
  },
  thumbnailUrl(photoId) {
    return `/api/v1/photos/${photoId}/thumbnail`
  },
  thumbnailBlob(photoId) {
    return http.get(`/photos/${photoId}/thumbnail`, { responseType: 'blob' })
  },
  previewUrl(photoId) {
    return `/api/v1/photos/${photoId}/preview`
  },
  previewBlob(photoId) {
    return http.get(`/photos/${photoId}/preview`, { responseType: 'blob' })
  },
  originalBlob(photoId) {
    return http.get(`/photos/${photoId}/original`, { responseType: 'blob' })
  },
  favorite(photoId, isFavorite) {
    return http.patch(`/photos/${photoId}/favorite`, null, { params: { is_favorite: isFavorite } })
  },
  remove(photoId) {
    return http.delete(`/photos/${photoId}`)
  }
}

export const albumApi = {
  list() {
    return http.get('/albums')
  },
  create(payload) {
    return http.post('/albums', payload)
  },
  addPhoto(albumId, photoId) {
    return http.post(`/albums/${albumId}/photos/${photoId}`)
  },
  photos(albumId) {
    return http.get(`/albums/${albumId}/photos`)
  }
}
