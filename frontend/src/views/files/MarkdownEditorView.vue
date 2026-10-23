<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { onBeforeRouteLeave, useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import {
  AlertTriangle,
  ArrowLeft,
  Bold,
  Check,
  CloudOff,
  Code,
  Columns2,
  Download,
  Eye,
  Heading,
  Italic,
  Link,
  List,
  ListChecks,
  ListOrdered,
  Loader2,
  Pencil,
  Quote
} from 'lucide-vue-next'
import { fileApi } from '../../api/fileApi'
import { useAuthStore } from '../../stores/authStore'
import { useDialogStore } from '../../stores/dialogStore'
import { saveBlobToDevice } from '../../utils/saveFile'
import { renderMarkdown } from '../../utils/markdown'
import '../../styles/markdown.css'

const route = useRoute()
const router = useRouter()
const { t } = useI18n()
const authStore = useAuthStore()
const dialog = useDialogStore()

const file = ref(null)
const editable = ref(true)
const content = ref('')
const loading = ref(true)
const loadError = ref('')
const actionError = ref('')
const saveState = ref('saved') // saved | dirty | saving | error | conflict
const narrow = ref(window.matchMedia('(max-width: 860px)').matches)
const mode = ref(route.query.mode === 'preview' ? 'preview' : narrow.value ? 'edit' : 'split')
const textareaRef = ref(null)
let editVersion = 0
let saveTimer = null
let saving = null
const narrowQuery = window.matchMedia('(max-width: 860px)')

const isPro = computed(() => authStore.user?.plan === 'pro')
const html = computed(() => renderMarkdown(content.value))
const saveLabel = computed(() => ({
  saved: t('pages.markdown.saved'),
  dirty: t('pages.markdown.saving'),
  saving: t('pages.markdown.saving'),
  error: t('pages.markdown.saveError'),
  conflict: t('pages.markdown.conflictShort')
})[saveState.value])

function errorText(err, fallback) {
  return err.response?.data?.message || fallback
}

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    if (!authStore.user) await authStore.loadMe()
    if (!isPro.value) return
    const response = await fileApi.readMarkdown(route.params.id)
    file.value = response.data.data.file
    content.value = response.data.data.content
    editable.value = response.data.data.editable !== false
    if (!editable.value) mode.value = 'preview'
    editVersion = 0
    saveState.value = 'saved'
  } catch (err) {
    loadError.value = errorText(err, t('pages.markdown.loadFailed'))
  } finally {
    loading.value = false
  }
}

function onInput() {
  if (!editable.value) return
  editVersion += 1
  if (saveState.value !== 'conflict') saveState.value = 'dirty'
  clearTimeout(saveTimer)
  saveTimer = setTimeout(() => save(), 1200)
}

async function save({ force = false } = {}) {
  clearTimeout(saveTimer)
  if (!file.value) return
  if (saving) {
    await saving
    if (saveState.value === 'dirty') return save({ force })
    return
  }
  if (saveState.value === 'saved' || (saveState.value === 'conflict' && !force)) return
  const version = editVersion
  const body = content.value
  saveState.value = 'saving'
  saving = (async () => {
    try {
      const response = await fileApi.saveMarkdown(file.value.id, { content: body, base_sha256: force ? null : file.value.sha256_hash })
      file.value = response.data.data.file
      saveState.value = version === editVersion ? 'saved' : 'dirty'
      actionError.value = ''
    } catch (err) {
      saveState.value = err.response?.status === 409 ? 'conflict' : 'error'
      if (saveState.value === 'error') actionError.value = errorText(err, t('pages.markdown.saveFailed'))
    } finally {
      saving = null
    }
  })()
  await saving
  if (saveState.value === 'dirty') saveTimer = setTimeout(() => save(), 300)
}

async function reloadLatest() {
  await load()
}

async function saveAsCopy() {
  const stem = (file.value.display_name || 'untitled').replace(/\.(md|markdown)$/i, '')
  try {
    const response = await fileApi.createMarkdown({
      name: `${stem} ${t('pages.markdown.copySuffix')}`,
      content: content.value,
      folder_id: file.value.folder_id
    })
    saveState.value = 'saved'
    await router.replace({ name: 'markdown-editor', params: { id: response.data.data.file.id } })
  } catch (err) {
    actionError.value = errorText(err, t('pages.markdown.saveFailed'))
  }
}

