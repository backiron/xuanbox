<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { onBeforeRouteLeave, useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ArrowLeft, Check, ImagePlus, Pencil, Pin, PinOff, Plus, Search, StickyNote, Trash2, X } from 'lucide-vue-next'

import { noteApi } from '../../api/noteApi'
import { useDialogStore } from '../../stores/dialogStore'
import '../../styles/notes.css'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const dialog = useDialogStore()

const IMAGE_LINE = /^\[\[img:([0-9a-fA-F-]{36})\]\]$/
let keySeq = 0

const notes = ref([])
const query = ref('')
const loadingList = ref(false)
const listError = ref('')
const current = ref(null) // { id, updated_at, pinned, created_at }
const blocks = ref([])
const editing = ref(false)
const saveState = ref('saved') // saved | dirty | saving | error | conflict
const actionError = ref('')
const viewer = ref('')
const editorRef = ref(null)
const imageUrls = ref({})

let saveTimer = null
let searchTimer = null
let editVersion = 0
let saving = null
let lastFocus = null // { key, pos }

const hasOpenNote = computed(() => Boolean(current.value))
const uploading = computed(() => blocks.value.some((block) => block.type === 'image' && block.uploading))

function textBlock(text = '') {
  return { key: ++keySeq, type: 'text', text }
}

function imageBlock(id, extra = {}) {
  return { key: ++keySeq, type: 'image', id, ...extra }
}

function parseBody(body) {
  const result = []
  let buffer = []
  const flush = () => {
    result.push(textBlock(buffer.join('\n')))
    buffer = []
  }
  for (const line of (body || '').split('\n')) {
    const match = line.match(IMAGE_LINE)
    if (match) {
      flush()
      result.push(imageBlock(match[1]))
    } else {
      buffer.push(line)
    }
  }
  flush()
  return result
}

function serialize(list = blocks.value) {
  return list
    .filter((block) => (block.type === 'image' ? block.id : block.text !== ''))
    .map((block) => (block.type === 'image' ? `[[img:${block.id}]]` : block.text))
    .join('\n')
}

function summarize(body) {
  const lines = body.split('\n').filter((line) => !IMAGE_LINE.test(line)).map((line) => line.trim()).filter(Boolean)
  const images = body.split('\n').map((line) => line.match(IMAGE_LINE)).filter(Boolean).map((match) => match[1])
  return { title: (lines[0] || '').slice(0, 120), snippet: lines.slice(1).join(' ').slice(0, 240), image_count: images.length, cover_image_id: images[0] || null }
}

function formatDate(value) {
  if (!value) return ''
  const date = new Date(value)
  const sameDay = date.toDateString() === new Date().toDateString()
  return new Intl.DateTimeFormat(undefined, sameDay ? { timeStyle: 'short' } : { dateStyle: 'medium' }).format(date)
}

function errorText(err, fallback) {
  return err?.response?.data?.message || fallback
}

// ---------------------------------------------------------------- images

function ensureImage(noteId, imageId) {
  const cacheKey = `${noteId}/${imageId}`
  if (cacheKey in imageUrls.value) return
  imageUrls.value = { ...imageUrls.value, [cacheKey]: '' }
  noteApi.image(noteId, imageId)
    .then((response) => {
      imageUrls.value = { ...imageUrls.value, [cacheKey]: URL.createObjectURL(response.data) }
    })
    .catch(() => {
      imageUrls.value = { ...imageUrls.value, [cacheKey]: 'error' }
    })
}

function imageUrl(noteId, imageId) {
  return imageUrls.value[`${noteId}/${imageId}`] || ''
}

function blockImageSrc(block) {
  if (block.localUrl) return block.localUrl
  return current.value && block.id ? imageUrl(current.value.id, block.id) : ''
}

// Images are fetched with the session token, so they are loaded here rather than by <img src>.
watch(notes, (list) => list.forEach((note) => note.cover_image_id && ensureImage(note.id, note.cover_image_id)))
watch(blocks, (list) => {
  if (!current.value) return
  list.forEach((block) => block.type === 'image' && block.id && !block.localUrl && ensureImage(current.value.id, block.id))
}, { deep: true })

