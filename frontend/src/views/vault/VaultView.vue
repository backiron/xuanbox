<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Download, FileText, KeyRound, Lock, LockKeyhole, Pencil, StickyNote, Trash2, Undo2, Upload, X } from 'lucide-vue-next'

import PageHeader from '../../components/common/PageHeader.vue'
import { vaultApi } from '../../api/vaultApi'
import { useDialogStore } from '../../stores/dialogStore'
import { useVaultStore } from '../../stores/vaultStore'

const { t, locale } = useI18n()
const vault = useVaultStore()
const dialog = useDialogStore()

const items = ref([])
const loading = ref(false)
const message = ref('')
const error = ref('')
const uploadProgress = ref(0)
const dragging = ref(false)
const thumbs = ref({})
const viewer = ref(null) // { item, url, kind } — for a note: { item, kind: 'note', blocks: [{ text } | { imageId, url }] }
let clock = null

const minutesLeft = computed(() => Math.max(1, Math.ceil(vault.secondsLeft / 60)))

function formatBytes(value) {
  if (!value) return ''
  if (value < 1024 * 1024) return `${Math.max(1, Math.ceil(value / 1024))} KB`
  return `${(value / 1024 / 1024).toFixed(1)} MB`
}

function formatDate(value) {
  return value ? new Intl.DateTimeFormat(locale.value, { dateStyle: 'medium' }).format(new Date(value)) : ''
}

function failure(err, fallbackKey) {
  if (err?.response?.status === 401) vault.clear()
  error.value = err?.response?.data?.message && err.response.status !== 401 ? err.response.data.message : t(fallbackKey)
}

function forgetViewer() {
  if (viewer.value?.url) URL.revokeObjectURL(viewer.value.url)
  viewer.value?.blocks?.forEach((block) => block.url && URL.revokeObjectURL(block.url))
  viewer.value = null
}

function forgetBlobs() {
  Object.values(thumbs.value).forEach((url) => url && URL.revokeObjectURL(url))
  thumbs.value = {}
  forgetViewer()
}

const isNote = (item) => item.kind === 'note'

async function loadItems() {
  if (!vault.unlocked) return
  loading.value = true
  try {
    const response = await vaultApi.list(vault.token)
    items.value = response.data.data
    items.value.filter((item) => (item.is_image || (isNote(item) && item.cover_image_id)) && !(item.id in thumbs.value)).forEach(loadThumb)
  } catch (err) {
    failure(err, 'pages.vault.loadFailed')
  } finally {
    loading.value = false
  }
}

async function loadThumb(item) {
  thumbs.value = { ...thumbs.value, [item.id]: '' }
  try {
    const response = isNote(item)
      ? await vaultApi.noteImage(vault.token, item.id, item.cover_image_id)
      : await vaultApi.thumbnail(vault.token, item.id)
    thumbs.value = { ...thumbs.value, [item.id]: URL.createObjectURL(response.data) }
  } catch {
    // shown with a file icon instead
  }
}

async function unlock() {
  error.value = ''
  const token = await vault.ensureUnlocked()
  if (token) await loadItems()
}

async function lockNow() {
  forgetBlobs()
  items.value = []
  await vault.lock()
}

async function changePin() {
  const token = await vault.openDialog('change')
  if (token) message.value = t('pages.vault.pinChanged')
}

async function uploadFiles(fileList) {
  const files = [...(fileList || [])]
  if (!files.length) return
  message.value = ''
  error.value = ''
  let done = 0
  for (const file of files) {
    try {
      const result = await vault.run((token) => vaultApi.upload(token, file, (event) => {
        if (event.total) uploadProgress.value = Math.round(((done + event.loaded / event.total) / files.length) * 100)
      }))
      if (!result) break
      done += 1
    } catch (err) {
      failure(err, 'pages.vault.uploadFailed')
      break
    }
  }
  uploadProgress.value = 0
  if (done) message.value = t('pages.vault.uploaded', { count: done })
  await loadItems()
}

