<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Bell, BellRing, ChevronLeft, Laptop, Pencil, QrCode, Smartphone, Trash2, UserMinus, Users, X } from 'lucide-vue-next'
import { dropChatApi } from '../../api/dropChatApi'
import { useDropSocket } from '../../composables/useDropSocket'
import { useDialogStore } from '../../stores/dialogStore'
import { deliverFile, fetchMessageFile, forgetMessage, formatSize } from '../../utils/dropMedia'
import { defaultDeviceName } from '../../utils/deviceIdentity'
import DropComposer from '../../components/drop/DropComposer.vue'
import DropContactsPanel from '../../components/drop/DropContactsPanel.vue'
import DropMessageBubble from '../../components/drop/DropMessageBubble.vue'
import DropQrDialog from '../../components/drop/DropQrDialog.vue'

const RETENTION_DAYS = 7
const PAGE_SIZE = 50

const { t } = useI18n()
const dialog = useDialogStore()

const me = ref(null)
const threads = ref([])
const contacts = ref([])
const activeThreadId = ref('')
const messagesByThread = reactive({})
const hasMoreByThread = reactive({})
const pendingByThread = reactive({})
const savingIds = ref(new Set())
const target = ref('')
const pageError = ref('')
const showQr = ref(false)
const showContacts = ref(false)
const dragging = ref(false)
const preview = reactive({ message: null, url: '', file: null, loading: false })
const toast = ref(null)
const notificationPermission = ref(typeof Notification === 'undefined' ? 'unsupported' : Notification.permission)
const isMobile = ref(window.matchMedia('(max-width: 840px)').matches)
const scroller = ref(null)
let toastTimer = null
let readTimer = null
const originalTitle = document.title

const socket = useDropSocket(handleEvent)

// ---------------------------------------------------------------- derived state

const myUserId = computed(() => me.value?.user?.id || '')
const currentDeviceId = computed(() => me.value?.current_device_id || '')
const devices = computed(() => me.value?.devices || [])
const deviceNames = computed(() => Object.fromEntries(devices.value.map((device) => [device.id, device.device_name])))
const otherDevices = computed(() => devices.value.filter((device) => !device.is_current))
const activeThread = computed(() => threads.value.find((thread) => thread.id === activeThreadId.value) || null)
const acceptedContacts = computed(() => contacts.value.filter((contact) => contact.status === 'accepted'))
const pendingIncoming = computed(() => contacts.value.filter((contact) => contact.status === 'pending' && contact.direction === 'incoming').length)
const totalUnread = computed(() => threads.value.reduce((sum, thread) => sum + (thread.unread_count || 0), 0))

// Self thread first, then every accepted contact (with or without an existing conversation).
const conversationList = computed(() => {
  const list = []
  const self = threads.value.find((thread) => thread.kind === 'self')
  if (self) list.push({ key: self.id, thread: self, title: t('pages.xuandrop.myDevices'), self: true })
  const direct = threads.value.filter((thread) => thread.kind === 'direct')
  const seenPeers = new Set()
  for (const thread of direct) {
    seenPeers.add(thread.peer?.id)
    list.push({ key: thread.id, thread, title: thread.peer?.display_name || '?', peer: thread.peer })
  }
  for (const contact of acceptedContacts.value) {
    if (!seenPeers.has(contact.peer?.id)) list.push({ key: `contact-${contact.id}`, thread: null, title: contact.peer?.display_name, peer: contact.peer })
  }
  return list
})

const activeMessages = computed(() => messagesByThread[activeThreadId.value] || [])
const activePending = computed(() => pendingByThread[activeThreadId.value] || [])
const peerLastReadAt = computed(() => activeThread.value?.peer_last_read_at || null)

const timeline = computed(() => {
  const rows = []
  let lastDay = ''
  for (const message of activeMessages.value) {
    const day = new Date(message.created_at).toDateString()
    if (day !== lastDay) {
      rows.push({ type: 'day', key: `day-${day}`, label: dayLabel(message.created_at) })
      lastDay = day
    }
    rows.push({ type: 'message', key: message.id, message })
  }
  return rows
})