async function insertImages(files, at = lastFocus) {
  const images = [...files].filter((file) => file.type.startsWith('image/'))
  if (!images.length || !current.value) return
  if (!editing.value) editing.value = true
  let index = blocks.value.findIndex((block) => block.key === at?.key)
  if (index < 0) index = blocks.value.length - 1
  const target = blocks.value[index]
  const pos = Math.min(at?.pos ?? target.text.length, target.text.length)
  const before = target.text.slice(0, pos).replace(/\n$/, '')
  const after = target.text.slice(pos).replace(/^\n/, '')
  const inserted = [textBlock(before)]
  const pending = []
  images.forEach((file, i) => {
    const block = imageBlock(null, { uploading: true, localUrl: URL.createObjectURL(file) })
    inserted.push(block)
    pending.push([block, file])
    inserted.push(textBlock(i === images.length - 1 ? after : ''))
  })
  blocks.value.splice(index, 1, ...inserted)
  const noteId = current.value.id
  for (const [block, file] of pending) {
    try {
      const response = await noteApi.addImage(noteId, file)
      const live = blocks.value.find((item) => item.key === block.key)
      if (live) {
        live.id = response.data.data.id
        live.uploading = false
      }
      markDirty()
    } catch (err) {
      actionError.value = errorText(err, t('pages.notes.imageFailed'))
      removeImage(block.key, { save: false })
    }
  }
  await nextTick()
  autosizeAll()
}

function removeImage(key, { save = true } = {}) {
  const index = blocks.value.findIndex((block) => block.key === key)
  if (index < 0) return
  const removed = blocks.value[index]
  if (removed.localUrl) URL.revokeObjectURL(removed.localUrl)
  const prev = blocks.value[index - 1]
  const next = blocks.value[index + 1]
  if (prev?.type === 'text' && next?.type === 'text') {
    prev.text = [prev.text, next.text].filter((text) => text !== '').join('\n')
    blocks.value.splice(index, 2)
  } else {
    blocks.value.splice(index, 1)
  }
  if (save) markDirty()
  nextTick(autosizeAll)
}

function onPaste(event, block) {
  const files = [...(event.clipboardData?.files || [])].filter((file) => file.type.startsWith('image/'))
  if (!files.length) return
  event.preventDefault()
  insertImages(files, { key: block.key, pos: event.target.selectionStart })
}

function onDrop(event) {
  const files = event.dataTransfer?.files
  if (!files?.length || !current.value) return
  const textarea = event.target.closest?.('textarea')
  const key = textarea ? Number(textarea.dataset.key) : null
  insertImages(files, key ? { key, pos: textarea.selectionStart } : null)
}

function onPickImages(event) {
  insertImages(event.target.files)
  event.target.value = ''
}

// ---------------------------------------------------------------- editing

function autosize(el) {
  if (!el) return
  el.style.height = 'auto'
  el.style.height = `${el.scrollHeight + 2}px`
}

function autosizeAll() {
  editorRef.value?.querySelectorAll('textarea').forEach(autosize)
}

function onInput(event, block) {
  block.text = event.target.value
  lastFocus = { key: block.key, pos: event.target.selectionStart }
  autosize(event.target)
  markDirty()
}

function rememberCursor(event, block) {
  lastFocus = { key: block.key, pos: event.target.selectionStart }
}

function markDirty() {
  editVersion += 1
  if (saveState.value !== 'conflict') saveState.value = 'dirty'
  clearTimeout(saveTimer)
  saveTimer = setTimeout(() => save(), 900)
}