function onPick(event) {
  uploadFiles(event.target.files)
  event.target.value = ''
}

function onDrop(event) {
  dragging.value = false
  uploadFiles(event.dataTransfer?.files)
}

function kindOf(item) {
  const mime = item.mime_type || ''
  if (mime.startsWith('image/') && mime !== 'image/svg+xml') return 'image'
  if (mime === 'application/pdf') return 'pdf'
  if (mime.startsWith('video/')) return 'video'
  if (mime.startsWith('audio/')) return 'audio'
  if (mime.startsWith('text/plain')) return 'text'
  return 'other'
}

const NOTE_IMAGE = /^\[\[img:([0-9a-fA-F-]{36})\]\]$/

async function openNote(item) {
  viewer.value = { item, kind: 'note', loading: true, blocks: [] }
  try {
    const response = await vault.run((token) => vaultApi.note(token, item.id))
    if (!response || viewer.value?.item.id !== item.id) return
    const blocks = []
    for (const line of response.data.data.body.split('\n')) {
      const match = line.match(NOTE_IMAGE)
      if (match) blocks.push({ imageId: match[1], url: '' })
      else if (blocks.length && 'text' in blocks.at(-1)) blocks.at(-1).text += `\n${line}`
      else blocks.push({ text: line })
    }
    viewer.value = { item, kind: 'note', loading: false, blocks }
    // Through viewer.value so each image shows as soon as it arrives.
    for (const block of viewer.value.blocks.filter((entry) => entry.imageId)) {
      const image = await vault.run((token) => vaultApi.noteImage(token, item.id, block.imageId))
      if (!image || viewer.value?.item.id !== item.id) return
      block.url = URL.createObjectURL(image.data)
    }
  } catch (err) {
    forgetViewer()
    failure(err, 'pages.vault.openFailed')
  }
}

async function openItem(item) {
  if (isNote(item)) return openNote(item)
  const kind = kindOf(item)
  viewer.value = { item, url: '', kind, loading: kind !== 'other' }
  if (kind === 'other') return
  try {
    const response = await vault.run((token) => vaultApi.content(token, item.id))
    if (!response || viewer.value?.item.id !== item.id) return
    viewer.value = { item, url: URL.createObjectURL(response.data), kind, loading: false }
  } catch (err) {
    viewer.value = null
    failure(err, 'pages.vault.openFailed')
  }
}

function closeViewer() {
  forgetViewer()
}

async function download(item) {
  try {
    const response = await vault.run((token) => vaultApi.content(token, item.id, true))
    if (!response) return
    const url = URL.createObjectURL(response.data)
    const link = document.createElement('a')
    link.href = url
    link.download = item.filename || item.title
    document.body.appendChild(link)
    link.click()
    link.remove()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  } catch (err) {
    failure(err, 'pages.vault.openFailed')
  }
}

async function rename(item) {
  const title = await dialog.prompt({ title: t('pages.vault.renameTitle'), label: t('pages.vault.nameLabel'), defaultValue: item.title })
  if (!title || title === item.title) return
  try {
    const response = await vault.run((token) => vaultApi.update(token, item.id, { title }))
    if (!response) return
    Object.assign(item, response.data.data)
    if (viewer.value?.item.id === item.id) viewer.value.item = item
  } catch (err) {
    failure(err, 'pages.vault.actionFailed')
  }
}

function restoreHint(item) {
  if (isNote(item)) return t('pages.vault.restoreToNotes')
  return item.from_photos ? t('pages.vault.restoreToPhotos') : t('pages.vault.restoreToFiles')
}

