<script setup>
import { computed, onMounted, ref } from 'vue'
import { CheckCircle2, FileText, Image, Inbox, ReceiptText, RotateCcw, Trash2, Upload } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'

import PageHeader from '../../components/common/PageHeader.vue'
import { inboxApi } from '../../api/inboxApi'

const items = ref([])
const loading = ref(false)
const resolvingId = ref('')
const uploadProgress = ref(0)
const draggingFiles = ref(false)
const message = ref('')
const error = ref('')
const { t } = useI18n()

const pendingCount = computed(() => items.value.length)

function formatBytes(value) {
  if (!value) return t('common.file.noSize')
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
  return item.file?.mime_type?.startsWith('image/')
    ? t('pages.inbox.saveAsPdf')
    : t('pages.inbox.fileActionFile')
}

async function loadInbox() {
  loading.value = true
  error.value = ''
  try {
    const response = await inboxApi.list()
    items.value = response.data.data
  } catch (err) {
    error.value = err.response?.data?.message || t('pages.inbox.loadedFailed')
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
    message.value = t('pages.inbox.uploadAdded', {
      count: pickedFiles.length,
      plural: pickedFiles.length > 1 ? 's' : ''
    })
    await loadInbox()
  } catch (err) {
    error.value = err.response?.data?.message || t('pages.inbox.uploadFailed')
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

function onDragEnter(event) {
  if (!event.dataTransfer?.types?.includes('Files')) return
  draggingFiles.value = true
}

function onDragLeave(event) {
  if (event.currentTarget.contains(event.relatedTarget)) return
  draggingFiles.value = false
}

async function onFileDrop(event) {
  draggingFiles.value = false
  await uploadFiles(event.dataTransfer?.files)
}

async function resolveItem(item, action) {
  resolvingId.value = item.id
  message.value = ''
  error.value = ''
  try {
    await inboxApi.resolve(item.id, action)
    const label = action === 'photo'
      ? t('pages.dashboard.photos')
      : action === 'receipt'
        ? t('routes.receipts')
        : action === 'file'
          ? t('routes.files')
          : t('pages.inbox.dismiss')
    message.value = action === 'dismiss'
      ? t('pages.inbox.dismissed')
      : t('pages.inbox.saved', { name: label })
    await loadInbox()
  } catch (err) {
    error.value = err.response?.data?.message || t('pages.inbox.resolveFailed')
  } finally {
    resolvingId.value = ''
  }
}

onMounted(loadInbox)
</script>

<template>
  <section
    class="xb-inbox-page xb-upload-page"
    :class="{ 'is-dragging': draggingFiles }"
    @dragenter.prevent="onDragEnter"
    @dragover.prevent="draggingFiles = true"
    @dragleave="onDragLeave"
    @drop.prevent="onFileDrop"
  >
    <PageHeader
      :title="t('pages.inbox.title')"
      :subtitle="pendingCount ? t('pages.inbox.subtitleBusy', { count: pendingCount }) : t('pages.inbox.subtitleClear')"
    >
      <button class="xb-secondary-button" type="button" :disabled="loading" @click="loadInbox">
        <RotateCcw :size="16" />
        {{ t('common.actions.refresh') }}
      </button>
      <label
        class="xb-upload-button"
        @dragenter.prevent="onDragEnter"
        @dragover.prevent="draggingFiles = true"
        @drop.prevent="onFileDrop"
      >
        <Upload :size="16" />
        {{ t('common.actions.upload') }}
        <input type="file" multiple @click="resetFileInput" @change="onFileChange" />
      </label>
    </PageHeader>

    <div v-if="uploadProgress" class="xb-progress xb-dashboard-upload-progress">
      <span :style="{ width: `${uploadProgress}%` }"></span>
    </div>
    <p v-if="message" class="xb-status-note is-success">{{ message }}</p>
    <p v-if="error" class="xb-status-note is-error">{{ error }}</p>

    <label
      class="xb-panel xb-inbox-dropzone"
      @dragenter.prevent="onDragEnter"
      @dragover.prevent="draggingFiles = true"
      @drop.prevent="onFileDrop"
    >
      <Upload :size="28" />
      <div>
        <strong>{{ t('pages.inbox.dropLabel') }}</strong>
        <span>{{ t('pages.inbox.dropDesc') }}</span>
      </div>
      <input type="file" multiple @click="resetFileInput" @change="onFileChange" />
    </label>

    <div v-if="loading" class="xb-empty-state">
      <strong>{{ t('pages.inbox.loadingTitle') }}</strong>
      <p>{{ t('pages.inbox.loadingSubtitle') }}</p>
    </div>

    <div v-else-if="!items.length" class="xb-empty-state">
      <Inbox :size="34" />
      <strong>{{ t('pages.inbox.clearTitle') }}</strong>
      <p>{{ t('pages.inbox.clearSubtitle') }}</p>
    </div>

    <section v-else class="xb-inbox-list">
      <article v-for="item in items" :key="item.id" class="xb-panel xb-inbox-item">
        <div class="xb-inbox-icon">
          <component :is="iconFor(item)" :size="24" />
        </div>
        <div class="xb-inbox-main">
          <div class="xb-inbox-title-row">
            <div>
              <strong>{{ item.file?.display_name || t('pages.inbox.fileDefaultName') }}</strong>
              <span>{{ item.file?.mime_type || item.file?.file_category || t('pages.files.noValue') }} / {{ formatBytes(item.file?.file_size) }}</span>
            </div>
            <time>{{ formatDate(item.created_at) }}</time>
          </div>
            <p>{{ item.suggestion_reason || t('pages.inbox.unresolved') }}</p>
          <div class="xb-inbox-actions">
            <button class="xb-secondary-button" type="button" :disabled="resolvingId === item.id || !item.file?.mime_type?.startsWith('image/')" @click="resolveItem(item, 'photo')">
              <Image :size="16" />
              {{ t('pages.inbox.saveAsPhoto') }}
            </button>
            <button class="xb-secondary-button" type="button" :disabled="resolvingId === item.id" @click="resolveItem(item, 'file')">
              <FileText :size="16" />
              {{ fileActionLabel(item) }}
            </button>
            <button class="xb-secondary-button" type="button" :disabled="resolvingId === item.id" @click="resolveItem(item, 'receipt')">
              <ReceiptText :size="16" />
              {{ t('pages.inbox.saveAsReceipt') }}
            </button>
            <button class="xb-secondary-button xb-danger-button" type="button" :disabled="resolvingId === item.id" @click="resolveItem(item, 'dismiss')">
              <Trash2 :size="16" />
              {{ t('pages.inbox.dismiss') }}
            </button>
          </div>
        </div>
        <CheckCircle2 v-if="item.suggested_type" class="xb-inbox-suggested" :size="18" />
      </article>
    </section>
  </section>
</template>
