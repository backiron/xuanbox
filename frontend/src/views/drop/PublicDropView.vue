<script setup>
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import { Send, Upload } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { dropApi } from '../../api/dropApi'
import { findUploadLimitError } from '../../utils/uploadLimits'

const route = useRoute()
const { t } = useI18n()
const token = route.params.token
const status = ref('')
const error = ref('')
const progress = ref(0)
const uploading = ref(false)
const draggingFiles = ref(false)
const currentFile = ref('')
const completedCount = ref(0)
const totalCount = ref(0)

function getErrorMessage(uploadError) {
  const code = uploadError.response?.data?.error?.code
  if (code === 'drop_session_closed') return t('pages.publicDrop.expired')
  return uploadError.response?.data?.error?.message || uploadError.response?.data?.message || t('pages.publicDrop.uploadFailed')
}

async function uploadFiles(fileList) {
  const files = Array.from(fileList || [])
  if (!files.length) return
  const limitError = findUploadLimitError(files, t)
  if (limitError) {
    error.value = limitError
    status.value = ''
    return
  }
  uploading.value = true
  status.value = t('pages.publicDrop.preparingUpload')
  error.value = ''
  completedCount.value = 0
  totalCount.value = files.length
  try {
    for (const [index, file] of files.entries()) {
      currentFile.value = file.name
      status.value = t('pages.publicDrop.uploading', { current: index + 1, total: files.length })
      progress.value = 1
      const formData = new FormData()
      formData.append('file', file)
      await dropApi.publicUpload(token, formData, {
        onUploadProgress(progressEvent) {
          if (progressEvent.total) progress.value = Math.round((progressEvent.loaded / progressEvent.total) * 100)
        }
      })
      completedCount.value += 1
    }
    progress.value = 100
    status.value = files.length === 1 ? t('pages.publicDrop.uploadComplete') : t('pages.publicDrop.uploadDone', { count: files.length })
    currentFile.value = ''
  } catch (uploadError) {
    error.value = getErrorMessage(uploadError)
    status.value = completedCount.value
      ? t('pages.publicDrop.filesCount', { sent: completedCount.value, total: totalCount.value })
      : ''
  } finally {
    uploading.value = false
  }
}

async function onFileChange(event) {
  await uploadFiles(event.target.files)
  event.target.value = ''
}

function onDragEnter(event) {
  if (!event.dataTransfer?.types?.includes('Files') || uploading.value) return
  draggingFiles.value = true
}

function onDragLeave(event) {
  if (event.currentTarget.contains(event.relatedTarget)) return
  draggingFiles.value = false
}

async function onFileDrop(event) {
  draggingFiles.value = false
  if (uploading.value) return
  await uploadFiles(event.dataTransfer?.files)
}
</script>

<template>
  <main
    class="xb-public-drop"
    :class="{ 'is-dragging': draggingFiles }"
    @dragenter.prevent="onDragEnter"
    @dragover.prevent="draggingFiles = true"
    @dragleave="onDragLeave"
    @drop.prevent="onFileDrop"
  >
    <section class="xb-public-drop-panel">
      <Send :size="42" />
      <h1>{{ t('pages.publicDrop.title') }}</h1>
      <p>{{ t('pages.publicDrop.subtitle') }}</p>
      <div v-if="progress" class="xb-progress">
        <span :style="{ width: `${progress}%` }"></span>
      </div>
      <label
        class="xb-upload-button"
        :class="{ 'is-disabled': uploading }"
        @dragenter.prevent="onDragEnter"
        @dragover.prevent="draggingFiles = true"
        @drop.prevent="onFileDrop"
      >
        <Upload :size="18" />
        {{ uploading ? t('pages.publicDrop.uploadInProgress') : t('pages.publicDrop.chooseFiles') }}
        <input type="file" multiple :disabled="uploading" @change="onFileChange" />
      </label>
      <strong v-if="status">{{ status }}</strong>
      <span v-if="currentFile" class="xb-public-drop-file">{{ currentFile }}</span>
      <span v-if="totalCount" class="xb-public-drop-count">{{ t('pages.publicDrop.filesCount', { sent: completedCount, total: totalCount }) }}</span>
      <p v-if="error" class="xb-form-error">{{ error }}</p>
    </section>
  </main>
</template>
