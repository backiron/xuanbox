<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import QRCode from 'qrcode'
import { Check, Copy, Download, FileCheck, RefreshCw, Save, Send, Trash2 } from 'lucide-vue-next'
import PageHeader from '../../components/common/PageHeader.vue'
import EmptyState from '../../components/common/EmptyState.vue'
import { dropApi } from '../../api/dropApi'

const sessions = ref([])
const items = ref([])
const activeSession = ref(null)
const uploadUrl = ref('')
const qrCodeUrl = ref('')
const loading = ref(false)
const liveStatus = ref('Offline')
const copied = ref(false)
let eventSource = null

const configuredPublicOrigin = (import.meta.env.VITE_DROP_PUBLIC_ORIGIN || '').replace(/\/$/, '')
const isLocalhost = ['localhost', '127.0.0.1'].includes(window.location.hostname)

async function loadSessions() {
  const response = await dropApi.sessions()
  sessions.value = response.data.data
  if (!activeSession.value && sessions.value.length) {
    activeSession.value = sessions.value[0]
    await refreshUploadLink()
    await loadItems()
  }
}

async function createSession() {
  const title = window.prompt('Session name', 'Send to XuanBox') || 'Send to XuanBox'
  const response = await dropApi.createSession({ title, expires_in_minutes: 30 })
  activeSession.value = response.data.data
  await refreshUploadLink()
  await loadSessions()
  await loadItems()
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
    ? await QRCode.toDataURL(uploadUrl.value, {
        width: 240,
        margin: 2,
        errorCorrectionLevel: 'M'
      })
    : ''
}

async function loadItems() {
  if (!activeSession.value) return
  loading.value = true
  try {
    const response = await dropApi.items(activeSession.value.id)
    items.value = response.data.data
  } finally {
    loading.value = false
  }
}

function closeEvents() {
  if (eventSource) {
    eventSource.close()
    eventSource = null
  }
  liveStatus.value = 'Offline'
}

function connectEvents() {
  closeEvents()
  if (!activeSession.value) return
  eventSource = new EventSource(dropApi.eventUrl(activeSession.value.id))
  liveStatus.value = 'Connecting'
  eventSource.addEventListener('open', () => {
    liveStatus.value = 'Live'
  })
  eventSource.addEventListener('items', (event) => {
    items.value = JSON.parse(event.data || '[]')
    liveStatus.value = 'Live'
  })
  eventSource.addEventListener('error', () => {
    liveStatus.value = 'Reconnecting'
  })
}

async function saveItem(item, destination) {
  const payload = { destination }
  if (destination === 'receipts') {
    payload.merchant = window.prompt('Merchant', '') || null
    payload.category = window.prompt('Category', 'XuanDrop') || 'XuanDrop'
  }
  await dropApi.saveItem(item.id, payload)
  await loadItems()
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

async function deleteItem(item) {
  if (!window.confirm(`Delete ${item.original_filename}?`)) return
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
  connectEvents()
}

onMounted(async () => {
  await loadSessions()
  connectEvents()
})
onBeforeUnmount(closeEvents)
</script>

<template>
  <PageHeader title="XuanDrop" subtitle="Create a temporary upload session, open the link on a phone, then save incoming files to the vault.">
    <button class="xb-secondary-button" type="button" @click="loadItems">
      <RefreshCw :size="18" />
      Refresh
    </button>
    <button class="xb-primary-button" type="button" @click="createSession">
      <Send :size="18" />
      New Drop
    </button>
  </PageHeader>

  <section class="xb-drop-layout">
    <article class="xb-drop-zone">
      <Send :size="42" />
      <strong>{{ activeSession?.title || 'No active drop session' }}</strong>
      <p v-if="activeSession">Expires {{ new Date(activeSession.expires_at).toLocaleString() }}</p>
      <p v-else>Create a session to receive files from another device.</p>
      <div v-if="uploadUrl" class="xb-drop-link">
        <img :src="qrCodeUrl" alt="XuanDrop upload QR code" />
        <strong>Scan with your phone camera</strong>
        <span>{{ uploadUrl }}</span>
        <button class="xb-secondary-button" type="button" @click="copyUploadLink">
          <component :is="copied ? Check : Copy" :size="16" />
          {{ copied ? 'Copied' : 'Copy link' }}
        </button>
        <small v-if="!configuredPublicOrigin && isLocalhost">
          A phone cannot open localhost from this computer. Set DROP_PUBLIC_ORIGIN to this PC's LAN address, for example http://10.0.0.39:15173.
        </small>
      </div>
      <div v-else-if="activeSession" class="xb-drop-link">
        <strong>Link unavailable</strong>
        <span>This older session was created before QR links were persisted. Create a new Drop to get a scannable QR code.</span>
      </div>
    </article>

    <article class="xb-panel">
      <h3>Sessions</h3>
      <p class="xb-muted">Realtime: {{ liveStatus }}</p>
      <p v-if="sessions.length === 0">No sessions yet.</p>
      <button v-for="session in sessions" :key="session.id" class="xb-session-row" :class="{ 'is-active': activeSession?.id === session.id }" type="button" @click="selectSession(session)">
        <strong>{{ session.title }}</strong>
        <span>{{ session.status }} · {{ new Date(session.expires_at).toLocaleTimeString() }}</span>
      </button>
    </article>
  </section>

  <section class="xb-panel xb-drop-items">
    <h3>Received items</h3>
    <EmptyState v-if="!loading && items.length === 0" title="Nothing received yet" description="Open the upload link on another device and send a file." />
    <article v-for="item in items" :key="item.id" class="xb-file-row">
      <FileCheck :size="20" />
      <div class="xb-file-main">
        <strong>{{ item.original_filename }}</strong>
        <span>{{ item.mime_type || 'application/octet-stream' }} · {{ Math.ceil(item.file_size / 1024) }} KB · {{ item.status }}</span>
      </div>
      <div class="xb-row-actions">
        <button class="xb-text-button" type="button" @click="downloadItem(item)">
          <Download :size="16" />
          Download
        </button>
        <button class="xb-text-button" type="button" @click="saveItem(item, 'files')">
          <Save :size="16" />
          Files
        </button>
        <button class="xb-text-button" type="button" @click="saveItem(item, 'photos')">Photos</button>
        <button class="xb-text-button" type="button" @click="saveItem(item, 'receipts')">Receipts</button>
        <button class="xb-text-button xb-danger-button" type="button" @click="deleteItem(item)">
          <Trash2 :size="16" />
          Delete
        </button>
      </div>
    </article>
  </section>
</template>
