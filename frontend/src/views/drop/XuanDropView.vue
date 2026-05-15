<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import QRCode from 'qrcode'
import { useI18n } from 'vue-i18n'
import { Check, Copy, Download, FileCheck, QrCode, RefreshCw, Save, Send, Smartphone, Trash2, Upload, Wifi, X } from 'lucide-vue-next'
import PageHeader from '../../components/common/PageHeader.vue'
import EmptyState from '../../components/common/EmptyState.vue'
import { dropApi } from '../../api/dropApi'
import { useDialogStore } from '../../stores/dialogStore'
import { findUploadLimitError } from '../../utils/uploadLimits'

const { t } = useI18n()
const sessions = ref([])
const items = ref([])
const activeSession = ref(null)
const uploadUrl = ref('')
const qrCodeUrl = ref('')
const loading = ref(false)
const liveStatus = ref('Offline')
const copied = ref(false)
const toast = ref(null)
const previewItem = ref(null)
const previewUrl = ref('')
const pageError = ref('')
const uploadProgress = ref(0)
const uploading = ref(false)
const draggingLocalFiles = ref(false)
const lastItemIds = ref(new Set())
const savingIds = ref(new Set())
const notificationsArmed = ref(false)
const dialog = useDialogStore()
let eventSource = null
let toastTimer = null
let pollTimer = null
let sessionTimer = null

const configuredPublicOrigin = (import.meta.env.VITE_DROP_PUBLIC_ORIGIN || '').replace(/\/$/, '')
const isLocalhost = ['localhost', '127.0.0.1'].includes(window.location.hostname)
const latestItem = computed(() => items.value[0])
const receivedItems = computed(() => items.value)