async function save({ force = false } = {}) {
  clearTimeout(saveTimer)
  if (!current.value) return
  if (saving) {
    await saving
    if (saveState.value === 'dirty') return save({ force })
    return
  }
  if (saveState.value === 'saved' || (saveState.value === 'conflict' && !force)) return
  if (uploading.value) {
    saveTimer = setTimeout(() => save(), 700)
    return
  }
  const note = current.value
  const version = editVersion
  const body = serialize()
  saveState.value = 'saving'
  saving = (async () => {
    try {
      const response = await noteApi.update(note.id, { body, base_updated_at: force ? null : note.updated_at })
      note.updated_at = response.data.data.updated_at
      upsertSummary(note, body)
      saveState.value = version === editVersion ? 'saved' : 'dirty'
    } catch (err) {
      saveState.value = err.response?.status === 409 ? 'conflict' : 'error'
      if (saveState.value === 'error') actionError.value = errorText(err, t('pages.notes.saveFailed'))
    } finally {
      saving = null
    }
  })()
  await saving
  if (saveState.value === 'dirty') saveTimer = setTimeout(() => save(), 300)
}

function upsertSummary(note, body) {
  const summary = { id: note.id, pinned: note.pinned, created_at: note.created_at, updated_at: note.updated_at, ...summarize(body) }
  const rest = notes.value.filter((item) => item.id !== note.id)
  notes.value = sortNotes([summary, ...rest])
}

function sortNotes(list) {
  return [...list].sort((a, b) => Number(b.pinned) - Number(a.pinned) || new Date(b.updated_at) - new Date(a.updated_at))
}

// ---------------------------------------------------------------- notes

async function loadNotes() {
  loadingList.value = true
  listError.value = ''
  try {
    const response = await noteApi.list(query.value.trim())
    notes.value = response.data.data
  } catch (err) {
    listError.value = errorText(err, t('pages.notes.loadFailed'))
  } finally {
    loadingList.value = false
  }
}

function onSearch() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(loadNotes, 300)
}

async function closeCurrent() {
  if (!current.value) return
  await save()
  const note = current.value
  const empty = serialize() === '' && saveState.value === 'saved'
  current.value = null
  blocks.value = []
  if (empty) {
    // A note that was opened and left blank is not worth keeping.
    notes.value = notes.value.filter((item) => item.id !== note.id)
    noteApi.remove(note.id).catch(() => {})
  }
}

async function openNote(id, { edit = false } = {}) {
  if (current.value?.id === id) return
  await closeCurrent()
  actionError.value = ''
  try {
    const response = await noteApi.get(id)
    const note = response.data.data
    current.value = { id: note.id, updated_at: note.updated_at, created_at: note.created_at, pinned: note.pinned }
    blocks.value = parseBody(note.body)
    saveState.value = 'saved'
    editVersion = 0
    editing.value = edit || !note.body
    lastFocus = null
    if (route.query.note !== id) router.replace({ query: { ...route.query, note: id } })
    await nextTick()
    autosizeAll()
    if (editing.value) focusEnd()
  } catch (err) {
    actionError.value = errorText(err, t('pages.notes.loadFailed'))
    if (route.query.note) router.replace({ query: { ...route.query, note: undefined } })
  }
}

async function backToList() {
  await closeCurrent()
  router.replace({ query: { ...route.query, note: undefined } })
}

async function createNote() {
  await closeCurrent()
  try {
    const response = await noteApi.create('')
    const note = response.data.data
    upsertSummary(note, '')
    await openNote(note.id, { edit: true })
  } catch (err) {
    actionError.value = errorText(err, t('pages.notes.saveFailed'))
  }
}

function focusEnd() {
  const areas = editorRef.value?.querySelectorAll('textarea')
  const last = areas?.[areas.length - 1]
  if (last) {
    last.focus()
    last.setSelectionRange(last.value.length, last.value.length)
  }
}

async function toggleEditing() {
  if (editing.value) {
    editing.value = false
    await save()
  } else {
    editing.value = true
    await nextTick()
    autosizeAll()
  }
}

async function togglePin() {
  const note = current.value
  if (!note) return
  try {
    await save()
    const response = await noteApi.update(note.id, { pinned: !note.pinned })
    note.pinned = response.data.data.pinned
    note.updated_at = response.data.data.updated_at
    upsertSummary(note, serialize())
  } catch (err) {
    actionError.value = errorText(err, t('pages.notes.saveFailed'))
  }
}

