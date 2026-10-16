import { canShareFile, downloadFile } from './dropMedia'

/**
 * Hand a downloaded blob to the person.
 *
 * On iPhone/iPad a page can only put a video or photo into Photos (or a file into Files) through the
 * share sheet, and the share sheet only opens from a fresh tap. The download itself takes a while, so
 * `askToSave` shows a "ready" prompt whose button supplies that tap. Elsewhere the file is just saved.
 */
export async function saveBlobToDevice(blob, filename, askToSave) {
  const file = new File([blob], filename || 'download', { type: blob.type || 'application/octet-stream' })
  if (canShareFile(file)) {
    if (!(await askToSave(file))) return
    try {
      await navigator.share({ files: [file] })
      return
    } catch (error) {
      if (error?.name === 'AbortError') return
    }
  }
  downloadFile(file)
}

export function downloadPercent(event) {
  return event.total ? Math.max(1, Math.round((event.loaded / event.total) * 100)) : 1
}

const EXTENSIONS = { 'image/jpeg': 'jpg', 'image/png': 'png', 'image/heic': 'heic', 'image/webp': 'webp', 'image/gif': 'gif', 'video/mp4': 'mp4', 'video/quicktime': 'mov', 'application/pdf': 'pdf' }

export function withExtension(name, mimeType) {
  const ext = EXTENSIONS[mimeType]
  return !ext || /\.[a-z0-9]{2,5}$/i.test(name) ? name : `${name}.${ext}`
}
