<script setup>
import { onMounted, ref } from 'vue'
import { FileCheck, QrCode, RefreshCw, Save, Send } from 'lucide-vue-next'
import PageHeader from '../../components/common/PageHeader.vue'
import EmptyState from '../../components/common/EmptyState.vue'
import { dropApi } from '../../api/dropApi'

const sessions = ref([])
const items = ref([])
const activeSession = ref(null)
const lastUploadUrl = ref('')
const loading = ref(false)

async function loadSessions() {
  const response = await dropApi.sessions()
  sessions.value = response.data.data
  if (!activeSession.value && sessions.value.length) {
    activeSession.value = sessions.value[0]
    await loadItems()
  }
}

async function createSession() {
  const title = window.prompt('Session name', 'Send to XuanBox') || 'Send to XuanBox'
  const response = await dropApi.createSession({ title, expires_in_minutes: 30 })
  activeSession.value = response.data.data
  lastUploadUrl.value = `${window.location.origin}/drop/public/${activeSession.value.token}`
  await loadSessions()
  await loadItems()
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

async function saveItem(item, destination) {
  const payload = { destination }
  if (destination === 'receipts') {
    payload.merchant = window.prompt('Merchant', '') || null
    payload.category = window.prompt('Category', 'XuanDrop') || 'XuanDrop'
  }
  await dropApi.saveItem(item.id, payload)
  await loadItems()
}

function selectSession(session) {
  activeSession.value = session
  lastUploadUrl.value = ''
  loadItems()
}

onMounted(loadSessions)
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
      <div v-if="lastUploadUrl" class="xb-drop-link">
        <QrCode :size="72" />
        <strong>Open on mobile</strong>
        <span>{{ lastUploadUrl }}</span>
      </div>
    </article>

    <article class="xb-panel">
      <h3>Sessions</h3>
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
        <button class="xb-text-button" type="button" @click="saveItem(item, 'files')">
          <Save :size="16" />
          Files
        </button>
        <button class="xb-text-button" type="button" @click="saveItem(item, 'photos')">Photos</button>
        <button class="xb-text-button" type="button" @click="saveItem(item, 'receipts')">Receipts</button>
      </div>
    </article>
  </section>
</template>