async function deleteCurrent() {
  const note = current.value
  if (!note) return
  const ok = await dialog.confirm({
    title: t('pages.notes.deleteTitle'),
    message: t('pages.notes.deleteMessage'),
    confirmText: t('common.actions.delete'),
    danger: true
  })
  if (!ok) return
  clearTimeout(saveTimer)
  try {
    await noteApi.remove(note.id)
    notes.value = notes.value.filter((item) => item.id !== note.id)
    current.value = null
    blocks.value = []
    saveState.value = 'saved'
    router.replace({ query: { ...route.query, note: undefined } })
  } catch (err) {
    actionError.value = errorText(err, t('pages.notes.deleteFailed'))
  }
}

async function reloadLatest() {
  const id = current.value?.id
  if (!id) return
  saveState.value = 'saved'
  current.value = null
  await openNote(id)
}

function onBeforeUnload(event) {
  if (['dirty', 'saving'].includes(saveState.value) || uploading.value) {
    save()
    event.preventDefault()
    event.returnValue = ''
  }
}

function onVisibility() {
  if (document.visibilityState === 'hidden') save()
}

onBeforeRouteLeave(async () => {
  await closeCurrent()
})

onMounted(async () => {
  window.addEventListener('beforeunload', onBeforeUnload)
  document.addEventListener('visibilitychange', onVisibility)
  await loadNotes()
  if (route.query.note) await openNote(String(route.query.note))
})

onBeforeUnmount(() => {
  window.removeEventListener('beforeunload', onBeforeUnload)
  document.removeEventListener('visibilitychange', onVisibility)
  clearTimeout(saveTimer)
  clearTimeout(searchTimer)
  Object.values(imageUrls.value).forEach((url) => url && url !== 'error' && URL.revokeObjectURL(url))
})

const saveLabel = computed(() => ({
  saved: t('pages.notes.saved'),
  dirty: t('pages.notes.saving'),
  saving: t('pages.notes.saving'),
  error: t('pages.notes.saveError'),
  conflict: t('pages.notes.conflictShort')
})[saveState.value])
</script>