const connectionLabel = computed(() => ({
  online: t('pages.xuandrop.live'),
  connecting: t('pages.xuandrop.connecting'),
  reconnecting: t('pages.xuandrop.reconnecting'),
  offline: t('pages.xuandrop.offline')
}[socket.status.value]))

watch(totalUnread, (count) => {
  document.title = count ? `(${count}) ${originalTitle}` : originalTitle
})

// ---------------------------------------------------------------- helpers

function dayLabel(value) {
  const date = new Date(value)
  const today = new Date()
  const yesterday = new Date(Date.now() - 86400000)
  if (date.toDateString() === today.toDateString()) return t('pages.xuandrop.today')
  if (date.toDateString() === yesterday.toDateString()) return t('pages.xuandrop.yesterday')
  return date.toLocaleDateString()
}

function errorMessage(error) {
  return error.response?.data?.message || error.message || t('pages.xuandrop.loadFailed')
}

function notify(message, detail = '') {
  toast.value = { message, detail }
  window.clearTimeout(toastTimer)
  toastTimer = window.setTimeout(() => { toast.value = null }, 6000)
}

function isMine(message) {
  if (message.sender_user_id !== myUserId.value) return false
  if (activeThread.value?.kind === 'self') return message.sender_device_id === currentDeviceId.value
  return true
}

function senderLabel(message, thread = activeThread.value) {
  if (message.sender_label) return message.sender_label.startsWith('QR') ? t('pages.xuandrop.fromQr') : message.sender_label
  if (thread?.kind === 'self') {
    if (message.sender_device_id === currentDeviceId.value) return t('pages.xuandrop.thisDevice')
    return deviceNames.value[message.sender_device_id] || t('pages.xuandrop.otherDevice')
  }
  return message.sender_user_id === myUserId.value ? '' : thread?.peer?.display_name || ''
}

function targetLabel(message) {
  if (!message.target_device_id) return ''
  if (message.target_device_id === currentDeviceId.value) return t('pages.xuandrop.thisDevice')
  return deviceNames.value[message.target_device_id] || t('pages.xuandrop.otherDevice')
}

function isRead(message) {
  if (activeThread.value?.kind !== 'direct' || message.sender_user_id !== myUserId.value || !peerLastReadAt.value) return false
  return new Date(peerLastReadAt.value) >= new Date(message.created_at)
}

function previewText(message) {
  if (!message) return ''
  return message.kind === 'text' ? message.body : `📎 ${message.filename}`
}

function isNearBottom() {
  const element = scroller.value
  return !element || element.scrollHeight - element.scrollTop - element.clientHeight < 120
}

async function scrollToBottom(force = false) {
  if (!force && !isNearBottom()) return
  await nextTick()
  if (scroller.value) scroller.value.scrollTop = scroller.value.scrollHeight
}

function upsertMessage(threadId, message) {
  const list = messagesByThread[threadId]
  if (!list) return
  const index = list.findIndex((item) => item.id === message.id)
  if (index >= 0) list.splice(index, 1, { ...list[index], ...message, saved_to: message.saved_to ?? list[index].saved_to })
  else list.push(message)
  const pending = pendingByThread[threadId]
  if (pending && message.client_id) {
    const pendingIndex = pending.findIndex((item) => item.clientId === message.client_id)
    if (pendingIndex >= 0) {
      if (pending[pendingIndex].previewUrl) URL.revokeObjectURL(pending[pendingIndex].previewUrl)
      pending.splice(pendingIndex, 1)
    }
  }
}

// ---------------------------------------------------------------- loading

async function loadMe() {
  me.value = (await dropChatApi.me()).data.data
}

async function loadThreads() {
  const previous = Object.fromEntries(threads.value.map((thread) => [thread.id, thread.peer_last_read_at]))
  const next = (await dropChatApi.threads()).data.data
  threads.value = next.map((thread) => ({ ...thread, peer_last_read_at: previous[thread.id] || null }))
}

async function loadContacts() {
  contacts.value = (await dropChatApi.contacts()).data.data
}

async function loadMessages(threadId) {
  const list = (await dropChatApi.messages(threadId, { limit: PAGE_SIZE })).data.data
  messagesByThread[threadId] = list
  hasMoreByThread[threadId] = list.length === PAGE_SIZE
}

