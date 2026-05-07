import axios from 'axios'

export const http = axios.create({
  baseURL: '/api/v1',
  timeout: 30000
})

let refreshPromise = null

http.interceptors.request.use((config) => {
  const token = localStorage.getItem('xb_access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

http.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config
    const status = error.response?.status
    const refreshToken = localStorage.getItem('xb_refresh_token')
    const isAuthRequest = originalRequest?.url?.startsWith('/auth/login') || originalRequest?.url?.startsWith('/auth/refresh')
    const currentAccessToken = localStorage.getItem('xb_access_token')
    const requestAccessToken = originalRequest?.headers?.Authorization?.replace('Bearer ', '')

    if (status === 401 && currentAccessToken && requestAccessToken && currentAccessToken !== requestAccessToken && !originalRequest?._retry) {
      originalRequest._retry = true
      originalRequest.headers.Authorization = `Bearer ${currentAccessToken}`
      return http(originalRequest)
    }

    if (status !== 401 || !refreshToken || originalRequest?._retry || isAuthRequest) {
      if (status === 401 && !isAuthRequest) {
        localStorage.removeItem('xb_access_token')
        localStorage.removeItem('xb_refresh_token')
        if (!window.location.pathname.startsWith('/login') && !window.location.pathname.startsWith('/drop/public/') && !window.location.pathname.startsWith('/public-share/')) {
          window.location.href = '/login'
        }
      }
      return Promise.reject(error)
    }

    originalRequest._retry = true
    try {
      refreshPromise ||= http.post('/auth/refresh', { refresh_token: refreshToken })
      const response = await refreshPromise
      refreshPromise = null
      const tokens = response.data.data
      localStorage.setItem('xb_access_token', tokens.access_token)
      localStorage.setItem('xb_refresh_token', tokens.refresh_token)
      originalRequest.headers.Authorization = `Bearer ${tokens.access_token}`
      return http(originalRequest)
    } catch (refreshError) {
      refreshPromise = null
      localStorage.removeItem('xb_access_token')
      localStorage.removeItem('xb_refresh_token')
      if (!window.location.pathname.startsWith('/login') && !window.location.pathname.startsWith('/drop/public/') && !window.location.pathname.startsWith('/public-share/')) {
        window.location.href = '/login'
      }
      return Promise.reject(refreshError)
    }
  }
)
