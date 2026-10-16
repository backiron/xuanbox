import { downloadFile, isAppleMobile } from './dropMedia'

/**
 * Hand a downloaded blob to the person.
 *
 * iPhone/iPad Safari ignores a save that does not happen during a tap, and the download itself takes a
 * while, so there `askToSave(file, deliver)` shows a "ready" prompt and its button calls `deliver`
 * synchronously: the share sheet (Save Video / Save Image into Photos, or Save to Files) when it can take
 * the file, otherwise a regular download. Elsewhere the file is just saved.
 */
export function saveBlobToDevice(blob, filename, askToSave) {
  const file = new File([blob], filename || 'download', { type: blob.type || 'application/octet-stream' })
  if (!isAppleMobile) {
    downloadFile(file)
    return Promise.resolve()
  }
  return askToSave(file, () => deliverDuringTap(file))
}

function deliverDuringTap(file) {
  if (navigator.canShare?.({ files: [file] })) {
    navigator.share({ files: [file] }).catch((error) => {
      if (error?.name !== 'AbortError') downloadFile(file)
    })
    return
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