// Says exactly where the item went back to.
function restoredMessage(result) {
  if (result.destination === 'notes') return t('pages.vault.restoredNotes')
  if (result.destination === 'photos') {
    return result.albums?.length ? t('pages.vault.restoredAlbums', { albums: result.albums.join(locale.value.startsWith('zh') ? '、' : ', ') }) : t('pages.vault.restoredPhotos')
  }
  return result.folder_name ? t('pages.vault.restoredFolder', { folder: result.folder_name }) : t('pages.vault.restoredFiles')
}

async function restore(item) {
  const ok = await dialog.confirm({
    title: t('pages.vault.restoreTitle'),
    message: restoreHint(item),
    confirmText: t('pages.vault.restore')
  })
  if (!ok) return
  try {
    const response = await vault.run((token) => (isNote(item) ? vaultApi.restoreNote(token, item.id) : vaultApi.restore(token, item.id)))
    if (!response) return
    closeViewer()
    message.value = restoredMessage(response.data.data)
    await loadItems()
  } catch (err) {
    failure(err, 'pages.vault.actionFailed')
  }
}

async function remove(item) {
  const ok = await dialog.confirm({
    title: t('pages.vault.deleteTitle'),
    message: t('pages.vault.deleteMessage', { name: item.title || t('pages.notes.untitled') }),
    confirmText: t('common.actions.delete'),
    danger: true
  })
  if (!ok) return
  try {
    const response = await vault.run((token) => (isNote(item) ? vaultApi.removeNote(token, item.id) : vaultApi.remove(token, item.id)))
    if (!response) return
    closeViewer()
    message.value = t('pages.vault.deleted')
    await loadItems()
  } catch (err) {
    failure(err, 'pages.vault.actionFailed')
  }
}

watch(() => vault.unlocked, (unlocked) => {
  if (!unlocked) {
    // Locked (timeout, lock button, another tab): drop everything decrypted from memory.
    forgetBlobs()
    items.value = []
  }
})

onMounted(async () => {
  clock = setInterval(() => vault.tick(), 15000)
  try {
    await vault.refreshStatus()
  } catch {
    // shown as locked
  }
  if (vault.unlocked) await loadItems()
})

onBeforeUnmount(() => {
  clearInterval(clock)
  forgetBlobs()
})
</script>

