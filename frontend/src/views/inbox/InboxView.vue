<script setup>
import { computed, onMounted, ref } from 'vue'
import { CheckCircle2, FileText, Image, Inbox, ReceiptText, RotateCcw, Trash2, Upload } from 'lucide-vue-next'

import PageHeader from '../../components/common/PageHeader.vue'
import { inboxApi } from '../../api/inboxApi'

const items = ref([])
const loading = ref(false)
const resolvingId = ref('')
const uploadProgress = ref(0)
const message = ref('')
const error = ref('')

const pendingCount = computed(() => items.value.length)

function formatBytes(value) {
  if (!value) return '0 KB'
  if (value < 1024 * 1024) return `${Math.max(1, Math.ceil(value / 1024))} KB`
  return `${(value / 1024 / 1024).toFixed(1)} MB`
}

function formatDate(value) {
  if (!value) return ''
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))
}

function iconFor(item) {
  if (item.file?.mime_type?.startsWith('image/')) return Image
  if (item.suggested_type === 'receipt') return ReceiptText
  return FileText
}

function fileActionLabel(item) {
  return item.file?.mime_type?.startsWith('image/') ? 'Save as PDF file' : 'Save as file'
}

async function loadInbox() {
  loading.value = true
  error.value = ''
  try {
    const response = await inboxApi.list()
    items.value = response.data.data
  } catch (err) {
    error.value = err.response?.data?.message || 'Inbox could not be loaded.'
  } finally {
    loading.value = false
  }
}

async function uploadFiles(files) {
  const pickedFiles = Array.from(files || [])
  if (!pickedFiles.length) return
  uploadProgress.value = 1
  message.value = ''
  error.value = ''
  try {
    for (const pickedFile of pickedFiles) {
      const formData = new FormData()
      formData.append('file', pickedFile)
      await inboxApi.upload(formData, {
        onUploadProgress(progressEvent) {
          if (progressEvent.total) uploadProgress.value = Math.round((progressEvent.loaded / progressEvent.total) * 100)
        }
      })
    }
    message.value = `${pickedFiles.length} item${pickedFiles.length > 1 ? 's' : ''} added to Inbox.`
    await loadInbox()
  } catch (err) {
    error.value = err.response?.data?.message || 'Upload failed.'
  } finally {
    uploadProgress.value = 0
  }
}

async function onFileChange(event) {
  await uploadFiles(event.target.files)
  event.target.value = ''
}

function resetFileInput(event) {
  event.target.value = ''
}

async function resolveItem(item, action) {
  resolvingId.value = item.id
  message.value = ''
  error.value = ''
  try {
    await inboxApi.resolve(item.id, action)
    const label = action === 'photo' ? 'Photos' : action === 'receipt' ? 'Receipts' : action === 'file' ? 'Files' : 'dismissed'
    message.value = action === 'dismiss' ? 'Item dismissed.' : `Saved to ${label}.`
    await loadInbox()
  } catch (err) {
    error.value = err.response?.data?.message || 'Could not resolve item.'
  } finally {
    resolvingId.value = ''
  }
}

onMounted(loadInbox)
</script>

<template>
  <section class="xb-inbox-page">
    <PageHeader title="Inbox" :subtitle="pendingCount ? `${pendingCount} uploads waiting for your decision.` : 'Review new uploads before they become photos, files, or receipts.'">
      <button class="xb-secondary-button" type="button" :disabled="loading" @click="loadInbox">
        <RotateCcw :size="16" />
        Refresh
      </button>
      <label class="xb-upload-button">
        <Upload :size="16" />
        Upload
        <input type="file" multiple @click="resetFileInput" @change="onFileChange" />
      </label>
    </PageHeader>

    <div v-if="uploadProgress" class="xb-progress xb-dashboard-upload-progress">
      <span :style="{ width: `${uploadProgress}%` }"></span>
    </div>
    <p v-if="message" class="xb-status-note is-success">{{ message }}</p>
    <p v-if="error" class="xb-status-note is-error">{{ error }}</p>

    <label class="xb-panel xb-inbox-dropzone">
      <Upload :size="28" />
      <div>
        <strong>Inbox upload queue</strong>
        <span>New uploads stay here until you choose Photo, File, Receipt, or Dismiss.</span>
      </div>
      <input type="file" multiple @click="resetFileInput" @change="onFileChange" />
    </label>

    <div v-if="loading" class="xb-empty-state">
      <strong>Loading Inbox...</strong>
      <p>Checking pending uploads.</p>
    </div>

    <div v-else-if="!items.length" class="xb-empty-state">
      <Inbox :size="34" />
      <strong>Inbox is clear</strong>
      <p>Dashboard uploads will wait here until you decide where they belong.</p>
    </div>

    <section v-else class="xb-inbox-list">
      <article v-for="item in items" :key="item.id" class="xb-panel xb-inbox-item">
        <div class="xb-inbox-icon">
          <component :is="iconFor(item)" :size="24" />
        </div>
        <div class="xb-inbox-main">
          <div class="xb-inbox-title-row">
            <div>
              <strong>{{ item.file?.display_name || 'Upload' }}</strong>
              <span>{{ item.file?.mime_type || item.file?.file_category || 'file' }} / {{ formatBytes(item.file?.file_size) }}</span>
            </div>
            <time>{{ formatDate(item.created_at) }}</time>
          </div>
          <p>{{ item.suggestion_reason || 'Choose the correct destination before this item appears in your library.' }}</p>
          <div class="xb-inbox-actions">
            <button class="xb-secondary-button" type="button" :disabled="resolvingId === item.id || !item.file?.mime_type?.startsWith('image/')" @click="resolveItem(item, 'photo')">
              <Image :size="16" />
              Save as photo
            </button>
            <button class="xb-secondary-button" type="button" :disabled="resolvingId === item.id" @click="resolveItem(item, 'file')">
              <FileText :size="16" />
              {{ fileActionLabel(item) }}
            </button>
            <button class="xb-secondary-button" type="button" :disabled="resolvingId === item.id" @click="resolveItem(item, 'receipt')">
              <ReceiptText :size="16" />
              Save as receipt
            </button>
            <button class="xb-secondary-button xb-danger-button" type="button" :disabled="resolvingId === item.id" @click="resolveItem(item, 'dismiss')">
              <Trash2 :size="16" />
              Dismiss
            </button>
          </div>
        </div>
        <CheckCircle2 v-if="item.suggested_type" class="xb-inbox-suggested" :size="18" />
      </article>
    </section>
  </section>
</template>
