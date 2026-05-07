<script setup>
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import { Send, Upload } from 'lucide-vue-next'
import { dropApi } from '../../api/dropApi'

const route = useRoute()
const token = route.params.token
const status = ref('')
const progress = ref(0)

async function onFileChange(event) {
  const files = Array.from(event.target.files || [])
  if (!files.length) return
  status.value = 'Uploading'
  for (const file of files) {
    const formData = new FormData()
    formData.append('file', file)
    await dropApi.publicUpload(token, formData, {
      onUploadProgress(progressEvent) {
        if (progressEvent.total) progress.value = Math.round((progressEvent.loaded / progressEvent.total) * 100)
      }
    })
  }
  progress.value = 0
  status.value = 'Uploaded'
  event.target.value = ''
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
      <label class="xb-upload-button">
        <Upload :size="18" />
        Choose files
        <input type="file" multiple @change="onFileChange" />
      </label>
      <strong v-if="status">{{ status }}</strong>
    </section>
  </main>
</template>
