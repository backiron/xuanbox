<script setup>
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import { Send, Upload } from 'lucide-vue-next'
import { dropApi } from '../../api/dropApi'

const route = useRoute()
const token = route.params.token
const status = ref('')
const error = ref('')
const progress = ref(0)
const uploading = ref(false)
const currentFile = ref('')
const completedCount = ref(0)
const totalCount = ref(0)

function getErrorMessage(uploadError) {
  const code = uploadError.response?.data?.error?.code
  if (code === 'drop_session_closed') return 'This upload link has expired. Please scan the newest XuanDrop QR code.'
  return uploadError.response?.data?.error?.message || uploadError.response?.data?.message || 'Upload failed. Please try again.'
}

async function onFileChange(event) {
  const files = Array.from(event.target.files || [])
  if (!files.length) return
  uploading.value = true
  status.value = 'Preparing upload'
  error.value = ''
  completedCount.value = 0
  totalCount.value = files.length
  try {
    for (const [index, file] of files.entries()) {
      currentFile.value = file.name
      status.value = `Uploading ${index + 1} of ${files.length}`
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
    status.value = files.length === 1 ? 'Upload complete' : `${files.length} uploads complete`
    currentFile.value = ''
  } catch (uploadError) {
    error.value = getErrorMessage(uploadError)
    status.value = completedCount.value
      ? `${completedCount.value} of ${totalCount.value} uploaded`
      : ''
  } finally {
    uploading.value = false
    event.target.value = ''
  }
}
</script>

<template>
  <main class="xb-public-drop">
    <section class="xb-public-drop-panel">
      <Send :size="42" />
      <h1>XuanDrop</h1>
      <p>Send files directly into this private XuanBox session.</p>
      <div v-if="progress" class="xb-progress">
        <span :style="{ width: `${progress}%` }"></span>
      </div>
      <label class="xb-upload-button" :class="{ 'is-disabled': uploading }">
        <Upload :size="18" />
        {{ uploading ? 'Uploading...' : 'Choose files' }}
        <input type="file" multiple :disabled="uploading" @change="onFileChange" />
      </label>
      <strong v-if="status">{{ status }}</strong>
      <span v-if="currentFile" class="xb-public-drop-file">{{ currentFile }}</span>
      <span v-if="totalCount" class="xb-public-drop-count">{{ completedCount }} / {{ totalCount }} sent</span>
      <p v-if="error" class="xb-form-error">{{ error }}</p>
    </section>
  </main>
</template>