<template>
  <section
    class="xb-vault-page"
    :class="{ 'is-dragging': dragging && vault.unlocked }"
    @dragover.prevent="dragging = vault.unlocked"
    @dragleave.self="dragging = false"
    @drop.prevent="onDrop"
  >
    <PageHeader
      :title="t('pages.vault.title')"
      :subtitle="vault.unlocked ? t('pages.vault.autoLock', { minutes: minutesLeft }) : t('pages.vault.subtitle')"
    >
      <template v-if="vault.unlocked">
        <button class="xb-secondary-button" type="button" @click="changePin">
          <KeyRound :size="16" />
          {{ t('pages.vault.changePin') }}
        </button>
        <button class="xb-secondary-button" type="button" @click="lockNow">
          <Lock :size="16" />
          {{ t('pages.vault.lockNow') }}
        </button>
        <label class="xb-upload-button">
          <Upload :size="16" />
          {{ t('pages.vault.upload') }}
          <input type="file" multiple hidden @change="onPick" />
        </label>
      </template>
    </PageHeader>

    <div v-if="uploadProgress" class="xb-progress"><span :style="{ width: `${uploadProgress}%` }"></span></div>
    <p v-if="message" class="xb-status-note is-success">{{ message }}</p>
    <p v-if="error" class="xb-status-note is-error">{{ error }}</p>

    <div v-if="!vault.unlocked" class="xb-panel xb-vault-locked">
      <LockKeyhole :size="40" />
      <h3>{{ vault.pinSet === false ? t('pages.vault.setupTitle') : t('pages.vault.lockedTitle') }}</h3>
      <p>{{ vault.pinSet === false ? t('pages.vault.setupHint') : t('pages.vault.lockedHint') }}</p>
      <button class="xb-primary-button" type="button" @click="unlock">
        {{ vault.pinSet === false ? t('pages.vault.setupButton') : t('pages.vault.unlockButton') }}
      </button>
      <ul class="xb-vault-facts">
        <li>{{ t('pages.vault.factHidden') }}</li>
        <li>{{ t('pages.vault.factNoShare') }}</li>
        <li>{{ t('pages.vault.factAutoLock') }}</li>
      </ul>
    </div>

    <template v-else>
      <label v-if="!loading && !items.length" class="xb-panel xb-vault-empty">
        <Upload :size="28" />
        <strong>{{ t('pages.vault.emptyTitle') }}</strong>
        <span>{{ t('pages.vault.emptyHint') }}</span>
        <input type="file" multiple hidden @change="onPick" />
      </label>
      <div v-else class="xb-vault-grid">
        <button v-for="item in items" :key="item.id" type="button" class="xb-vault-card" @click="openItem(item)">
          <div class="xb-vault-thumb">
            <img v-if="thumbs[item.id]" :src="thumbs[item.id]" alt="" />
            <StickyNote v-else-if="isNote(item)" :size="34" />
            <FileText v-else :size="34" />
          </div>
          <strong>{{ item.title || (isNote(item) ? t('pages.notes.untitled') : '') }}</strong>
          <small v-if="isNote(item)">{{ [t('pages.vault.noteKind'), formatDate(item.added_at)].join(' · ') }}</small>
          <small v-else>{{ [formatBytes(item.file_size), formatDate(item.created_at)].filter(Boolean).join(' · ') }}</small>
        </button>
      </div>
    </template>

    <section v-if="viewer" class="xb-modal-backdrop xb-vault-viewer" @click.self="closeViewer">
      <div class="xb-modal">
        <header>
          <strong>{{ viewer.item.title || t('pages.notes.untitled') }}</strong>
          <button class="xb-icon-button" type="button" :title="t('common.actions.close')" @click="closeViewer"><X :size="18" /></button>
        </header>
        <div class="xb-vault-viewer-body">
          <p v-if="viewer.loading" class="xb-vault-hint">{{ t('common.actions.loading') }}…</p>
          <div v-else-if="viewer.kind === 'note'" class="xb-vault-note">
            <template v-for="(block, index) in viewer.blocks" :key="index">
              <img v-if="block.imageId && block.url" :src="block.url" alt="" />
              <p v-else-if="block.imageId" class="xb-vault-hint">…</p>
              <div v-else-if="block.text.trim()" class="xb-vault-note-text">{{ block.text }}</div>
            </template>
          </div>
          <img v-else-if="viewer.kind === 'image'" :src="viewer.url" alt="" />
          <iframe v-else-if="viewer.kind === 'pdf' || viewer.kind === 'text'" :src="viewer.url" :title="viewer.item.title"></iframe>
          <video v-else-if="viewer.kind === 'video'" :src="viewer.url" controls></video>
          <audio v-else-if="viewer.kind === 'audio'" :src="viewer.url" controls></audio>
          <p v-else class="xb-vault-hint">{{ t('pages.vault.noPreview') }}</p>
        </div>
        <footer>
          <template v-if="viewer.kind !== 'note'">
            <button class="xb-secondary-button" type="button" @click="download(viewer.item)"><Download :size="16" />{{ t('common.actions.download') }}</button>
            <button class="xb-secondary-button" type="button" @click="rename(viewer.item)"><Pencil :size="16" />{{ t('pages.vault.rename') }}</button>
          </template>
          <button class="xb-secondary-button" type="button" @click="restore(viewer.item)"><Undo2 :size="16" />{{ t('pages.vault.restore') }}</button>
          <button class="xb-secondary-button xb-danger-button" type="button" @click="remove(viewer.item)"><Trash2 :size="16" />{{ t('common.actions.delete') }}</button>
        </footer>
      </div>
    </section>
  </section>
</template>