async function loadEarlier() {
  const threadId = activeThreadId.value
  const list = messagesByThread[threadId]
  if (!list?.length) return
  const element = scroller.value
  const previousHeight = element?.scrollHeight || 0
  const older = (await dropChatApi.messages(threadId, { limit: PAGE_SIZE, before: list[0].created_at })).data.data
  messagesByThread[threadId] = [...older, ...list]
  hasMoreByThread[threadId] = older.length === PAGE_SIZE
  await nextTick()
  if (element) element.scrollTop = element.scrollHeight - previousHeight
}

async function selectConversation(entry) {
  try {
    let threadId = entry.thread?.id
    if (!threadId) {
      threadId = (await dropChatApi.openDirect(entry.peer.id)).data.data.id
      await loadThreads()
    }
    activeThreadId.value = threadId
    target.value = ''
    showContacts.value = false
    if (!messagesByThread[threadId]) await loadMessages(threadId)
    await scrollToBottom(true)
    markActiveRead()
  } catch (error) {
    notify(t('pages.xuandrop.loadFailed'), errorMessage(error))
  }
}

function closeConversation() {
  activeThreadId.value = ''
}

function markActiveRead() {
  const thread = activeThread.value
  if (!thread || document.visibilityState !== 'visible') return
  window.clearTimeout(readTimer)
  readTimer = window.setTimeout(async () => {
    if (!thread.unread_count && thread.last_read_at && thread.last_message_at && new Date(thread.last_read_at) >= new Date(thread.last_message_at)) return
    thread.unread_count = 0
    try {
      thread.last_read_at = (await dropChatApi.markRead(thread.id)).data.data.last_read_at
    } catch {
      // next event will retry
    }
  }, 400)
}

// ---------------------------------------------------------------- realtime events

function showSystemNotification(title, body) {
  if (notificationPermission.value !== 'granted' || document.visibilityState === 'visible') return
  try {
    const notification = new Notification(title, { body, tag: 'xuandrop', renotify: true })
    notification.onclick = () => { window.focus(); notification.close() }
  } catch {
    // Some mobile browsers only allow notifications from a service worker.
  }
}

async function handleEvent({ event, data }) {
  if (event === 'socket.open') {
    // Catch up on anything missed while disconnected.
    await Promise.all([loadMe(), loadThreads(), loadContacts()]).catch(() => {})
    if (activeThreadId.value) {
      await loadMessages(activeThreadId.value).catch(() => {})
      scrollToBottom()
    }
    return
  }
  if (event === 'message.created') {
    const thread = threads.value.find((item) => item.id === data.thread_id)
    if (!thread) {
      await loadThreads()
      return
    }
    if (data.sender_device_id && !deviceNames.value[data.sender_device_id] && data.sender_user_id === myUserId.value) {
      // A device that signed in after this page loaded; fetch its name before labelling the message.
      await loadMe().catch(() => {})
    }
    const fromHere = data.sender_device_id && data.sender_device_id === currentDeviceId.value
    const fromOther = thread.kind === 'self' ? !fromHere : data.sender_user_id !== myUserId.value
    const shouldScroll = data.thread_id === activeThreadId.value && (fromHere || isNearBottom())
    upsertMessage(data.thread_id, data)
    thread.last_message = data
    thread.last_message_at = data.created_at
    threads.value = [...threads.value].sort((a, b) => (b.kind === 'self') - (a.kind === 'self') || new Date(b.last_message_at || 0) - new Date(a.last_message_at || 0))
    if (fromOther) {
      const viewing = data.thread_id === activeThreadId.value && document.visibilityState === 'visible'
      if (viewing) {
        markActiveRead()
      } else {
        thread.unread_count = (thread.unread_count || 0) + 1
        const name = senderLabel(data, thread) || t('pages.xuandrop.title')
        notify(t('pages.xuandrop.newMessageFrom', { name }), previewText(data))
        showSystemNotification(t('pages.xuandrop.newMessageFrom', { name }), previewText(data))
      }
    }
    if (shouldScroll) scrollToBottom(true)
    return
  }
  if (event === 'message.deleted') {
    const list = messagesByThread[data.thread_id]
    if (list) messagesByThread[data.thread_id] = list.filter((message) => message.id !== data.id)
    forgetMessage(data.id)
    loadThreads().catch(() => {})
    return
  }
  if (event === 'thread.read') {
    const thread = threads.value.find((item) => item.id === data.thread_id)
    if (thread && data.user_id !== myUserId.value) thread.peer_last_read_at = data.last_read_at
    return
  }
  if (event === 'presence' || event === 'devices.changed') {
    loadMe().catch(() => {})
    return
  }
  if (event === 'contacts.changed') {
    await Promise.all([loadContacts(), loadThreads()]).catch(() => {})
  }
}