function askToSave(item, onConfirm) {
  return dialog.confirm({
    title: t('common.saveFile.readyTitle'),
    message: t('common.saveFile.readyMessage', { name: item.name }),
    confirmText: t('common.saveFile.save'),
    cancelText: t('common.actions.cancel'),
    onConfirm
  })
}

// The text is already here, so save what is on screen without another round trip.
async function download() {
  const name = /\.(md|markdown)$/i.test(file.value.display_name) ? file.value.display_name : `${file.value.display_name}.md`
  await saveBlobToDevice(new Blob([content.value], { type: 'text/markdown;charset=utf-8' }), name, askToSave)
}

// Wrap the selection (or insert a placeholder) and keep the cursor inside the markup.
function wrap(before, after = before, placeholder = '') {
  const el = textareaRef.value
  if (!el) return
  const start = el.selectionStart
  const end = el.selectionEnd
  const selected = content.value.slice(start, end) || placeholder
  content.value = content.value.slice(0, start) + before + selected + after + content.value.slice(end)
  onInput()
  nextTick(() => {
    el.focus()
    el.setSelectionRange(start + before.length, start + before.length + selected.length)
  })
}

// Prefix every selected line (headings, lists, quotes).
function prefixLines(prefix) {
  const el = textareaRef.value
  if (!el) return
  const start = content.value.lastIndexOf('\n', el.selectionStart - 1) + 1
  const end = el.selectionEnd
  const lines = content.value.slice(start, end).split('\n')
  const replaced = lines.map((line, index) => (typeof prefix === 'function' ? prefix(index) : prefix) + line).join('\n')
  content.value = content.value.slice(0, start) + replaced + content.value.slice(end)
  onInput()
  nextTick(() => {
    el.focus()
    el.setSelectionRange(start, start + replaced.length)
  })
}

const tools = [
  { key: 'heading', icon: Heading, run: () => prefixLines('## ') },
  { key: 'bold', icon: Bold, run: () => wrap('**', '**', t('pages.markdown.sampleText')) },
  { key: 'italic', icon: Italic, run: () => wrap('*', '*', t('pages.markdown.sampleText')) },
  { key: 'list', icon: List, run: () => prefixLines('- ') },
  { key: 'ordered', icon: ListOrdered, run: () => prefixLines((index) => `${index + 1}. `) },
  { key: 'task', icon: ListChecks, run: () => prefixLines('- [ ] ') },
  { key: 'quote', icon: Quote, run: () => prefixLines('> ') },
  { key: 'code', icon: Code, run: () => wrap('`', '`', 'code') },
  { key: 'link', icon: Link, run: () => wrap('[', '](https://)', t('pages.markdown.sampleText')) }
]

function onKeydown(event) {
  const mod = event.ctrlKey || event.metaKey
  if (mod && event.key.toLowerCase() === 's') {
    event.preventDefault()
    save({ force: false })
  } else if (mod && event.key.toLowerCase() === 'b') {
    event.preventDefault()
    wrap('**', '**', t('pages.markdown.sampleText'))
  } else if (mod && event.key.toLowerCase() === 'i') {
    event.preventDefault()
    wrap('*', '*', t('pages.markdown.sampleText'))
  } else if (event.key === 'Tab' && event.target === textareaRef.value) {
    event.preventDefault()
    wrap('  ', '', '')
  }
}

function onBeforeUnload(event) {
  if (['dirty', 'saving'].includes(saveState.value)) {
    save()
    event.preventDefault()
    event.returnValue = ''
  }
}

function onVisibility() {
  if (document.visibilityState === 'hidden') save()
}

function onNarrowChange(event) {
  narrow.value = event.matches
  if (event.matches && mode.value === 'split') mode.value = 'edit'
}

function goBack() {
  if (window.history.state?.back) router.back()
  else router.push('/files')
}

watch(() => route.params.id, async (id, previous) => {
  if (id && id !== previous) await load()
})

onBeforeRouteLeave(async () => {
  await save()
  if (['dirty', 'error', 'conflict'].includes(saveState.value)) {
    return dialog.confirm({ title: t('pages.markdown.leaveTitle'), message: t('pages.markdown.leaveUnsaved'), confirmText: t('pages.markdown.leaveAnyway') })
  }
})

onMounted(async () => {
  window.addEventListener('beforeunload', onBeforeUnload)
  document.addEventListener('visibilitychange', onVisibility)
  narrowQuery.addEventListener('change', onNarrowChange)
  await load()
})

onBeforeUnmount(() => {
  window.removeEventListener('beforeunload', onBeforeUnload)
  document.removeEventListener('visibilitychange', onVisibility)
  narrowQuery.removeEventListener('change', onNarrowChange)
  clearTimeout(saveTimer)
})
</script>

