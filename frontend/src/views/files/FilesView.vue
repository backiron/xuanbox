<script setup>
import { computed, onActivated, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import {
  ArrowLeft,
  Download,
  Folder,
  FolderPlus,
  Info,
  MoreHorizontal,
  MoveRight,
  Pencil,
  ReceiptText,
  RotateCcw,
  ShieldCheck,
  Star,
  Tag,
  Trash2,
  Upload
} from 'lucide-vue-next'
import PageHeader from '../../components/common/PageHeader.vue'
import EmptyState from '../../components/common/EmptyState.vue'
import DownloadToast from '../../components/common/DownloadToast.vue'
import { fileApi, folderApi, intelligenceApi, tagApi } from '../../api/fileApi'
import { vaultApi } from '../../api/vaultApi'
import { useVaultStore } from '../../stores/vaultStore'
import { receiptApi } from '../../api/receiptApi'
import { useDialogStore } from '../../stores/dialogStore'
import { findUploadLimitError } from '../../utils/uploadLimits'
import { downloadPercent, saveBlobToDevice } from '../../utils/saveFile'

const files = ref([])
const { t, locale } = useI18n()
const folders = ref([])
const allFolders = ref([])
const activeFileScope = ref('all')
const trash = ref([])
const tags = ref([])
const tagLinks = ref([])
const loading = ref(false)
const currentFolderId = ref(null)
const folderStack = ref([])
const showTrash = ref(false)
const selectedIds = ref(new Set())
const activeFile = ref(null)
const activeFileIntelligence = ref(null)
const intelligenceEditorOpen = ref(false)
const intelligenceForm = ref({})
const intelligenceLoading = ref(false)
const actionFile = ref(null)
const uploadProgress = ref(0)
const downloadProgress = ref(0)
const draggingFiles = ref(false)
const tagModalOpen = ref(false)
const tagTargetFiles = ref([])
const selectedTagId = ref('')
const editingTagId = ref('')
const tagDraft = ref({ name: '', color: '#4e83ff' })
const tagError = ref('')
const moveModalOpen = ref(false)
const moveTargetFiles = ref([])
const moveFolderId = ref(null)
const moveFolderQuery = ref('')
const moveNewFolderName = ref('')
const moveError = ref('')
const moveFolderMenuOpen = ref(false)
const dialog = useDialogStore()
const router = useRouter()
const vault = useVaultStore()
const tagPalette = ['#4e83ff', '#22c55e', '#f59e0b', '#ef4444', '#a855f7', '#06b6d4', '#f97316', '#e879f9']

const pageTitle = computed(() => currentFolderName.value)
const pageSubtitle = computed(() => t('pages.files.pageSubtitleAll'))
const currentFolderName = computed(() => folderStack.value.at(-1)?.name || t('pages.files.allFiles'))
const selectedFiles = computed(() => files.value.filter((file) => selectedIds.value.has(file.id)))
const mobileFolderPills = computed(() => uniqueFolders([...folderStack.value, ...folders.value]))
const visibleMobileFolders = computed(() => mobileFolderPills.value.slice(0, 2))
const hiddenMobileFolders = computed(() => mobileFolderPills.value.slice(2))
const filteredMoveFolders = computed(() => {
  const query = moveFolderQuery.value.trim().toLowerCase()
  return allFolders.value.filter((folder) => {
    if (!query) return true
    return [folder.name, folder.path_cache].some((value) => value?.toLowerCase().includes(query))
  })
})
const selectedMoveFolderLabel = computed(() => folderNameById(moveFolderId.value))
const latestIntelligenceTask = computed(() => activeFileIntelligence.value?.tasks?.[0] || null)
const intelligenceFields = computed(() => activeFileIntelligence.value?.fields || [])

function isImageFile(file) {
  return file.file_category === 'photo' || file.mime_type?.startsWith('image/')
}

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${Math.ceil(bytes / 1024)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

function formatDate(value) {
  return new Intl.DateTimeFormat(locale.value, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))
}

function tagsFor(fileId) {
  const ids = tagLinks.value.filter((link) => link.target_id === fileId).map((link) => link.tag_id)
  return tags.value.filter((tag) => ids.includes(tag.id))
}

function hasTag(fileId, tagId) {
  return tagLinks.value.some((link) => link.target_id === fileId && link.tag_id === tagId)
}

function docTypeLabel(type) {
  return ['receipt', 'invoice', 'contract', 'warranty', 'manual', 'statement', 'general', 'unknown'].includes(type)
    ? t(`pages.files.docTypes.${type}`)
    : type
}

const FIELD_LABEL_KEYS = {
  document_type: 'pages.files.type',
  title: 'pages.files.fields.title',
  issuer: 'pages.files.fields.issuer',
  counterparty: 'pages.files.fields.counterparty',
  primary_date: 'pages.files.fields.date',
  amount: 'pages.files.fields.amount',
  currency: 'pages.files.fields.currency',
  warranty_until: 'pages.files.fields.warrantyUntil',
  serial_number: 'pages.files.fields.serialNumber'
}

function fieldLabel(field) {
  const key = FIELD_LABEL_KEYS[field.field_key]
  return key ? t(key) : field.field_label || field.field_key
}

function taskStatusLabel(status) {
  return ['pending', 'processing', 'completed', 'confirmed', 'failed'].includes(status)
    ? t(`pages.files.taskStatus.${status}`)
    : status
}

function folderLabel(folder) {
  return folder.path_cache || folder.name
}

function folderNameById(folderId) {
  if (!folderId) return t('pages.files.allFiles')
  return allFolders.value.find((folder) => folder.id === folderId)?.name
    || folderStack.value.find((folder) => folder.id === folderId)?.name
    || t('pages.files.unknownFolder')
}

function uniqueFolders(items) {
  return Array.from(new Map(items.map((folder) => [folder.id, folder])).values())
}

async function loadFiles() {
  loading.value = true
  try {
    const params = currentFolderId.value ? { folder_id: currentFolderId.value } : {}
    const folderParams = currentFolderId.value ? { parent_id: currentFolderId.value } : {}
    const [fileResponse, folderResponse, trashResponse, tagResponse, linkResponse, rootFolderResponse] = await Promise.all([
      fileApi.list(params),
      folderApi.list(folderParams),
      fileApi.trash(),
      tagApi.list(),
      tagApi.links({ target_type: 'file' }),
      folderApi.list()
    ])
    files.value = fileResponse.data.data.filter((file) => !isImageFile(file))
    folders.value = folderResponse.data.data
    trash.value = trashResponse.data.data.filter((file) => !isImageFile(file))
    tags.value = tagResponse.data.data
    tagLinks.value = linkResponse.data.data
    allFolders.value = uniqueFolders([...rootFolderResponse.data.data, ...folderResponse.data.data, ...folderStack.value])
    selectedIds.value = new Set([...selectedIds.value].filter((id) => files.value.some((file) => file.id === id)))
    if (activeFile.value) activeFile.value = files.value.find((file) => file.id === activeFile.value.id) || activeFile.value
  } finally {
    loading.value = false
  }
}

async function uploadFiles(pickedFiles) {
  pickedFiles = Array.from(pickedFiles || [])
  if (!pickedFiles.length) return
  const limitError = findUploadLimitError(pickedFiles, t)
  if (limitError) {
    await dialog.confirm({ title: t('pages.files.uploadFailed'), message: limitError, confirmText: t('common.actions.close') })
    return
  }
  const imageFiles = pickedFiles.filter((file) => file.type.startsWith('image/'))
  if (imageFiles.length) {
    await dialog.confirm({
      title: t('pages.files.uploadInboxTitle'),
      message: t('pages.files.imagesGoToPhotos'),
      confirmText: t('pages.files.dialogOk')
    })
    return
  }
  uploadProgress.value = 1
  for (const pickedFile of pickedFiles) {
    const formData = new FormData()
    formData.append('file', pickedFile)
    if (currentFolderId.value) formData.append('folder_id', currentFolderId.value)
    await fileApi.upload(formData, {
      onUploadProgress(progressEvent) {
        if (progressEvent.total) uploadProgress.value = Math.round((progressEvent.loaded / progressEvent.total) * 100)
      }
    })
  }
  uploadProgress.value = 0
  await loadFiles()
}

async function onFileChange(event) {
  await uploadFiles(event.target.files)
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

async function createFolder() {
  const name = await dialog.prompt({ title: t('pages.files.newFolder'), label: t('pages.files.newFolderLabel'), placeholder: t('pages.files.newFolderPlaceholder') })
  if (!name) return
  await folderApi.create({ name, parent_id: currentFolderId.value })
  await loadFiles()
}

async function renameFile(file) {
  const displayName = await dialog.prompt({ title: t('pages.files.renameFile'), label: t('pages.files.renameFileLabel'), defaultValue: file.display_name })
  if (!displayName) return
  await fileApi.update(file.id, { display_name: displayName })
  await loadFiles()
}

async function renameFolder(folder) {
  const name = await dialog.prompt({ title: t('pages.files.renameFolder'), label: t('pages.files.renameFolderLabel'), defaultValue: folder.name })
  if (!name) return
  await folderApi.update(folder.id, { name })
  await loadFiles()
}

async function toggleFavorite(file) {
  await fileApi.update(file.id, { is_favorite: !file.is_favorite })
  await loadFiles()
}

async function deleteFile(file) {
  await fileApi.remove(file.id)
  if (activeFile.value?.id === file.id) activeFile.value = null
  await loadFiles()
}

async function loadFileIntelligence(file) {
  activeFileIntelligence.value = null
  if (!file) return
  intelligenceLoading.value = true
  try {
    const response = await intelligenceApi.file(file.id)
    activeFileIntelligence.value = response.data.data
  } catch {
    activeFileIntelligence.value = null
  } finally {
    intelligenceLoading.value = false
  }
}

async function openFileDetails(file) {
  activeFile.value = file
  await loadFileIntelligence(file)
}

async function retryFileIntelligence() {
  if (!activeFile.value) return
  await intelligenceApi.retry(activeFile.value.id)
  await loadFileIntelligence(activeFile.value)
}

async function saveFileAsReceipt(file = activeFile.value) {
  if (!file?.id) return
  await receiptApi.createFromFile(file.id, { category: 'file import' })
  const open = await dialog.confirm({
    title: t('pages.files.savedAsReceiptTitle'),
    message: t('pages.files.savedAsReceiptMessage'),
    confirmText: t('pages.files.openReceipts'),
    cancelText: t('common.actions.close')
  })
  if (open) await router.push('/receipts')
}

function openIntelligenceEditor() {
  const profile = activeFileIntelligence.value?.profile || {}
  intelligenceForm.value = {
    title: profile.title || activeFile.value?.display_name || '',
    summary: profile.summary || '',
    document_type: profile.document_type || 'general',
    issuer: profile.issuer || '',
    counterparty: profile.counterparty || '',
    primary_date: profile.primary_date || '',
    amount: profile.amount || '',
    currency: profile.currency || '',
    warranty_until: profile.warranty_until || '',
    serial_number: profile.serial_number || '',
    keywordsText: (profile.keywords || []).join(', '),
    labelsText: (profile.labels || []).join(', ')
  }
  intelligenceEditorOpen.value = true
}

function closeIntelligenceEditor() {
  intelligenceEditorOpen.value = false
}

async function saveIntelligenceProfile() {
  if (!activeFile.value) return
  const payload = { ...intelligenceForm.value }
  payload.keywords = String(payload.keywordsText || '').split(',').map((item) => item.trim()).filter(Boolean)
  payload.labels = String(payload.labelsText || '').split(',').map((item) => item.trim()).filter(Boolean)
  delete payload.keywordsText
  delete payload.labelsText
  Object.keys(payload).forEach((key) => {
    if (payload[key] === '') payload[key] = null
  })
  await intelligenceApi.updateProfile(activeFile.value.id, payload)
  intelligenceEditorOpen.value = false
  await loadFileIntelligence(activeFile.value)
}

function openAllFiles() {
  activeFileScope.value = 'all'
  currentFolderId.value = null
  folderStack.value = []
  activeFile.value = null
  showTrash.value = false
  loadFiles()
}

function toggleTrashPanel() {
  activeFileScope.value = 'all'
  showTrash.value = !showTrash.value
}

async function addToVault(targetFiles) {
  const list = targetFiles.filter((file) => file?.id)
  if (!list.length) return
  try {
    const done = await vault.run(async (token) => {
      for (const file of list) await vaultApi.addFile(token, file.id)
      return true
    })
    if (!done) return
    selectedIds.value = new Set()
    moveModalOpen.value = false
    activeFile.value = null
    await loadFiles()
    const open = await dialog.confirm({
      title: t('pages.vault.added'),
      message: t('pages.vault.addedCount', { count: list.length }),
      confirmText: t('pages.vault.openVault'),
      cancelText: t('common.actions.close')
    })
    if (open) await router.push('/vault')
  } catch (err) {
    await dialog.confirm({
      title: t('pages.vault.addFailed'),
      message: err.response?.data?.message || '',
      confirmText: t('pages.files.dialogOk')
    })
  }
}

function openFileActions(file) {
  actionFile.value = file
}

function closeFileActions() {
  actionFile.value = null
}

async function runFileAction(action) {
  const file = actionFile.value
  if (!file) return
  closeFileActions()
  if (action === 'download') await downloadFile(file)
  if (action === 'favorite') await toggleFavorite(file)
  if (action === 'details') await openFileDetails(file)
  if (action === 'move') moveFile(file)
  if (action === 'rename') await renameFile(file)
  if (action === 'tag') attachTag(file)
  if (action === 'important') await addToVault([file])
  if (action === 'delete') await deleteFile(file)
}

async function restoreFile(file) {
  await fileApi.restore(file.id)
  await loadFiles()
}

async function purgeFile(file) {
  const confirmed = await dialog.confirm({
    title: t('pages.files.removeFromVault'),
    message: t('pages.files.removeFromVaultMessage', { name: file.display_name }),
    confirmText: t('pages.files.removeFromVaultAction'),
    danger: true
  })
  if (!confirmed) return
  await fileApi.purge(file.id)
  await loadFiles()
}

async function moveFile(file) {
  openMoveModal([file])
}

function askToSave(file, onConfirm) {
  return dialog.confirm({
    title: t('common.saveFile.readyTitle'),
    message: t('common.saveFile.readyMessage', { name: file.name }),
    confirmText: t('common.saveFile.save'),
    cancelText: t('common.actions.cancel'),
    onConfirm
  })
}

async function downloadFile(file) {
  if (downloadProgress.value) return
  downloadProgress.value = 1
  try {
    const response = await fileApi.download(file.id, (event) => { downloadProgress.value = downloadPercent(event) })
    downloadProgress.value = 0
    await saveBlobToDevice(response.data, file.original_filename || file.display_name, askToSave)
  } catch {
    downloadProgress.value = 0
    await dialog.confirm({ title: t('common.saveFile.failed'), message: '', confirmText: t('common.actions.close') })
  }
}

async function bulkMove() {
  openMoveModal(selectedFiles.value)
}

function openMoveModal(targetFiles) {
  moveTargetFiles.value = targetFiles
  moveFolderId.value = targetFiles[0]?.folder_id || null
  moveFolderQuery.value = ''
  moveNewFolderName.value = ''
  moveError.value = ''
  moveFolderMenuOpen.value = false
  moveModalOpen.value = true
}

function closeMoveModal() {
  moveModalOpen.value = false
  moveTargetFiles.value = []
  moveFolderMenuOpen.value = false
}

function chooseMoveFolder(folderId) {
  moveFolderId.value = folderId
  moveFolderMenuOpen.value = false
  moveError.value = ''
}

async function moveFilesToFolder(targetFolderId) {
  const filesToMove = moveTargetFiles.value.filter((file) => file.folder_id !== targetFolderId)
  if (!filesToMove.length) {
    moveError.value = t('pages.files.folderExists')
    return
  }
  await Promise.all(filesToMove.map((file) => fileApi.update(file.id, { folder_id: targetFolderId })))
  if (moveTargetFiles.value.length > 1) selectedIds.value = new Set()
  closeMoveModal()
  await loadFiles()
}

async function applyMoveFolder() {
  await moveFilesToFolder(moveFolderId.value)
}

async function moveToImportantDocs() {
  await addToVault(moveTargetFiles.value)
}

async function createFolderAndMove() {
  const name = moveNewFolderName.value.trim()
  if (!name) {
    moveError.value = t('pages.files.enterFolderName')
    return
  }
  const response = await folderApi.create({ name, parent_id: currentFolderId.value })
  await moveFilesToFolder(response.data.data.id)
}

async function bulkFavorite() {
  await Promise.all(selectedFiles.value.map((file) => fileApi.update(file.id, { is_favorite: true })))
  selectedIds.value = new Set()
  await loadFiles()
}

async function bulkDelete() {
  await Promise.all(selectedFiles.value.map((file) => fileApi.remove(file.id)))
  selectedIds.value = new Set()
  activeFile.value = null
  await loadFiles()
}

function openTagModal(targetFiles = []) {
  tagTargetFiles.value = targetFiles
  selectedTagId.value = tags.value[0]?.id || ''
  editingTagId.value = ''
  tagDraft.value = { name: '', color: tagPalette[0] }
  tagError.value = ''
  tagModalOpen.value = true
}

function closeTagModal() {
  tagModalOpen.value = false
  tagTargetFiles.value = []
}

async function createTag() {
  openTagModal([])
}

async function attachTag(file) {
  openTagModal([file])
}

async function attachTagToFiles(tag, targetFiles = tagTargetFiles.value) {
  const links = targetFiles
    .filter((file) => !hasTag(file.id, tag.id))
    .map((file) => tagApi.attach(tag.id, { target_type: 'file', target_id: file.id }))
  if (links.length) await Promise.all(links)
}

function editTag(tag) {
  editingTagId.value = tag.id
  tagDraft.value = { name: tag.name, color: tag.color }
  tagError.value = ''
}

function resetTagEdit() {
  editingTagId.value = ''
  tagDraft.value = { name: '', color: tagPalette[0] }
  tagError.value = ''
}

async function applyExistingTag() {
  if (!tagTargetFiles.value.length) {
    tagError.value = t('pages.files.selectFilesFirst')
    return
  }
  if (!selectedTagId.value) {
    tagError.value = t('pages.files.chooseTagFirst')
    return
  }
  const tag = tags.value.find((item) => item.id === selectedTagId.value)
  if (!tag) return
  await attachTagToFiles(tag)
  if (tagTargetFiles.value.length > 1) selectedIds.value = new Set()
  closeTagModal()
  await loadFiles()
}

async function saveTagDraft() {
  const name = tagDraft.value.name.trim()
  if (!name) {
    tagError.value = t('pages.files.enterTagName')
    return
  }
  let tag = tags.value.find((item) => item.id === editingTagId.value)
  if (tag) {
    const response = await tagApi.update(tag.id, { name, color: tagDraft.value.color })
    tag = response.data.data
  } else {
    tag = tags.value.find((item) => item.name.toLowerCase() === name.toLowerCase())
  }
  if (!tag) {
    const response = await tagApi.create({ name, color: tagDraft.value.color })
    tag = response.data.data
  }
  if (tagTargetFiles.value.length) await attachTagToFiles(tag)
  if (tagTargetFiles.value.length > 1) selectedIds.value = new Set()
  closeTagModal()
  await loadFiles()
}

function toggleSelected(file) {
  const next = new Set(selectedIds.value)
  if (next.has(file.id)) next.delete(file.id)
  else next.add(file.id)
  selectedIds.value = next
}

function openFolder(folder) {
  const existingIndex = folderStack.value.findIndex((item) => item.id === folder.id)
  if (existingIndex !== -1) {
    folderStack.value = folderStack.value.slice(0, existingIndex + 1)
  } else {
    folderStack.value.push(folder)
  }
  currentFolderId.value = folder.id
  activeFile.value = null
  loadFiles()
}

function openRootFolder() {
  folderStack.value = []
  currentFolderId.value = null
  activeFile.value = null
  loadFiles()
}

function goBack() {
  folderStack.value.pop()
  currentFolderId.value = folderStack.value.at(-1)?.id || null
  activeFile.value = null
  loadFiles()
}

onMounted(loadFiles)
let shownOnce = false
onActivated(() => {
  if (shownOnce) loadFiles()
  shownOnce = true
})
</script>

<template>
  <div
    class="xb-upload-page xb-files-page"
    :class="{ 'is-dragging': draggingFiles }"
    @dragenter.prevent="onDragEnter"
    @dragover.prevent="draggingFiles = true"
    @dragleave="onDragLeave"
    @drop.prevent="onFileDrop"
  >
  <PageHeader :title="pageTitle" :subtitle="pageSubtitle">
    <button v-if="currentFolderId" class="xb-secondary-button" type="button" @click="goBack">
      <ArrowLeft :size="18" />
      {{ t('pages.files.back') }}
    </button>
    <button class="xb-secondary-button" type="button" @click="toggleTrashPanel">
      <Trash2 :size="18" />
      {{ t('pages.files.trash') }}
    </button>
    <button class="xb-secondary-button" type="button" @click="createTag">
      <Tag :size="18" />
      {{ t('pages.files.addTag') }}
    </button>
    <button class="xb-secondary-button" type="button" @click="createFolder">
      <FolderPlus :size="18" />
      {{ t('pages.files.newFolder') }}
    </button>
    <label class="xb-upload-button">
      <Upload :size="18" />
      {{ t('common.actions.upload') }}
      <input type="file" multiple @change="onFileChange" />
    </label>
  </PageHeader>

  <div v-if="uploadProgress" class="xb-progress">
    <span :style="{ width: `${uploadProgress}%` }"></span>
  </div>
  <DownloadToast :percent="downloadProgress" />

  <section class="xb-upload-drop-hint" :class="{ 'is-visible': draggingFiles }">
    <Upload :size="18" />
    <strong>{{ t('pages.files.dropFiles') }}</strong>
    <span>{{ currentFolderId ? t('pages.files.dropFolderHint') : t('pages.files.dropRootHint') }}</span>
  </section>

  <section class="xb-file-scope-tabs">
    <button class="xb-album-pill" :class="{ 'is-active': activeFileScope === 'all' }" type="button" @click="openAllFiles">
      <Folder :size="16" />
      {{ t('pages.files.allFiles') }}
    </button>
    <router-link class="xb-album-pill" to="/vault">
      <ShieldCheck :size="16" />
      {{ t('routes.vault') }}
    </router-link>
  </section>

  <section v-if="activeFileScope === 'all' && selectedFiles.length" class="xb-action-bar">
    <strong>{{ t('pages.photos.selectCount', { count: selectedFiles.length }) }}</strong>
    <button class="xb-text-button" type="button" @click="bulkFavorite">{{ t('pages.files.favorite') }}</button>
    <button class="xb-text-button" type="button" @click="openTagModal(selectedFiles)">
      {{ t('pages.files.addTag') }}
    </button>
    <button class="xb-text-button" type="button" @click="bulkMove">{{ t('pages.files.move') }}</button>
    <button class="xb-text-button xb-danger-button" type="button" @click="bulkDelete">{{ t('common.actions.delete') }}</button>
  </section>

  <section v-if="activeFileScope === 'all' && showTrash" class="xb-panel xb-trash-panel">
    <h3>{{ t('pages.files.trash') }}</h3>
    <p v-if="trash.length === 0">{{ t('pages.files.trashEmpty') }}</p>
    <article v-for="file in trash" :key="file.id" class="xb-file-row">
      <div>
        <strong>{{ file.display_name }}</strong>
        <span>{{ formatDate(file.updated_at) }}</span>
      </div>
      <div class="xb-row-actions">
        <button class="xb-icon-button" type="button" :title="t('pages.files.restore')" @click="restoreFile(file)">
          <RotateCcw :size="17" />
        </button>
        <button class="xb-icon-button xb-danger-button" type="button" :title="t('pages.files.purge')" @click="purgeFile(file)">
          <Trash2 :size="17" />
        </button>
      </div>
    </article>
  </section>

  <div class="xb-workspace-grid">
    <section>
      <template v-if="activeFileScope === 'all'">
      <section v-if="mobileFolderPills.length" class="xb-folder-strip-mobile">
        <button
          v-for="folder in visibleMobileFolders"
          :key="folder.id"
          class="xb-album-pill"
          :class="{ 'is-active': currentFolderId === folder.id }"
          type="button"
          @click="openFolder(folder)"
        >
          <Folder :size="16" />
          <span>{{ folder.name }}</span>
        </button>
        <details v-if="hiddenMobileFolders.length" class="xb-album-more">
          <summary class="xb-album-pill">
            <span>{{ t('common.actions.more') }}</span>
              <span aria-hidden="true">▾</span>
          </summary>
          <nav>
            <button v-for="folder in hiddenMobileFolders" :key="folder.id" type="button" @click="openFolder(folder)">
              {{ folder.name }}
            </button>
          </nav>
        </details>
      </section>

      <div v-if="folders.length" class="xb-folder-grid">
        <article v-for="folder in folders" :key="folder.id" class="xb-folder-card">
          <button type="button" @click="openFolder(folder)">
            <Folder :size="20" />
            {{ folder.name }}
          </button>
          <button class="xb-text-button" type="button" @click="renameFolder(folder)">{{ t('pages.files.rename') }}</button>
        </article>
      </div>

      <EmptyState v-if="!loading && files.length === 0 && folders.length === 0" :title="t('pages.files.noFilesHere')" :description="t('pages.files.emptyHint')" />

      <div v-else class="xb-file-list">
        <article v-for="file in files" :key="file.id" class="xb-file-row" :class="{ 'is-active': activeFile?.id === file.id }">
          <label class="xb-check">
            <input type="checkbox" :checked="selectedIds.has(file.id)" @change="toggleSelected(file)" />
          </label>
          <div class="xb-file-main">
            <strong>{{ file.display_name }}</strong>
            <span>{{ file.mime_type || 'application/octet-stream' }} · {{ formatSize(file.file_size) }}</span>
            <div v-if="tagsFor(file.id).length" class="xb-tag-list">
              <span v-for="tag in tagsFor(file.id)" :key="tag.id" :style="{ borderColor: tag.color, color: tag.color }">{{ tag.name }}</span>
            </div>
          </div>
          <span class="xb-file-date">{{ formatDate(file.updated_at) }}</span>
          <div class="xb-row-actions">
            <button class="xb-icon-button" type="button" :title="t('common.actions.download')" @click="downloadFile(file)">
              <Download :size="17" />
            </button>
            <button class="xb-icon-button" type="button" :title="t('pages.files.favorite')" @click="toggleFavorite(file)">
              <Star :size="17" :fill="file.is_favorite ? 'currentColor' : 'none'" />
            </button>
            <button class="xb-icon-button" type="button" :title="t('pages.files.detailsTitle')" @click="openFileDetails(file)">
              <Info :size="17" />
            </button>
            <button class="xb-icon-button" type="button" :title="t('pages.files.move')" @click="moveFile(file)">
              <MoveRight :size="17" />
            </button>
            <button class="xb-text-button" type="button" @click="renameFile(file)">{{ t('pages.files.rename') }}</button>
            <button class="xb-icon-button" type="button" :title="t('pages.files.tag')" @click="attachTag(file)">
              <Tag :size="17" />
            </button>
            <button class="xb-icon-button" type="button" :title="t('pages.vault.addTo')" @click="addToVault([file])">
              <ShieldCheck :size="17" />
            </button>
            <button class="xb-icon-button xb-danger-button" type="button" :title="t('common.actions.delete')" @click="deleteFile(file)">
              <Trash2 :size="17" />
            </button>
            <button class="xb-icon-button xb-file-more-button" type="button" :title="t('pages.files.moreActions')" @click="openFileActions(file)">
              <MoreHorizontal :size="18" />
            </button>
          </div>
        </article>
      </div>
      </template>

    </section>

    <aside class="xb-detail-drawer" :class="{ 'is-open': activeFile }">
      <template v-if="activeFile">
        <button class="xb-text-button" type="button" @click="activeFile = null">{{ t('common.actions.close') }}</button>
        <h3>{{ activeFile.display_name }}</h3>
        <dl>
          <div><dt>{{ t('pages.files.original') }}</dt><dd>{{ activeFile.original_filename }}</dd></div>
          <div><dt>{{ t('pages.files.location') }}</dt><dd>{{ folderNameById(activeFile.folder_id) }}</dd></div>
          <div><dt>{{ t('pages.files.type') }}</dt><dd>{{ activeFile.mime_type || 'application/octet-stream' }}</dd></div>
          <div><dt>{{ t('pages.files.size') }}</dt><dd>{{ formatSize(activeFile.file_size) }}</dd></div>
          <div><dt>{{ t('pages.files.hash') }}</dt><dd>{{ activeFile.sha256_hash }}</dd></div>
          <div><dt>{{ t('pages.files.created') }}</dt><dd>{{ formatDate(activeFile.created_at) }}</dd></div>
          <div><dt>{{ t('pages.files.updated') }}</dt><dd>{{ formatDate(activeFile.updated_at) }}</dd></div>
        </dl>
        <div class="xb-tag-list">
          <span v-for="tag in tagsFor(activeFile.id)" :key="tag.id" :style="{ borderColor: tag.color, color: tag.color }">{{ tag.name }}</span>
        </div>
        <button class="xb-secondary-button" type="button" @click="attachTag(activeFile)">
          <Tag :size="17" />
          {{ t('pages.files.addTag') }}
        </button>
        <button class="xb-secondary-button" type="button" @click="moveFile(activeFile)">
          <MoveRight :size="17" />
          {{ t('pages.files.move') }}
        </button>
        <button class="xb-secondary-button" type="button" @click="saveFileAsReceipt(activeFile)">
          <ReceiptText :size="17" />
          {{ t('pages.files.saveAsReceipt') }}
        </button>
        <section class="xb-intelligence-panel">
          <div class="xb-intelligence-head">
            <div>
              <strong>{{ t('pages.files.intelligence') }}</strong>
              <span v-if="intelligenceLoading">{{ t('pages.files.loadingLabel') }}</span>
              <span v-else>{{ latestIntelligenceTask?.status ? taskStatusLabel(latestIntelligenceTask.status) : t('pages.files.notQueued') }}</span>
            </div>
            <div class="xb-row-actions">
              <button class="xb-text-button" type="button" @click="openIntelligenceEditor">
                {{ activeFileIntelligence?.profile ? t('common.actions.edit') : t('pages.files.createProfile') }}
              </button>
              <button class="xb-text-button" type="button" @click="retryFileIntelligence">{{ t('pages.files.retry') }}</button>
            </div>
          </div>
          <template v-if="activeFileIntelligence?.profile">
            <dl>
              <div><dt>{{ t('pages.files.type') }}</dt><dd>{{ docTypeLabel(activeFileIntelligence.profile.document_type) }}</dd></div>
              <div><dt>{{ t('pages.files.fields.title') }}</dt><dd>{{ activeFileIntelligence.profile.title || t('pages.files.untitled') }}</dd></div>
              <div v-if="activeFileIntelligence.profile.summary"><dt>{{ t('pages.files.fields.summary') }}</dt><dd>{{ activeFileIntelligence.profile.summary }}</dd></div>
              <div v-if="activeFileIntelligence.profile.issuer"><dt>{{ t('pages.files.fields.issuer') }}</dt><dd>{{ activeFileIntelligence.profile.issuer }}</dd></div>
              <div v-if="activeFileIntelligence.profile.counterparty"><dt>{{ t('pages.files.fields.counterparty') }}</dt><dd>{{ activeFileIntelligence.profile.counterparty }}</dd></div>
              <div v-if="activeFileIntelligence.profile.amount"><dt>{{ t('pages.files.fields.amount') }}</dt><dd>{{ activeFileIntelligence.profile.currency }} {{ activeFileIntelligence.profile.amount }}</dd></div>
              <div v-if="activeFileIntelligence.profile.serial_number"><dt>{{ t('pages.files.fields.serial') }}</dt><dd>{{ activeFileIntelligence.profile.serial_number }}</dd></div>
            </dl>
            <div v-if="activeFileIntelligence.profile.labels?.length" class="xb-tag-list">
              <span v-for="label in activeFileIntelligence.profile.labels" :key="label">{{ label }}</span>
            </div>
            <div v-if="intelligenceFields.length" class="xb-intelligence-fields">
              <span v-for="field in intelligenceFields" :key="field.id">
                <strong>{{ fieldLabel(field) }}</strong>
                {{ field.field_key === 'document_type' ? docTypeLabel(field.field_value) : field.field_value }}
              </span>
            </div>
            <p class="xb-inline-help">
              {{ activeFileIntelligence.profile.confirmed_at ? t('pages.files.confirmedByYou') : t('pages.files.confirmFields') }}
            </p>
          </template>
          <p v-else-if="latestIntelligenceTask?.error_message" class="xb-form-error">{{ latestIntelligenceTask.error_message }}</p>
          <p v-else class="xb-muted">{{ t('pages.files.textExtraction') }}</p>
          <details v-if="activeFileIntelligence?.chunks?.length" class="xb-intelligence-text">
            <summary>{{ t('pages.files.extractedText') }}</summary>
            <p v-for="chunk in activeFileIntelligence.chunks.slice(0, 2)" :key="chunk.id">{{ chunk.text }}</p>
          </details>
        </section>
      </template>
      <template v-else>
        <h3>{{ t('pages.files.detailsTitle') }}</h3>
        <p>{{ t('pages.files.detailsHint') }}</p>
      </template>
    </aside>
  </div>

  <Teleport to="body">
    <section v-if="actionFile" class="xb-mobile-action-backdrop" @click.self="closeFileActions">
      <div class="xb-mobile-action-sheet">
        <header>
          <div>
            <strong>{{ actionFile.display_name }}</strong>
            <span>{{ actionFile.mime_type || 'application/octet-stream' }} · {{ formatSize(actionFile.file_size) }}</span>
          </div>
          <button class="xb-icon-button" type="button" :title="t('common.actions.close')" @click="closeFileActions">×</button>
        </header>
        <div class="xb-mobile-action-grid">
          <button type="button" @click="runFileAction('download')">
            <Download :size="18" />
            {{ t('common.actions.download') }}
          </button>
          <button type="button" @click="runFileAction('favorite')">
            <Star :size="18" :fill="actionFile.is_favorite ? 'currentColor' : 'none'" />
            {{ actionFile.is_favorite ? t('pages.files.unfavorite') : t('pages.files.favorite') }}
          </button>
          <button type="button" @click="runFileAction('details')">
            <Info :size="18" />
            {{ t('pages.files.detailsTitle') }}
          </button>
          <button type="button" @click="runFileAction('move')">
            <MoveRight :size="18" />
            {{ t('pages.files.move') }}
          </button>
          <button type="button" @click="runFileAction('rename')">
            <Pencil :size="18" />
            {{ t('pages.files.rename') }}
          </button>
          <button type="button" @click="runFileAction('tag')">
            <Tag :size="18" />
            {{ t('pages.files.tag') }}
          </button>
          <button type="button" @click="runFileAction('important')">
            <ShieldCheck :size="18" />
            {{ t('pages.vault.addTo') }}
          </button>
          <button class="is-danger" type="button" @click="runFileAction('delete')">
            <Trash2 :size="18" />
            {{ t('common.actions.delete') }}
          </button>
        </div>
      </div>
    </section>
  </Teleport>


  <Teleport to="body">
    <section v-if="intelligenceEditorOpen" class="xb-modal-backdrop" @click.self="closeIntelligenceEditor">
      <form class="xb-modal xb-intelligence-editor" @submit.prevent="saveIntelligenceProfile">
        <Info :size="24" />
        <h3>{{ t('pages.files.reviewProfile') }}</h3>
        <p>{{ t('pages.files.reviewHint') }}</p>
        <label>
          {{ t('pages.files.type') }}
          <select v-model="intelligenceForm.document_type">
            <option value="receipt">{{ t('pages.files.docTypes.receipt') }}</option>
            <option value="invoice">{{ t('pages.files.docTypes.invoice') }}</option>
            <option value="contract">{{ t('pages.files.docTypes.contract') }}</option>
            <option value="warranty">{{ t('pages.files.docTypes.warranty') }}</option>
            <option value="manual">{{ t('pages.files.docTypes.manual') }}</option>
            <option value="statement">{{ t('pages.files.docTypes.statement') }}</option>
            <option value="general">{{ t('pages.files.docTypes.general') }}</option>
            <option value="unknown">{{ t('pages.files.docTypes.unknown') }}</option>
          </select>
        </label>
        <label>
          {{ t('pages.files.fields.title') }}
          <input v-model="intelligenceForm.title" maxlength="255" />
        </label>
        <label>
          {{ t('pages.files.fields.summary') }}
          <textarea v-model="intelligenceForm.summary" rows="4" maxlength="4000"></textarea>
        </label>
        <div class="xb-two-column-form">
          <label>
            {{ t('pages.files.fields.issuer') }}
            <input v-model="intelligenceForm.issuer" maxlength="255" />
          </label>
          <label>
            {{ t('pages.files.fields.counterparty') }}
            <input v-model="intelligenceForm.counterparty" maxlength="255" />
          </label>
          <label>
            {{ t('pages.files.fields.date') }}
            <input v-model="intelligenceForm.primary_date" maxlength="32" />
          </label>
          <label>
            {{ t('pages.files.fields.warrantyUntil') }}
            <input v-model="intelligenceForm.warranty_until" maxlength="32" />
          </label>
          <label>
            {{ t('pages.files.fields.amount') }}
            <input v-model="intelligenceForm.amount" maxlength="64" />
          </label>
          <label>
            {{ t('pages.files.fields.currency') }}
            <input v-model="intelligenceForm.currency" maxlength="16" />
          </label>
          <label>
            {{ t('pages.files.fields.serialNumber') }}
            <input v-model="intelligenceForm.serial_number" maxlength="120" />
          </label>
          <label>
            {{ t('pages.files.fields.labels') }}
            <input v-model="intelligenceForm.labelsText" :placeholder="t('pages.files.labelsPlaceholder')" />
          </label>
        </div>
        <label>
          {{ t('pages.files.fields.keywords') }}
          <input v-model="intelligenceForm.keywordsText" :placeholder="t('pages.files.keywordsPlaceholder')" />
        </label>
        <div class="xb-row-actions">
          <button class="xb-primary-button" type="submit">{{ t('pages.files.confirmProfile') }}</button>
          <button class="xb-secondary-button" type="button" @click="closeIntelligenceEditor">{{ t('common.actions.cancel') }}</button>
        </div>
      </form>
    </section>
  </Teleport>

  <Teleport to="body">
    <section v-if="tagModalOpen" class="xb-modal-backdrop" @click.self="closeTagModal">
      <form class="xb-modal xb-tag-modal" @submit.prevent="saveTagDraft">
        <Tag :size="24" />
        <h3>{{ tagTargetFiles.length ? t('pages.files.applyTagTitle') : t('pages.files.tagsTitle') }}</h3>
        <p>
          {{ tagTargetFiles.length ? t('pages.files.tagHintApply') : t('pages.files.tagHintManage') }}
        </p>

        <div v-if="tags.length" class="xb-tag-picker">
          <div
            v-for="tag in tags"
            :key="tag.id"
            class="xb-tag-option"
            :class="{ 'is-active': tagTargetFiles.length && selectedTagId === tag.id, 'is-editing': editingTagId === tag.id }"
            :style="{ '--tag-color': tag.color }"
          >
            <button type="button" @click="tagTargetFiles.length && (selectedTagId = tag.id)">
              <span></span>
              {{ tag.name }}
            </button>
            <button type="button" :title="t('pages.files.editTag')" @click="editTag(tag)">
              <Pencil :size="14" />
            </button>
          </div>
        </div>
        <p v-else class="xb-inline-help">{{ t('pages.files.noTags') }}</p>

        <button
          v-if="tagTargetFiles.length && tags.length"
          class="xb-secondary-button"
          type="button"
          :disabled="!selectedTagId"
          @click="applyExistingTag"
        >
          {{ t('pages.files.applyTag') }}
        </button>

        <div class="xb-tag-divider">
          <span>{{ editingTagId ? t('pages.files.editTagTitle') : (tags.length ? t('pages.files.createTagFallback') : t('pages.files.createTag')) }}</span>
        </div>
        <p v-if="tagError" class="xb-form-error">{{ tagError }}</p>

        <label>
          {{ t('pages.files.tagNameLabel') }}
          <input v-model="tagDraft.name" :placeholder="t('pages.files.tagNamePlaceholder')" autocomplete="off" />
        </label>

        <div class="xb-color-field">
          <span>{{ t('pages.files.color') }}</span>
          <div class="xb-color-picker">
            <button
              v-for="color in tagPalette"
              :key="color"
              type="button"
              :class="{ 'is-active': tagDraft.color === color }"
              :style="{ backgroundColor: color }"
              :title="color"
              @click="tagDraft.color = color"
            ></button>
            <input v-model="tagDraft.color" type="color" :title="t('pages.files.customColor')" />
          </div>
        </div>

        <div class="xb-row-actions">
          <button class="xb-primary-button" type="submit">
            {{ editingTagId ? t('pages.files.saveTag') : (tagTargetFiles.length ? t('pages.files.createAndApply') : t('pages.files.createTagTitle')) }}
          </button>
          <button v-if="editingTagId" class="xb-secondary-button" type="button" @click="resetTagEdit">{{ t('pages.files.cancelEditTag') }}</button>
          <button class="xb-secondary-button" type="button" @click="closeTagModal">{{ t('common.actions.cancel') }}</button>
        </div>
      </form>
    </section>
  </Teleport>

  <Teleport to="body">
    <section v-if="moveModalOpen" class="xb-modal-backdrop" @click.self="closeMoveModal">
      <form class="xb-modal xb-move-modal" @submit.prevent="applyMoveFolder">
        <MoveRight :size="24" />
        <h3>{{ moveTargetFiles.length > 1 ? t('pages.files.moveFilesTitle') : t('pages.files.moveFileTitle') }}</h3>
        <p>{{ t('pages.files.moveHint') }}</p>

        <label>
          {{ t('pages.files.searchFolders') }}
          <input v-model="moveFolderQuery" :placeholder="t('pages.files.searchFoldersPlaceholder')" autocomplete="off" />
        </label>

        <div class="xb-folder-select">
          <Folder :size="17" />
          <div class="xb-folder-combobox">
            <button type="button" @click="moveFolderMenuOpen = !moveFolderMenuOpen">
              <span>{{ selectedMoveFolderLabel }}</span>
              <span aria-hidden="true">▾</span>
            </button>
            <div v-if="moveFolderMenuOpen" class="xb-folder-menu">
              <button type="button" :class="{ 'is-active': moveFolderId === null }" @click="chooseMoveFolder(null)">
                {{ t('pages.files.allFiles') }}
              </button>
              <button
                v-for="folder in filteredMoveFolders"
                :key="folder.id"
                type="button"
                :class="{ 'is-active': moveFolderId === folder.id }"
                @click="chooseMoveFolder(folder.id)"
              >
                {{ folderLabel(folder) }}
              </button>
            </div>
          </div>
          <p v-if="!filteredMoveFolders.length" class="xb-inline-help">{{ t('pages.files.noMatchingFolder') }}</p>
        </div>

        <div class="xb-tag-divider">
          <span>{{ t('pages.files.createNewFolder') }}</span>
        </div>

        <label>
          {{ t('pages.files.renameFolderLabel') }}
          <input v-model="moveNewFolderName" :placeholder="t('pages.files.moveFolderPlaceholder')" autocomplete="off" />
        </label>
        <p v-if="moveError" class="xb-form-error">{{ moveError }}</p>

        <div class="xb-row-actions">
          <button class="xb-primary-button" type="submit">{{ t('pages.files.moveHere') }}</button>
          <button class="xb-secondary-button" type="button" @click="moveToImportantDocs">
            <ShieldCheck :size="17" />
            {{ t('pages.vault.addTo') }}
          </button>
          <button class="xb-secondary-button" type="button" @click="createFolderAndMove">{{ t('pages.files.createAndMove') }}</button>
          <button class="xb-secondary-button" type="button" @click="closeMoveModal">{{ t('common.actions.cancel') }}</button>
        </div>
      </form>
    </section>
  </Teleport>
  </div>
</template>