// ---------------------------------------------------------------- sending

function newClientId() {
  return window.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(16).slice(2)}`
}

async function sendText(body) {
  const threadId = activeThreadId.value
  if (!threadId) return
  try {
    const response = await dropChatApi.sendText(threadId, { body, target_device_id: target.value || null, client_id: newClientId() })
    upsertMessage(threadId, response.data.data)
    scrollToBottom(true)
  } catch (error) {
    notify(t('pages.xuandrop.uploadFailed'), errorMessage(error))
  }
}

function sendFiles(files) {
  const threadId = activeThreadId.value
  if (!threadId || !activeThread.value?.can_send) return
  const tooLarge = files.find((file) => file.size > DROP_MAX_FILE_BYTES)
  if (tooLarge) {
    notify(t('pages.xuandrop.uploadFailed'), t('pages.xuandrop.tooLarge', { name: tooLarge.name }))
    return
  }
  pendingByThread[threadId] ||= []
  for (const file of files) {
    const item = reactive({
      clientId: newClientId(),
      file,
      targetDeviceId: target.value || null,
      progress: 0,
      status: 'uploading',
      error: '',
      controller: null,
      uploadId: '',
      previewUrl: file.type.startsWith('image/') && file.size < 30 * 1024 * 1024 ? URL.createObjectURL(file) : ''
    })
    pendingByThread[threadId].push(item)
    uploadPending(threadId, item)
  }
  scrollToBottom(true)
}

const DROP_MAX_FILE_BYTES = 2048 * 1024 * 1024
// Bigger files go up in chunks: each request stays far below Cloudflare's 100 MB body limit,
// and a dropped connection only repeats one chunk.
const CHUNKED_FROM_BYTES = 8 * 1024 * 1024
const sleep = (ms) => new Promise((resolve) => window.setTimeout(resolve, ms))

async function uploadInChunks(threadId, item) {
  if (!item.uploadId) {
    const started = await dropChatApi.startUpload(threadId, {
      filename: item.file.name,
      mime_type: item.file.type || null,
      file_size: item.file.size,
      target_device_id: item.targetDeviceId,
      client_id: item.clientId
    })
    item.uploadId = started.data.data.id
  }
  let state = (await dropChatApi.uploadStatus(item.uploadId)).data.data
  const { chunk_size: chunkSize } = state
  let index = state.next_index
  while (index * chunkSize < item.file.size) {
    const start = index * chunkSize
    const blob = item.file.slice(start, Math.min(start + chunkSize, item.file.size))
    for (let attempt = 0; ; attempt += 1) {
      try {
        state = (await dropChatApi.uploadChunk(item.uploadId, index, blob, {
          signal: item.controller.signal,
          onProgress(loaded) { item.progress = (start + loaded) / item.file.size }
        })).data.data
        break
      } catch (error) {
        if (error.code === 'ERR_CANCELED' || attempt >= 4) throw error
        if (error.response?.status === 409) {
          state = (await dropChatApi.uploadStatus(item.uploadId)).data.data
          break
        }
        item.error = t('pages.xuandrop.resuming')
        await sleep(1000 * 2 ** attempt)
        item.error = ''
      }
    }
    index = state.next_index
    item.progress = state.received_bytes / item.file.size
  }
  return dropChatApi.completeUpload(item.uploadId)
}

async function uploadPending(threadId, item) {
  item.status = 'uploading'
  item.error = ''
  if (!item.uploadId) item.progress = 0
  item.controller = new AbortController()
  try {
    const response = item.file.size >= CHUNKED_FROM_BYTES ? await uploadInChunks(threadId, item) : await dropChatApi.sendFile(threadId, item.file, {
      targetDeviceId: item.targetDeviceId,
      clientId: item.clientId,
      signal: item.controller.signal,
      onProgress(value) { item.progress = value }
    })
    upsertMessage(threadId, response.data.data)
  } catch (error) {
    if (error.code === 'ERR_CANCELED') {
      if (item.uploadId) dropChatApi.cancelUpload(item.uploadId).catch(() => {})
      removePending(threadId, item)
      return
    }
    item.status = 'failed'
    item.error = errorMessage(error)
  }
}

function removePending(threadId, item) {
  const list = pendingByThread[threadId] || []
  const index = list.indexOf(item)
  if (index >= 0) list.splice(index, 1)
  if (item.previewUrl) URL.revokeObjectURL(item.previewUrl)
}

function cancelPending(item) {
  if (item.status === 'uploading') item.controller?.abort()
  else {
    if (item.uploadId) dropChatApi.cancelUpload(item.uploadId).catch(() => {})
    removePending(activeThreadId.value, item)
  }
}

function onDragOver(event) {
  if (!activeThread.value?.can_send || !event.dataTransfer?.types?.includes('Files')) return
  event.preventDefault()
  dragging.value = true
}

function onDragLeave(event) {
  if (!event.currentTarget.contains(event.relatedTarget)) dragging.value = false
}

function onDrop(event) {
  dragging.value = false
  const files = Array.from(event.dataTransfer?.files || [])
  if (files.length) {
    event.preventDefault()
    sendFiles(files)
  }
}

// ---------------------------------------------------------------- message actions

async function saveToLibrary(message, destination) {
  const payload = { destination }
  if (destination === 'receipts') {
    const merchant = await dialog.prompt({ title: t('pages.xuandrop.destinations.receipts'), label: t('pages.receipts.merchant') })
    if (merchant === null) return
    payload.merchant = merchant || null
  }
  const next = new Set(savingIds.value)
  next.add(message.id)
  savingIds.value = next
  try {
    const saved = (await dropChatApi.save(message.id, payload)).data.data
    upsertMessage(message.thread_id, { ...message, saved_to: saved.saved_to })
  } catch (error) {
    notify(t('pages.xuandrop.uploadFailed'), errorMessage(error))
  } finally {
    const after = new Set(savingIds.value)
    after.delete(message.id)
    savingIds.value = after
  }
}

async function deleteMessage(message) {
  const confirmed = await dialog.confirm({ title: t('pages.xuandrop.deleteForAll'), message: t('pages.xuandrop.deleteConfirm'), danger: true })
  if (!confirmed) return
  try {
    await dropChatApi.remove(message.id)
    const list = messagesByThread[message.thread_id]
    if (list) messagesByThread[message.thread_id] = list.filter((item) => item.id !== message.id)
    forgetMessage(message.id)
  } catch (error) {
    notify(t('pages.xuandrop.loadFailed'), errorMessage(error))
  }
}

async function openPreview(message) {
  closePreview()
  preview.message = message
  preview.loading = true
  try {
    const file = await fetchMessageFile(message)
    if (preview.message?.id !== message.id) return
    preview.file = file
    preview.url = URL.createObjectURL(file)
  } catch (error) {
    notify(t('pages.xuandrop.loadFailed'), errorMessage(error))
    closePreview()
  } finally {
    preview.loading = false
  }
}

function closePreview() {
  if (preview.url) URL.revokeObjectURL(preview.url)
  preview.message = null
  preview.url = ''
  preview.file = null
}

const GENERIC_DEVICE_NAMES = ['Local Browser', 'Browser', 'Unknown Device']

// Devices signed in by older versions are all called "Local Browser"; give this one a readable name.
async function upgradeCurrentDeviceName() {
  const current = devices.value.find((device) => device.is_current)
  if (!current || !GENERIC_DEVICE_NAMES.includes(current.device_name)) return
  try {
    await dropChatApi.renameDevice(current.id, defaultDeviceName())
    await loadMe()
  } catch {
    // keep the old name
  }
}

function isPhone(device) {
  return /iPhone|Android|iPad/.test(`${device.device_type} ${device.device_name}`)
}

function lastSeenText(device) {
  if (device.online || device.is_current) return t('pages.xuandrop.online')
  if (!device.last_seen_at) return t('pages.xuandrop.offline')
  const minutes = Math.round((Date.now() - new Date(device.last_seen_at)) / 60000)
  if (minutes < 60) return t('pages.xuandrop.seenMinutesAgo', { n: Math.max(1, minutes) })
  if (minutes < 60 * 24) return t('pages.xuandrop.seenHoursAgo', { n: Math.round(minutes / 60) })
  return t('pages.xuandrop.seenDaysAgo', { n: Math.round(minutes / 1440) })
}

async function renameDevice(device) {
  const name = await dialog.prompt({ title: t('pages.xuandrop.renameDevice'), label: t('pages.xuandrop.deviceName'), defaultValue: device.device_name })
  if (!name?.trim()) return
  await dropChatApi.renameDevice(device.id, name.trim())
  await loadMe()
}

async function removeDevice(device) {
  const confirmed = await dialog.confirm({
    title: t('pages.xuandrop.removeDevice'),
    message: t('pages.xuandrop.removeDeviceConfirm', { name: device.device_name }),
    danger: true
  })
  if (!confirmed) return
  try {
    await dropChatApi.removeDevice(device.id)
    await loadMe()
  } catch (error) {
    notify(t('pages.xuandrop.loadFailed'), errorMessage(error))
  }
}

async function removeActiveContact() {
  const peerId = activeThread.value?.peer?.id
  const contact = contacts.value.find((item) => item.peer?.id === peerId)
  if (!contact) return
  const confirmed = await dialog.confirm({ title: t('pages.xuandrop.removeContact'), message: t('pages.xuandrop.removeContactConfirm'), danger: true })
  if (!confirmed) return
  await dropChatApi.removeContact(contact.id)
  await Promise.all([loadContacts(), loadThreads()])
}

async function enableNotifications() {
  if (typeof Notification === 'undefined') {
    notify(t('pages.xuandrop.notificationsUnsupported'))
    return
  }
  notificationPermission.value = await Notification.requestPermission()
}

// ---------------------------------------------------------------- lifecycle

function onVisibility() {
  if (document.visibilityState === 'visible') markActiveRead()
}

const mobileQuery = window.matchMedia('(max-width: 840px)')
function onMobileChange(event) {
  isMobile.value = event.matches
}

watch([activeThreadId, isMobile], ([threadId, mobile]) => {
  document.body.classList.toggle('xd-chat-open', Boolean(threadId && mobile))
}, { immediate: true })

onMounted(async () => {
  document.addEventListener('visibilitychange', onVisibility)
  mobileQuery.addEventListener('change', onMobileChange)
  try {
    await Promise.all([loadMe(), loadThreads(), loadContacts()])
    await upgradeCurrentDeviceName()
    const self = threads.value.find((thread) => thread.kind === 'self')
    if (self && !isMobile.value) await selectConversation({ thread: self })
  } catch (error) {
    pageError.value = errorMessage(error)
  }
  socket.start()
})

onBeforeUnmount(() => {
  document.removeEventListener('visibilitychange', onVisibility)
  mobileQuery.removeEventListener('change', onMobileChange)
  document.body.classList.remove('xd-chat-open')
  document.title = originalTitle
  window.clearTimeout(toastTimer)
  window.clearTimeout(readTimer)
  closePreview()
})
</script>

<template>
  <div class="xd-page" :class="{ 'has-active': activeThreadId }">
    <aside class="xd-sidebar">
      <header class="xd-sidebar-head">
        <div>
          <strong>XuanDrop</strong>
          <span class="xd-status" :class="`is-${socket.status.value}`"><i />{{ connectionLabel }}</span>
        </div>
        <div class="xd-head-actions">
          <button type="button" class="xd-icon-only" :title="t('pages.xuandrop.qrUpload')" @click="showQr = true"><QrCode :size="18" /></button>
          <button
            v-if="notificationPermission !== 'granted'"
            type="button"
            class="xd-icon-only"
            :title="t('pages.xuandrop.notifications')"
            @click="enableNotifications"
          ><Bell :size="18" /></button>
          <span v-else class="xd-icon-only is-static" :title="t('pages.xuandrop.notificationsOn')"><BellRing :size="18" /></span>
          <button type="button" class="xd-icon-only" :class="{ 'has-badge': pendingIncoming }" :title="t('pages.xuandrop.contacts')" @click="showContacts = !showContacts">
            <Users :size="18" />
          </button>
        </div>
      </header>

      <p v-if="pageError" class="xd-error">{{ pageError }}</p>

      <DropContactsPanel v-if="showContacts || pendingIncoming" :contacts="contacts" @changed="handleEvent({ event: 'contacts.changed' })" />

      <nav class="xd-conversations" :aria-label="t('pages.xuandrop.conversations')">
        <button
          v-for="entry in conversationList"
          :key="entry.key"
          type="button"
          class="xd-conversation"
          :class="{ 'is-active': entry.thread && entry.thread.id === activeThreadId }"
          @click="selectConversation(entry)"
        >
          <span class="xd-avatar" :class="{ 'is-self': entry.self }">
            <Laptop v-if="entry.self" :size="20" />
            <template v-else>{{ (entry.title || '?').slice(0, 1).toUpperCase() }}</template>
          </span>
          <span class="xd-conversation-main">
            <strong>{{ entry.title }}</strong>
            <small>{{ entry.thread?.last_message ? previewText(entry.thread.last_message) : (entry.self ? t('pages.xuandrop.myDevicesHint') : `@${entry.peer?.username}`) }}</small>
          </span>
          <span v-if="entry.thread?.unread_count" class="xd-unread">{{ entry.thread.unread_count }}</span>
        </button>
        <p v-if="!acceptedContacts.length && !showContacts" class="xd-hint xd-pad">{{ t('pages.xuandrop.noContacts') }}</p>
      </nav>

      <section class="xd-devices">
        <header>
          <strong>{{ t('pages.xuandrop.devices') }}</strong>
        </header>
        <div v-for="device in devices" :key="device.id" class="xd-device" :class="{ 'is-current': device.is_current }">
          <span class="xd-device-icon">
            <Smartphone v-if="isPhone(device)" :size="18" />
            <Laptop v-else :size="18" />
            <i :class="{ 'is-online': device.online || device.is_current }" />
          </span>
          <span class="xd-device-main">
            <strong>{{ device.device_name }}</strong>
            <small>{{ device.is_current ? t('pages.xuandrop.thisDevice') : lastSeenText(device) }}</small>
          </span>
          <button type="button" class="xd-icon-only" :title="t('pages.xuandrop.renameDevice')" @click="renameDevice(device)"><Pencil :size="14" /></button>
          <button v-if="!device.is_current" type="button" class="xd-icon-only is-danger" :title="t('pages.xuandrop.removeDevice')" @click="removeDevice(device)"><Trash2 :size="14" /></button>
        </div>
      </section>
    </aside>

    <section
      class="xd-chat"
      :class="{ 'is-dragging': dragging }"
      @dragover="onDragOver"
      @dragleave="onDragLeave"
      @drop="onDrop"
    >
      <template v-if="activeThread">
        <header class="xd-chat-head">
          <button type="button" class="xd-icon-only xd-back" :aria-label="t('pages.xuandrop.back')" @click="closeConversation"><ChevronLeft :size="22" /></button>
          <div class="xd-chat-title">
            <strong>{{ activeThread.kind === 'self' ? t('pages.xuandrop.myDevices') : activeThread.peer?.display_name }}</strong>
            <small v-if="activeThread.kind === 'self'">
              {{ devices.filter((device) => device.online || device.is_current).length }} / {{ devices.length }} {{ t('pages.xuandrop.online') }}
            </small>
            <small v-else>@{{ activeThread.peer?.username }}</small>
          </div>
          <button v-if="activeThread.kind === 'direct' && activeThread.can_send" type="button" class="xd-icon-only" :title="t('pages.xuandrop.removeContact')" @click="removeActiveContact">
            <UserMinus :size="18" />
          </button>
        </header>

        <div ref="scroller" class="xd-messages">
          <button v-if="hasMoreByThread[activeThreadId]" type="button" class="xb-text-button xd-load-earlier" @click="loadEarlier">{{ t('pages.xuandrop.loadEarlier') }}</button>
          <p v-if="!activeMessages.length && !activePending.length" class="xd-empty">
            {{ activeThread.kind === 'self' ? t('pages.xuandrop.empty') : t('pages.xuandrop.emptyDirect', { name: activeThread.peer?.display_name, days: RETENTION_DAYS }) }}
          </p>
          <template v-for="row in timeline" :key="row.key">
            <div v-if="row.type === 'day'" class="xd-day"><span>{{ row.label }}</span></div>
            <DropMessageBubble
              v-else
              :message="row.message"
              :mine="isMine(row.message)"
              :sender-label="senderLabel(row.message)"
              :target-label="targetLabel(row.message)"
              :read="isRead(row.message)"
              :can-delete="row.message.sender_user_id === myUserId"
              :saving="savingIds.has(row.message.id)"
              @preview="openPreview"
              @save="(destination) => saveToLibrary(row.message, destination)"
              @delete="deleteMessage"
            />
          </template>
          <div v-for="item in activePending" :key="item.clientId" class="xd-msg is-mine is-pending">
            <div class="xd-bubble" :class="{ 'is-media': item.previewUrl }">
              <img v-if="item.previewUrl" :src="item.previewUrl" class="xd-pending-image" alt="" />
              <div class="xd-file" :class="{ 'is-compact': item.previewUrl }">
                <div class="xd-file-main">
                  <strong>{{ item.file.name }}</strong>
                  <span>{{ formatSize(item.file.size) }} · {{ item.status === 'failed' ? t('pages.xuandrop.uploadFailed') : `${t('pages.xuandrop.uploading')} ${Math.round(item.progress * 100)}%` }}</span>
                </div>
              </div>
              <div v-if="item.status === 'uploading'" class="xd-progress"><span :style="{ width: `${Math.round(item.progress * 100)}%` }" /></div>
              <p v-if="item.error" class="xd-error">{{ item.error }}</p>
            </div>
            <div class="xd-msg-actions">
              <button v-if="item.status === 'failed'" type="button" class="xd-action" @click="uploadPending(activeThreadId, item)">{{ t('pages.xuandrop.retry') }}</button>
              <button type="button" class="xd-action" @click="cancelPending(item)">{{ t('pages.xuandrop.cancelUpload') }}</button>
            </div>
          </div>
        </div>

        <p v-if="!activeThread.can_send" class="xd-hint xd-pad">{{ t('pages.xuandrop.notContactsAnymore') }}</p>
        <DropComposer
          v-else
          v-model:target="target"
          :targets="activeThread.kind === 'self' ? otherDevices : []"
          @send-text="sendText"
          @send-files="sendFiles"
        />
        <p class="xd-retention">{{ t('pages.xuandrop.retention', { days: RETENTION_DAYS }) }}</p>
        <div v-if="dragging" class="xd-drop-hint">{{ t('pages.xuandrop.dropHere') }}</div>
      </template>
      <div v-else class="xd-empty xd-empty-center">{{ t('pages.xuandrop.selectConversation') }}</div>
    </section>

    <Teleport to="body">
      <DropQrDialog v-if="showQr" @close="showQr = false" />

      <div v-if="preview.message" class="xd-overlay xd-lightbox" @click.self="closePreview">
        <button type="button" class="xd-icon-only xd-lightbox-close" :aria-label="t('common.actions.close')" @click="closePreview"><X :size="22" /></button>
        <img v-if="preview.url" :src="preview.url" :alt="preview.message.filename" />
        <span v-else class="xd-hint">{{ t('common.actions.loading') }}</span>
        <button v-if="preview.file" type="button" class="xb-primary-button xd-lightbox-save" @click="deliverFile(preview.file)">
          {{ t('pages.xuandrop.saveToDevice') }}
        </button>
      </div>

      <div v-if="toast" class="xd-toast" role="status" @click="toast = null">
        <strong>{{ toast.message }}</strong>
        <span v-if="toast.detail">{{ toast.detail }}</span>
      </div>
    </Teleport>
  </div>
</template>