<template>
  <div class="xb-md-page" @keydown="onKeydown">
    <header class="xb-md-head xb-panel">
      <button class="xb-icon-button" type="button" :title="t('pages.markdown.back')" @click="goBack">
        <ArrowLeft :size="18" />
      </button>
      <div class="xb-md-title">
        <strong>{{ file?.display_name || t('routes.markdown') }}</strong>
        <span v-if="file" class="xb-md-save" :class="`is-${saveState}`" role="status">
          <Loader2 v-if="saveState === 'saving' || saveState === 'dirty'" :size="14" />
          <CloudOff v-else-if="saveState === 'error'" :size="14" />
          <AlertTriangle v-else-if="saveState === 'conflict'" :size="14" />
          <Check v-else :size="14" />
          {{ saveLabel }}
        </span>
      </div>
      <div v-if="file && editable" class="xb-md-modes" role="group" :aria-label="t('pages.markdown.view')">
        <button type="button" :class="{ 'is-active': mode === 'edit' }" :title="t('pages.markdown.modeEdit')" @click="mode = 'edit'">
          <Pencil :size="16" /><span>{{ t('pages.markdown.modeEdit') }}</span>
        </button>
        <button v-if="!narrow" type="button" :class="{ 'is-active': mode === 'split' }" :title="t('pages.markdown.modeSplit')" @click="mode = 'split'">
          <Columns2 :size="16" /><span>{{ t('pages.markdown.modeSplit') }}</span>
        </button>
        <button type="button" :class="{ 'is-active': mode === 'preview' }" :title="t('pages.markdown.modePreview')" @click="mode = 'preview'">
          <Eye :size="16" /><span>{{ t('pages.markdown.modePreview') }}</span>
        </button>
      </div>
      <button v-if="file" class="xb-icon-button" type="button" :title="t('common.actions.download')" @click="download">
        <Download :size="18" />
      </button>
    </header>

    <p v-if="loading" class="xb-status-note">{{ t('pages.markdown.loading') }}</p>
    <section v-else-if="!isPro" class="xb-md-upsell xb-panel">
      <strong>{{ t('pages.markdown.proOnlyTitle') }}</strong>
      <p>{{ t('pages.markdown.proOnly') }}</p>
      <button class="xb-secondary-button" type="button" @click="router.push('/files')">{{ t('pages.markdown.backToFiles') }}</button>
    </section>
    <p v-else-if="loadError" class="xb-status-note is-error">{{ loadError }}</p>

    <template v-else-if="file">
      <div v-if="!editable" class="xb-md-conflict">
        <span>{{ t('pages.markdown.notUtf8') }}</span>
      </div>
      <div v-if="saveState === 'conflict'" class="xb-md-conflict">
        <span>{{ t('pages.markdown.conflict') }}</span>
        <button class="xb-secondary-button" type="button" @click="reloadLatest">{{ t('pages.markdown.loadLatest') }}</button>
        <button class="xb-secondary-button" type="button" @click="saveAsCopy">{{ t('pages.markdown.saveAsCopy') }}</button>
        <button class="xb-text-button" type="button" @click="save({ force: true })">{{ t('pages.markdown.keepMine') }}</button>
      </div>
      <p v-if="actionError" class="xb-status-note is-error" @click="actionError = ''">{{ actionError }}</p>

      <div class="xb-md-body" :class="`is-${mode}`">
        <section v-show="mode !== 'preview'" class="xb-md-editor xb-panel">
          <div class="xb-md-tools">
            <button v-for="tool in tools" :key="tool.key" class="xb-icon-button" type="button" :title="t(`pages.markdown.tools.${tool.key}`)" @mousedown.prevent @click="tool.run">
              <component :is="tool.icon" :size="16" />
            </button>
          </div>
          <textarea
            ref="textareaRef"
            v-model="content"
            class="xb-md-textarea"
            spellcheck="false"
            :placeholder="t('pages.markdown.placeholder')"
            @input="onInput"
          ></textarea>
        </section>
        <!-- Real DOM text so browser translate/select extensions work on the preview. -->
        <article v-show="mode !== 'edit'" class="xb-md-preview xb-panel">
          <div v-if="content.trim()" class="xb-md-rendered" v-html="html"></div>
          <p v-else class="xb-md-empty">{{ t('pages.markdown.emptyPreview') }}</p>
        </article>
      </div>
    </template>
  </div>
</template>
