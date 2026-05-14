<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import QRCode from 'qrcode'
import { Check, Copy, Download, FileCheck, QrCode, RefreshCw, Save, Send, Smartphone, Trash2, Upload, Wifi, X } from 'lucide-vue-next'
import PageHeader from '../../components/common/PageHeader.vue'
import EmptyState from '../../components/common/EmptyState.vue'
import { dropApi } from '../../api/dropApi'
import { useDialogStore } from '../../stores/dialogStore'

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
      newItems.length === 1 ? 'New file received' : `${newItems.length} files received`,
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
    pageError.value = getErrorMessage(error, 'Could not load XuanDrop sessions.')
    notify('Session load failed', pageError.value)
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
    title: 'New XuanDrop',
    label: 'Session name',
    defaultValue: 'Send to XuanBox'
  }) || 'Send to XuanBox'
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

async function uploadLocalFiles(event) {
  const files = Array.from(event.target.files || [])
  event.target.value = ''
  if (!files.length) return
  const session = await ensureSession()
  const token = session?.public_token || session?.token
  if (!token) {
    notify('No active Drop', 'Create or select a session before sending files.')
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
    notify('Files sent', `${files.length} item${files.length === 1 ? '' : 's'} added to ${session.title}`)
    await loadItems()
  } catch (error) {
    notify('Upload failed', getErrorMessage(error, 'The selected files could not be sent.'))
  } finally {
    uploading.value = false
    uploadProgress.value = 0
  }
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
    payload.merchant = await dialog.prompt({ title: 'Receipt merchant', label: 'Merchant', placeholder: 'Store name' }) || null
    payload.category = await dialog.prompt({ title: 'Receipt category', label: 'Category', defaultValue: 'XuanDrop' }) || 'XuanDrop'
  }
  setSaving(item.id, true)
  try {
    await dropApi.saveItem(item.id, payload)
    if (previewItem.value?.id === item.id) closePreview()
    notify('Item saved', `${item.original_filename} saved to ${destination}`)
    await loadItems()
  } catch (error) {
    notify('Save failed', error.response?.data?.message || 'This item could not be saved.')
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
    title: 'Delete received item',
    message: `${item.original_filename} will be removed from this transfer session.`,
    confirmText: 'Delete',
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
  <PageHeader title="XuanDrop" subtitle="Scan, receive, and route nearby device uploads without leaving this screen.">
    <button class="xb-secondary-button" type="button" @click="refreshSessions">
      <RefreshCw :size="18" />
      Refresh
    </button>
    <button class="xb-primary-button" type="button" @click="createSession">
      <Send :size="18" />
      New Drop
    </button>
  </PageHeader>

  <div class="xb-drop-livebar" :class="{ 'is-visible': toast }">
    <span class="xb-livebar-pulse"></span>
    <strong>{{ toast?.message || `${liveStatus} transfer channel` }}</strong>
    <span>{{ toast?.detail || (latestItem ? `Latest: ${latestItem.original_filename}` : 'Waiting for incoming files') }}</span>
  </div>

  <p v-if="pageError" class="xb-form-error xb-drop-error">{{ pageError }}</p>

  <section class="xb-drop-layout">
    <article class="xb-drop-zone">
      <div class="xb-drop-session-head">
        <div>
          <span class="xb-drop-kicker"><Wifi :size="15" /> {{ liveStatus }}</span>
          <strong>{{ activeSession?.title || 'No active drop session' }}</strong>
          <p v-if="activeSession">Expires {{ new Date(activeSession.expires_at).toLocaleString() }}</p>
          <p v-else>Create a session to receive files from another device.</p>
        </div>
        <div class="xb-drop-count">
          <strong>{{ items.length }}</strong>
          <span>received</span>
        </div>
      </div>

      <div v-if="uploadUrl" class="xb-drop-link">
        <div class="xb-drop-qr-shell">
          <img :src="qrCodeUrl" alt="XuanDrop upload QR code" />
        </div>
        <div class="xb-drop-link-copy">
          <QrCode :size="18" />
          <strong>Scan to send files</strong>
          <span>{{ uploadUrl }}</span>
          <div class="xb-row-actions">
            <button class="xb-secondary-button" type="button" @click="copyUploadLink">
              <component :is="copied ? Check : Copy" :size="16" />
              {{ copied ? 'Copied' : 'Copy link' }}
            </button>
            <router-link class="xb-text-button" to="/files">Open vault</router-link>
          </div>
          <small v-if="!configuredPublicOrigin && isLocalhost">A phone cannot open localhost from this computer. Set DROP_PUBLIC_ORIGIN to this PC's LAN address.</small>
        </div>
      </div>

      <div v-else-if="activeSession" class="xb-drop-link">
        <strong>Link unavailable</strong>
        <span>Create a new Drop to get a scannable QR code.</span>
      </div>

      <label class="xb-drop-upload-target" :class="{ 'is-disabled': !activeSession || uploading }">
        <Upload :size="22" />
        <strong>{{ uploading ? 'Sending files' : 'Send from this device' }}</strong>
        <span>{{ activeSession ? 'Choose files here, then open this XuanDrop session on your phone to download or save them.' : 'Create a session before choosing files.' }}</span>
        <div v-if="uploadProgress" class="xb-progress">
          <span :style="{ width: `${uploadProgress}%` }"></span>
        </div>
        <input type="file" multiple :disabled="!activeSession || uploading" @change="uploadLocalFiles" />
      </label>
    </article>

    <article class="xb-panel xb-drop-side">
      <div class="xb-panel-title">
        <h3>Sessions</h3>
        <span>{{ sessions.length }}</span>
      </div>
      <p v-if="sessions.length === 0">No active sessions.</p>
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
      <h3>Received items</h3>
      <span>{{ receivedItems.length }} stored</span>
    </div>
    <EmptyState v-if="!loading && receivedItems.length === 0" title="Nothing received yet" description="Open the upload link on another device and send a file. New files are stored automatically." />
    <article v-for="item in receivedItems" :key="item.id" class="xb-file-row xb-drop-item-row">
      <button class="xb-drop-file-icon" type="button" :title="isImageItem(item) ? 'Preview image' : 'Download file'" @click="openItem(item)">
        <FileCheck :size="18" />
      </button>
      <div class="xb-file-main">
        <button class="xb-drop-file-open" type="button" @click="openItem(item)">{{ item.original_filename }}</button>
        <span>{{ item.mime_type || 'application/octet-stream' }} · {{ formatSize(item.file_size) }} · stored in {{ item.saved_to || 'Files' }}</span>
      </div>
      <div class="xb-row-actions">
        <button class="xb-text-button" type="button" @click="downloadItem(item)">
          <Download :size="16" />
          Download
        </button>
        <button v-if="item.status !== 'saved'" class="xb-text-button" type="button" :disabled="savingIds.has(item.id)" @click="saveItem(item, 'files')">
          <Save :size="16" />
          {{ savingIds.has(item.id) ? 'Saving' : 'Files' }}
        </button>
        <button v-if="item.status !== 'saved' && isImageItem(item)" class="xb-text-button" type="button" :disabled="savingIds.has(item.id)" @click="saveItem(item, 'photos')">
          <Smartphone :size="16" />
          Photos
        </button>
        <button v-if="item.status !== 'saved'" class="xb-text-button" type="button" :disabled="savingIds.has(item.id)" @click="saveItem(item, 'receipts')">Receipts</button>
        <button class="xb-text-button xb-danger-button" type="button" @click="deleteItem(item)">
          <Trash2 :size="16" />
          Delete
        </button>
      </div>
    </article>
  </section>

  <div v-if="previewItem" class="xb-preview-backdrop" @click.self="closePreview">
    <article class="xb-preview-modal">
      <div class="xb-panel-title">
        <h3>{{ previewItem.original_filename }}</h3>
        <button class="xb-icon-button" type="button" title="Close preview" @click="closePreview">
          <X :size="18" />
        </button>
      </div>
      <img :src="previewUrl" alt="" />
      <div class="xb-row-actions">
        <button class="xb-secondary-button" type="button" @click="downloadItem(previewItem)">
          <Download :size="16" />
          Download
        </button>
        <button class="xb-primary-button" type="button" :disabled="savingIds.has(previewItem.id)" @click="saveItem(previewItem, 'photos')">
          <Smartphone :size="16" />
          {{ savingIds.has(previewItem.id) ? 'Saving' : 'Save to Photos' }}
        </button>
      </div>
    </article>
  </div>
</template>