<template>
  <section class="xb-notes-page" :class="{ 'has-open': hasOpenNote }">
    <aside class="xb-notes-list xb-panel">
      <div class="xb-notes-list-head">
        <h2>{{ t('pages.notes.title') }}</h2>
        <button class="xb-primary-button" type="button" @click="createNote">
          <Plus :size="16" />
          {{ t('pages.notes.new') }}
        </button>
      </div>
      <label class="xb-notes-search">
        <Search :size="16" />
        <input v-model="query" type="search" :placeholder="t('pages.notes.searchPlaceholder')" @input="onSearch" />
      </label>
      <p v-if="listError" class="xb-status-note is-error">{{ listError }}</p>
      <div v-if="!loadingList && !notes.length" class="xb-notes-empty">
        <StickyNote :size="30" />
        <p>{{ query ? t('pages.notes.noMatches') : t('pages.notes.emptyList') }}</p>
      </div>
      <ul>
        <li v-for="note in notes" :key="note.id">
          <button type="button" class="xb-note-card" :class="{ 'is-active': current?.id === note.id }" @click="openNote(note.id)">
            <div>
              <strong>
                <Pin v-if="note.pinned" :size="13" />
                {{ note.title || (note.image_count ? t('pages.notes.imageNote') : t('pages.notes.untitled')) }}
              </strong>
              <span v-if="note.snippet">{{ note.snippet }}</span>
              <small>{{ formatDate(note.updated_at) }}<template v-if="note.image_count"> · {{ t('pages.notes.imageCount', { count: note.image_count }) }}</template></small>
            </div>
            <img v-if="note.cover_image_id && !['', 'error'].includes(imageUrl(note.id, note.cover_image_id))" :src="imageUrl(note.id, note.cover_image_id)" alt="" />
          </button>
        </li>
      </ul>
    </aside>

    <article class="xb-note-pane xb-panel" @dragover.prevent @drop.prevent="onDrop">
      <template v-if="current">
        <header class="xb-note-toolbar">
          <button class="xb-icon-button xb-note-back" type="button" :title="t('pages.notes.back')" @click="backToList">
            <ArrowLeft :size="18" />
          </button>
          <span class="xb-note-save" :class="`is-${saveState}`">{{ saveLabel }}</span>
          <div class="xb-note-tools">
            <label v-if="editing" class="xb-icon-button" :title="t('pages.notes.insertImage')">
              <ImagePlus :size="18" />
              <input type="file" accept="image/*" multiple hidden @change="onPickImages" />
            </label>
            <button class="xb-icon-button" type="button" :title="current.pinned ? t('pages.notes.unpin') : t('pages.notes.pin')" @click="togglePin">
              <PinOff v-if="current.pinned" :size="18" />
              <Pin v-else :size="18" />
            </button>
            <button class="xb-icon-button" type="button" :title="t('common.actions.delete')" @click="deleteCurrent">
              <Trash2 :size="18" />
            </button>
            <button class="xb-secondary-button" type="button" @click="toggleEditing">
              <Check v-if="editing" :size="16" />
              <Pencil v-else :size="16" />
              {{ editing ? t('pages.notes.done') : t('pages.notes.edit') }}
            </button>
          </div>
        </header>

        <div v-if="saveState === 'conflict'" class="xb-note-conflict">
          <span>{{ t('pages.notes.conflict') }}</span>
          <button class="xb-secondary-button" type="button" @click="reloadLatest">{{ t('pages.notes.loadLatest') }}</button>
          <button class="xb-text-button" type="button" @click="save({ force: true })">{{ t('pages.notes.keepMine') }}</button>
        </div>
        <p v-if="actionError" class="xb-status-note is-error" @click="actionError = ''">{{ actionError }}</p>

        <div ref="editorRef" class="xb-note-body" :class="{ 'is-editing': editing }">
          <template v-for="block in blocks" :key="block.key">
            <template v-if="block.type === 'text'">
              <textarea
                v-if="editing"
                :data-key="block.key"
                :value="block.text"
                :placeholder="blocks.length === 1 ? t('pages.notes.placeholder') : ''"
                rows="1"
                spellcheck="false"
                @input="onInput($event, block)"
                @click="rememberCursor($event, block)"
                @keyup="rememberCursor($event, block)"
                @paste="onPaste($event, block)"
              ></textarea>
              <div v-else-if="block.text" class="xb-note-text">{{ block.text }}</div>
            </template>
            <figure v-else class="xb-note-image" :class="{ 'is-uploading': block.uploading }">
              <img
                v-if="blockImageSrc(block) && blockImageSrc(block) !== 'error'"
                :src="blockImageSrc(block)"
                alt=""
                @click="!editing && (viewer = blockImageSrc(block))"
              />
              <span v-else-if="blockImageSrc(block) === 'error'" class="xb-note-image-missing">{{ t('pages.notes.imageMissing') }}</span>
              <span v-else class="xb-note-image-missing">…</span>
              <button v-if="editing && !block.uploading" class="xb-icon-button" type="button" :title="t('pages.notes.removeImage')" @click="removeImage(block.key)">
                <X :size="16" />
              </button>
            </figure>
          </template>
          <p v-if="!editing && !serialize()" class="xb-note-hint">{{ t('pages.notes.emptyNote') }}</p>
        </div>
      </template>
      <div v-else class="xb-notes-empty xb-note-placeholder">
        <StickyNote :size="34" />
        <p>{{ t('pages.notes.pickOrCreate') }}</p>
        <p v-if="actionError" class="xb-status-note is-error">{{ actionError }}</p>
      </div>
    </article>

    <div v-if="viewer" class="xb-note-viewer" @click="viewer = ''">
      <img :src="viewer" alt="" />
    </div>
  </section>
</template>
