export const MAX_FILE_UPLOAD_BYTES = 200 * 1024 * 1024
export const MAX_IMAGE_UPLOAD_BYTES = 20 * 1024 * 1024
export const MAX_AVATAR_UPLOAD_BYTES = 2 * 1024 * 1024

export function uploadLimitFor(file) {
  return file?.type?.startsWith('image/') ? MAX_IMAGE_UPLOAD_BYTES : MAX_FILE_UPLOAD_BYTES
}

export function formatUploadLimit(bytes) {
  return `${Math.round(bytes / 1024 / 1024)} MB`
}

export function findUploadLimitError(files, t) {
  const pickedFiles = Array.from(files || [])
  const tooLarge = pickedFiles.find((file) => file.size > uploadLimitFor(file))
  if (!tooLarge) return ''
  return t('common.uploadLimits.tooLarge', {
    name: tooLarge.name,
    limit: formatUploadLimit(uploadLimitFor(tooLarge))
  })
}
