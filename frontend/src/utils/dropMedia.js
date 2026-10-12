import { dropChatApi } from '../api/dropChatApi'

const thumbnailUrls = new Map()
const fileCache = new Map()
const FILE_CACHE_LIMIT = 6

export const isAppleMobile = /iPhone|iPad|iPod/.test(navigator.userAgent)
  || (/Macintosh/.test(navigator.userAgent) && navigator.maxTouchPoints > 1)

export function thumbnailUrl(messageId) {
  if (!thumbnailUrls.has(messageId)) {
    thumbnailUrls.set(
      messageId,
      dropChatApi.thumbnail(messageId).then((response) => URL.createObjectURL(response.data)).catch((error) => {
        thumbnailUrls.delete(messageId)
        throw error
      })
    )
  }
  return thumbnailUrls.get(messageId)
}

export function cachedFile(messageId) {
  return fileCache.get(messageId) || null
}

export async function fetchMessageFile(message, onProgress) {
  const cached = fileCache.get(message.id)
  if (cached) return cached
  const response = await dropChatApi.download(message.id, onProgress)
  const file = new File([response.data], message.filename || 'file', { type: message.mime_type || response.data.type })
  fileCache.set(message.id, file)
  if (fileCache.size > FILE_CACHE_LIMIT) fileCache.delete(fileCache.keys().next().value)
  return file
}

export function forgetMessage(messageId) {
  fileCache.delete(messageId)
  const url = thumbnailUrls.get(messageId)
  thumbnailUrls.delete(messageId)
  if (url) url.then((value) => URL.revokeObjectURL(value)).catch(() => {})
}

export function downloadFile(file) {
  const url = URL.createObjectURL(file)
  const link = document.createElement('a')
  link.href = url
  link.download = file.name
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.setTimeout(() => URL.revokeObjectURL(url), 30000)
}

// On iPhone/iPad the share sheet is the only way a web page can put an image into Photos
// ("Save Image") or a file into the Files app. It must run inside a tap, so callers fetch first.
export function canShareFile(file) {
  return Boolean(isAppleMobile && navigator.canShare && navigator.canShare({ files: [file] }))
}

export async function deliverFile(file) {
  if (canShareFile(file)) {
    try {
      await navigator.share({ files: [file] })
      return
    } catch (error) {
      if (error?.name === 'AbortError') return
    }
  }
  downloadFile(file)
}

export function formatSize(bytes) {
  if (!bytes) return '0 KB'
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.ceil(bytes / 1024))} KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`
  return `${(bytes / 1024 / 1024 / 1024).toFixed(2)} GB`
}

const URL_PATTERN = /(https?:\/\/[^\s<>"']+)/g

export function splitLinks(text) {
  return (text || '').split(URL_PATTERN).filter(Boolean).map((part) => ({ text: part, isLink: /^https?:\/\//.test(part) }))
}