function formatTime(value) {
  if (!value) return ''
  return new Date(value).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

function formatSize(bytes) {
  if (!bytes) return '0 KB'
  if (bytes < 1024 * 1024) return `${Math.ceil(bytes / 1024)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

function notify(message, detail = '') {
  toast.value = { message, detail }
  window.clearTimeout(toastTimer)
  toastTimer = window.setTimeout(() => {
    toast.value = null
  }, 9000)
}

function getErrorMessage(error, fallback = 'Something went wrong.') {
  return error.response?.data?.error?.message || error.response?.data?.message || fallback
}

function setItems(nextItems, announce = false) {
  const previousIds = lastItemIds.value
  const newItems = nextItems.filter((item) => !previousIds.has(item.id))
  items.value = nextItems
  lastItemIds.value = new Set(nextItems.map((item) => item.id))

  if (!notificationsArmed.value) return
  if (announce && newItems.length) {
    notify(
      newItems.length === 1 ? t('pages.drop.newFileReceived') : t('pages.drop.filesReceived', { count: newItems.length }),
      newItems[0].original_filename
    )
  }
}

async function loadSessions() {
  pageError.value = ''
  try {
    const response = await dropApi.sessions()
    sessions.value = response.data.data
    const activeStillAvailable = sessions.value.some((session) => session.id === activeSession.value?.id)
    if (!activeStillAvailable) {
      activeSession.value = sessions.value[0] || null
      items.value = []
      lastItemIds.value = new Set()
      if (activeSession.value) await loadItems()
    } else if (activeSession.value) {
      activeSession.value = sessions.value.find((session) => session.id === activeSession.value.id) || activeSession.value
    }
    if (activeSession.value) {
      await refreshUploadLink()
    } else {
      uploadUrl.value = ''
      qrCodeUrl.value = ''
    }
  } catch (error) {
    pageError.value = getErrorMessage(error, t('pages.drop.newSessionFailed'))
    notify(t('pages.drop.sessionLoadFailed'), pageError.value)
    throw error
  }
}

async function refreshSessions() {
  await loadSessions()
  if (activeSession.value) await loadItems()
  if (activeSession.value) await connectEvents()
}

async function ensureSession() {
  if (activeSession.value) return activeSession.value
  if (sessions.value.length) {
    activeSession.value = sessions.value[0]
    await refreshUploadLink()
    await loadItems()
    await connectEvents()
    return activeSession.value
  }
  return null
}

async function createSession() {
  const title = await dialog.prompt({
    title: t('pages.drop.newDrop'),
    label: t('pages.drop.sessionName'),
    defaultValue: t('pages.drop.defaultSessionName')
  }) || t('pages.drop.defaultSessionName')
  const response = await dropApi.createSession({ title, expires_in_minutes: 30 })
  activeSession.value = response.data.data
  items.value = []
  lastItemIds.value = new Set()
  await refreshUploadLink()
  await loadSessions()
  await loadItems()
  await connectEvents()
}

function buildUploadUrl(session) {
  const token = session?.public_token || session?.token
  if (!token) return ''
  const origin = configuredPublicOrigin || window.location.origin
  return `${origin}/drop/public/${token}`
}

async function refreshUploadLink() {
  uploadUrl.value = buildUploadUrl(activeSession.value)
  copied.value = false
  qrCodeUrl.value = uploadUrl.value
    ? await QRCode.toDataURL(uploadUrl.value, { width: 168, margin: 2, errorCorrectionLevel: 'M' })
    : ''
}

async function loadItems() {
  if (!activeSession.value) return
  loading.value = true
  try {
    const response = await dropApi.items(activeSession.value.id)
    setItems(response.data.data)
  } finally {
    loading.value = false
  }
}

async function pollItems() {
  if (!activeSession.value) {
    await loadSessions()
    return
  }
  try {
    const response = await dropApi.items(activeSession.value.id)
    setItems(response.data.data, true)
    liveStatus.value = eventSource ? liveStatus.value : 'Polling'
  } catch (error) {
    liveStatus.value = 'Reconnecting'
  }
}

function startPolling() {
  window.clearInterval(pollTimer)
  pollTimer = window.setInterval(pollItems, 3000)
}

function startSessionRefresh() {
  window.clearInterval(sessionTimer)
  sessionTimer = window.setInterval(loadSessions, 5000)
}

async function uploadLocalFileList(fileList) {
  const files = Array.from(fileList || [])
  if (!files.length) return
  const limitError = findUploadLimitError(files, t)
  if (limitError) {
    notify(t('pages.drop.uploadFailed'), limitError)
    return
  }
  const session = await ensureSession()
  const token = session?.public_token || session?.token
  if (!token) {
    notify(t('pages.drop.noActiveDrop'), t('pages.drop.selectSessionFirst'))
    return
  }

  uploading.value = true
  uploadProgress.value = 0
  try {
    for (const file of files) {
      const formData = new FormData()
      formData.append('file', file)
      await dropApi.publicUpload(token, formData, {
        onUploadProgress(progressEvent) {
          if (progressEvent.total) uploadProgress.value = Math.round((progressEvent.loaded / progressEvent.total) * 100)
        }
      })
    }
    uploadProgress.value = 0
    notify(t('pages.drop.filesSent'), t('pages.drop.filesSentDetail', { count: files.length, title: session.title }))
    await loadItems()
  } catch (error) {
    notify(t('pages.drop.uploadFailed'), getErrorMessage(error, t('pages.drop.uploadFailedDetail')))
  } finally {
    uploading.value = false
    uploadProgress.value = 0
  }
}

async function uploadLocalFiles(event) {
  await uploadLocalFileList(event.target.files)
  event.target.value = ''
}

function onLocalDragEnter(event) {
  if (!event.dataTransfer?.types?.includes('Files') || uploading.value || !activeSession.value) return
  draggingLocalFiles.value = true
}

function onLocalDragLeave(event) {
  if (event.currentTarget.contains(event.relatedTarget)) return
  draggingLocalFiles.value = false
}

async function onLocalFileDrop(event) {
  draggingLocalFiles.value = false
  if (uploading.value || !activeSession.value) return
  await uploadLocalFileList(event.dataTransfer?.files)
}

function closeEvents() {
  if (eventSource) {
    eventSource.close()
    eventSource = null
  }
  liveStatus.value = 'Offline'
}

async function connectEvents() {
  closeEvents()
  if (!activeSession.value) return
  await dropApi.authorizeEvents(activeSession.value.id)
  eventSource = new EventSource(dropApi.eventUrl(activeSession.value.id))
  liveStatus.value = 'Connecting'
  eventSource.addEventListener('open', () => {
    liveStatus.value = 'Live'
    notificationsArmed.value = true
  })
  eventSource.addEventListener('items', (event) => {
    const nextItems = JSON.parse(event.data || '[]')
    setItems(nextItems, true)
    liveStatus.value = 'Live'
  })
  eventSource.addEventListener('error', () => {
    liveStatus.value = 'Reconnecting'
  })
}

async function saveItem(item, destination) {
  if (savingIds.value.has(item.id)) return
  const payload = { destination }
  if (destination === 'receipts') {
    payload.merchant = await dialog.prompt({ title: t('pages.drop.receiptMerchant'), label: t('pages.receipts.merchant'), placeholder: t('pages.drop.storeName') }) || null
    payload.category = await dialog.prompt({ title: t('pages.drop.receiptCategory'), label: t('pages.receipts.category'), defaultValue: 'XuanDrop' }) || 'XuanDrop'
  }
  setSaving(item.id, true)
  try {
    await dropApi.saveItem(item.id, payload)
    if (previewItem.value?.id === item.id) closePreview()
    notify(t('pages.drop.itemSaved'), t('pages.drop.filesSaved', { name: item.original_filename, destination }))
    await loadItems()
  } catch (error) {
    notify(t('pages.drop.saveFailed'), error.response?.data?.message || t('pages.drop.saveFail'))
  } finally {
    setSaving(item.id, false)
  }
}

async function downloadItem(item) {
  const response = await dropApi.downloadItem(item.id)
  const url = URL.createObjectURL(response.data)
  const link = document.createElement('a')
  link.href = url
  link.download = item.original_filename
  link.click()
  URL.revokeObjectURL(url)
}

function isImageItem(item) {
  return item.mime_type?.startsWith('image/')
}

function setSaving(itemId, isSaving) {
  const next = new Set(savingIds.value)
  if (isSaving) next.add(itemId)
  else next.delete(itemId)
  savingIds.value = next
}

async function openItem(item) {
  if (!isImageItem(item)) {
    await downloadItem(item)
    return
  }
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
  const response = await dropApi.downloadItem(item.id)
  previewItem.value = item
  previewUrl.value = URL.createObjectURL(response.data)
}

function closePreview() {
  previewItem.value = null
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
  previewUrl.value = ''
}

async function deleteItem(item) {
  const confirmed = await dialog.confirm({
    title: t('pages.drop.deleteItemTitle'),
    message: t('pages.drop.deleteItemMessage', { name: item.original_filename }),
    confirmText: t('common.actions.delete'),
    danger: true
  })
  if (!confirmed) return
  await dropApi.deleteItem(item.id)
  await loadItems()
}

async function copyUploadLink() {
  if (!uploadUrl.value) return
  await navigator.clipboard.writeText(uploadUrl.value)
  copied.value = true
  window.setTimeout(() => {
    copied.value = false
  }, 1500)
}

async function selectSession(session) {
  activeSession.value = session
  await refreshUploadLink()
  await loadItems()
  await connectEvents()
}

onMounted(async () => {
  try {
    await loadSessions()
    notificationsArmed.value = true
    startPolling()
    startSessionRefresh()
    await connectEvents()
  } catch {
    closeEvents()
    notificationsArmed.value = true
    startPolling()
    startSessionRefresh()
  }
})
onBeforeUnmount(() => {
  closeEvents()
  closePreview()
  window.clearTimeout(toastTimer)
  window.clearInterval(pollTimer)
  window.clearInterval(sessionTimer)
})
</script>

<template>
  <PageHeader :title="t('pages.drop.title')" :subtitle="t('pages.drop.subtitle')">
    <button class="xb-secondary-button" type="button" @click="refreshSessions">
      <RefreshCw :size="18" />
      {{ t('common.actions.refresh') }}
    </button>
    <button class="xb-primary-button" type="button" @click="createSession">
      <Send :size="18" />
      {{ t('pages.drop.newDrop') }}
    </button>
  </PageHeader>

  <div class="xb-drop-livebar" :class="{ 'is-visible': toast }">
    <span class="xb-livebar-pulse"></span>
    <strong>{{ toast?.message || t('pages.drop.transferChannel', { status: liveStatus }) }}</strong>
    <span>{{ toast?.detail || (latestItem ? t('pages.drop.receiveLatest', { name: latestItem.original_filename }) : t('pages.drop.waiting')) }}</span>
  </div>

  <p v-if="pageError" class="xb-form-error xb-drop-error">{{ pageError }}</p>

  <section class="xb-drop-layout">
    <article class="xb-drop-zone">
      <div class="xb-drop-session-head">
        <div>
          <span class="xb-drop-kicker"><Wifi :size="15" /> {{ liveStatus }}</span>
          <strong>{{ activeSession?.title || t('pages.drop.noSession') }}</strong>
          <p v-if="activeSession">{{ t('pages.drop.expires', { date: new Date(activeSession.expires_at).toLocaleString() }) }}</p>
          <p v-else>{{ t('pages.drop.createSessionHint') }}</p>
        </div>
        <div class="xb-drop-count">
          <strong>{{ items.length }}</strong>
          <span>{{ t('pages.drop.receiveCount') }}</span>
        </div>
      </div>

      <div v-if="uploadUrl" class="xb-drop-link">
        <div class="xb-drop-qr-shell">
          <img :src="qrCodeUrl" alt="XuanDrop upload QR code" />
        </div>
        <div class="xb-drop-link-copy">
          <QrCode :size="18" />
          <strong>{{ t('pages.drop.scanToSend') }}</strong>
          <span>{{ uploadUrl }}</span>
          <div class="xb-row-actions">
            <button class="xb-secondary-button" type="button" @click="copyUploadLink">
              <component :is="copied ? Check : Copy" :size="16" />
              {{ copied ? t('pages.drop.copied') : t('pages.drop.copyLink') }}
            </button>
            <router-link class="xb-text-button" to="/files">{{ t('pages.drop.openVault') }}</router-link>
          </div>
          <small v-if="!configuredPublicOrigin && isLocalhost">{{ t('pages.drop.noDeviceWarning') }}</small>
        </div>
      </div>

      <div v-else-if="activeSession" class="xb-drop-link">
        <strong>{{ t('pages.drop.sessionUnavailable') }}</strong>
        <span>{{ t('pages.drop.sessionUnavailableHint') }}</span>
      </div>

      <label
        class="xb-drop-upload-target"
        :class="{ 'is-disabled': !activeSession || uploading, 'is-dragging': draggingLocalFiles }"
        @dragenter.prevent="onLocalDragEnter"
        @dragover.prevent="draggingLocalFiles = Boolean(activeSession) && !uploading"
        @dragleave="onLocalDragLeave"
        @drop.prevent="onLocalFileDrop"
      >
        <Upload :size="22" />
        <strong>{{ uploading ? t('pages.drop.sending') : t('pages.drop.sendHere') }}</strong>
        <span>{{ activeSession ? t('pages.drop.sendElse') : t('pages.drop.sendHintNoSession') }}</span>
        <div v-if="uploadProgress" class="xb-progress">
          <span :style="{ width: `${uploadProgress}%` }"></span>
        </div>
        <input type="file" multiple :disabled="!activeSession || uploading" @change="uploadLocalFiles" />
      </label>
    </article>

    <article class="xb-panel xb-drop-side">
      <div class="xb-panel-title">
        <h3>{{ t('pages.drop.sessionsTitle') }}</h3>
        <span>{{ sessions.length }}</span>
      </div>
      <p v-if="sessions.length === 0">{{ t('pages.drop.noActiveSessions') }}</p>
      <div class="xb-drop-session-list">
        <button v-for="session in sessions" :key="session.id" class="xb-session-row" :class="{ 'is-active': activeSession?.id === session.id }" type="button" @click="selectSession(session)">
          <strong>{{ session.title }}</strong>
          <span>{{ session.status }} · {{ formatTime(session.expires_at) }}</span>
        </button>
      </div>
    </article>
  </section>

  <section class="xb-panel xb-drop-items">
    <div class="xb-panel-title">
      <h3>{{ t('pages.drop.receivedItems') }}</h3>
      <span>{{ t('pages.drop.storedCount', { count: receivedItems.length }) }}</span>
    </div>
    <EmptyState v-if="!loading && receivedItems.length === 0" :title="t('pages.drop.noReceived')" :description="t('pages.drop.noReceivedHint')" />
    <article v-for="item in receivedItems" :key="item.id" class="xb-file-row xb-drop-item-row">
      <button class="xb-drop-file-icon" type="button" :title="isImageItem(item) ? t('pages.drop.previewImage') : t('pages.drop.downloadFile')" @click="openItem(item)">
        <FileCheck :size="18" />
      </button>
      <div class="xb-file-main">
        <button class="xb-drop-file-open" type="button" @click="openItem(item)">{{ item.original_filename }}</button>
        <span>{{ item.mime_type || 'application/octet-stream' }} · {{ formatSize(item.file_size) }} · {{ t('pages.drop.storedIn', { destination: item.saved_to || t('pages.drop.files') }) }}</span>
      </div>
      <div class="xb-row-actions">
        <button class="xb-text-button" type="button" @click="downloadItem(item)">
          <Download :size="16" />
          {{ t('common.actions.download') }}
        </button>
        <button v-if="item.status !== 'saved'" class="xb-text-button" type="button" :disabled="savingIds.has(item.id)" @click="saveItem(item, 'files')">
          <Save :size="16" />
          {{ savingIds.has(item.id) ? t('pages.drop.saving') : t('pages.drop.files') }}
        </button>
        <button v-if="item.status !== 'saved' && isImageItem(item)" class="xb-text-button" type="button" :disabled="savingIds.has(item.id)" @click="saveItem(item, 'photos')">
          <Smartphone :size="16" />
          {{ t('routes.photos') }}
        </button>
        <button v-if="item.status !== 'saved'" class="xb-text-button" type="button" :disabled="savingIds.has(item.id)" @click="saveItem(item, 'receipts')">{{ t('routes.receipts') }}</button>
        <button class="xb-text-button xb-danger-button" type="button" @click="deleteItem(item)">
          <Trash2 :size="16" />
          {{ t('common.actions.delete') }}
        </button>
      </div>
    </article>
  </section>

  <div v-if="previewItem" class="xb-preview-backdrop" @click.self="closePreview">
    <article class="xb-preview-modal">
      <div class="xb-panel-title">
        <h3>{{ previewItem.original_filename }}</h3>
        <button class="xb-icon-button" type="button" :title="t('common.actions.close')" @click="closePreview">
          <X :size="18" />
        </button>
      </div>
      <img :src="previewUrl" alt="" />
      <div class="xb-row-actions">
        <button class="xb-secondary-button" type="button" @click="downloadItem(previewItem)">
          <Download :size="16" />
          {{ t('common.actions.download') }}
        </button>
        <button class="xb-primary-button" type="button" :disabled="savingIds.has(previewItem.id)" @click="saveItem(previewItem, 'photos')">
          <Smartphone :size="16" />
          {{ savingIds.has(previewItem.id) ? t('pages.drop.saving') : t('pages.drop.saveToPhotos') }}
        </button>
      </div>
    </article>
  </div>
</template>
