import axios from 'axios'

export const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  timeout: 30000
})

let refreshPromise = null

function isAuthRequest(url = '') {
  return url.startsWith('/auth/login') || url.startsWith('/auth/admin-login') || url.startsWith('/auth/refresh')
}

function decodeJwtPayload(token) {
  try {
    const payload = token.split('.')[1]
    const normalized = payload.replace(/-/g, '+').replace(/_/g, '/')
    const padded = normalized.padEnd(Math.ceil(normalized.length / 4) * 4, '=')
    return JSON.parse(window.atob(padded))
  } catch {
    return null
  }
}

function shouldRefreshAccessToken(token) {
  const payload = decodeJwtPayload(token)
  if (!payload?.exp) return false
  const refreshWindowSeconds = 45
  return payload.exp <= Math.floor(Date.now() / 1000) + refreshWindowSeconds
}

async function refreshTokens(refreshToken) {
  refreshPromise ||= axios.post('/auth/refresh', { refresh_token: refreshToken }, {
    baseURL: http.defaults.baseURL,
    timeout: http.defaults.timeout
  })
  try {
    const response = await refreshPromise
    const tokens = response.data.data
    localStorage.setItem('xb_access_token', tokens.access_token)
    localStorage.setItem('xb_refresh_token', tokens.refresh_token)
    localStorage.setItem('xb_client_type', tokens.client_type || 'user_app')
    return tokens
  } finally {
    refreshPromise = null
  }
}

function clearAuthAndRedirect() {
  localStorage.removeItem('xb_access_token')
  localStorage.removeItem('xb_refresh_token')
  localStorage.removeItem('xb_client_type')
  const isAdminArea = window.location.pathname.startsWith('/admin')
  const isPublic = window.location.pathname.startsWith('/drop/public/') || window.location.pathname.startsWith('/public-share/')
  if (!window.location.pathname.startsWith('/login') && !isAdminArea && !isPublic) {
    window.location.href = '/login'
  } else if (isAdminArea && window.location.pathname !== '/admin') {
    window.location.href = '/admin'
  }
}

http.interceptors.request.use(async (config) => {
  const token = localStorage.getItem('xb_access_token')
  const refreshToken = localStorage.getItem('xb_refresh_token')
  const url = config.url || ''
  let accessToken = token

  if (accessToken && refreshToken && !isAuthRequest(url) && shouldRefreshAccessToken(accessToken)) {
    try {
      const tokens = await refreshTokens(refreshToken)
      accessToken = tokens.access_token
    } catch {
      clearAuthAndRedirect()
    }
  }

  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`
  }
  return config
})

http.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config
    const status = error.response?.status
    const refreshToken = localStorage.getItem('xb_refresh_token')
    const authRequest = isAuthRequest(originalRequest?.url)
    const currentAccessToken = localStorage.getItem('xb_access_token')
    const requestAccessToken = originalRequest?.headers?.Authorization?.replace('Bearer ', '')

    if (status === 401 && currentAccessToken && requestAccessToken && currentAccessToken !== requestAccessToken && !originalRequest?._retry) {
      originalRequest._retry = true
      originalRequest.headers.Authorization = `Bearer ${currentAccessToken}`
      return http(originalRequest)
    }

    if (status !== 401 || !refreshToken || originalRequest?._retry || authRequest) {
      if (status === 401 && !authRequest) {
        clearAuthAndRedirect()
      }
      return Promise.reject(error)
    }

    originalRequest._retry = true
    try {
      const tokens = await refreshTokens(refreshToken)
      originalRequest.headers.Authorization = `Bearer ${tokens.access_token}`
      return http(originalRequest)
    } catch (refreshError) {
      clearAuthAndRedirect()
      return Promise.reject(refreshError)
    }
  }
)
