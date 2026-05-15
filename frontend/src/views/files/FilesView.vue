<script setup>
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
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
import { fileApi, folderApi, importantDocApi, intelligenceApi, tagApi } from '../../api/fileApi'
import { receiptApi } from '../../api/receiptApi'
import { useDialogStore } from '../../stores/dialogStore'
import { findUploadLimitError } from '../../utils/uploadLimits'

const files = ref([])
const { t } = useI18n()
const folders = ref([])
const allFolders = ref([])
const importantDocs = ref([])
const importantDocsLoading = ref(false)
const importantStatus = ref({ pin_set: false, locked_until: null })
const importantUnlockToken = ref('')
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
const importantActionDoc = ref(null)
const uploadProgress = ref(0)
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
const vaultModalMode = ref('')
const vaultPin = ref('')
const vaultPinConfirm = ref('')
const vaultPinError = ref('')
const pendingImportantFile = ref(null)
const dialog = useDialogStore()
const tagPalette = ['#4e83ff', '#22c55e', '#f59e0b', '#ef4444', '#a855f7', '#06b6d4', '#f97316', '#e879f9']

const pageTitle = computed(() => activeFileScope.value === 'important' ? t('pages.files.importantDocs') : currentFolderName.value)
const pageSubtitle = computed(() => activeFileScope.value === 'important'
  ? t('pages.files.pageSubtitleImportant')
  : t('pages.files.pageSubtitleAll'))
const currentFolderName = computed(() => folderStack.value.at(-1)?.name || t('pages.files.allFiles'))
const selectedFiles = computed(() => files.value.filter((file) => selectedIds.value.has(file.id)))
const visibleMobileFolders = computed(() => folders.value.slice(0, 2))
const hiddenMobileFolders = computed(() => folders.value.slice(2))
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
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))
}

function tagsFor(fileId) {
  const ids = tagLinks.value.filter((link) => link.target_id === fileId).map((link) => link.tag_id)
  return tags.value.filter((tag) => ids.includes(tag.id))
}

function hasTag(fileId, tagId) {
  return tagLinks.value.some((link) => link.target_id === fileId && link.tag_id === tagId)
}

function folderLabel(folder) {
  return folder.path_cache || folder.name
}

function folderNameById(folderId) {
  if (!folderId) return t('pages.files.allFiles')
  return allFolders.value.find((folder) => folder.id === folderId)?.name
    || folderStack.value.find((folder) => folder.id === folderId)?.name
    || 'Unknown folder'
}

function uniqueFolders(items) {
  return Array.from(new Map(items.map((folder) => [folder.id, folder])).values())
}

async function loadFiles() {
  loading.value = true
  try {
    const params = currentFolderId.value ? { folder_id: currentFolderId.value } : { root_only: true }
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
      title: 'Use Inbox for images',
      message: 'Images are managed in Photos. Use Dashboard or Inbox if you want to decide whether an image should become a Photo, File, or Receipt.',
      confirmText: 'OK'
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
  const name = await dialog.prompt({ title: 'New folder', label: 'Folder name', placeholder: 'Family documents' })
  if (!name) return
  await folderApi.create({ name, parent_id: currentFolderId.value })
  await loadFiles()
}

async function renameFile(file) {
  const displayName = await dialog.prompt({ title: 'Rename file', label: 'New name', defaultValue: file.display_name })
  if (!displayName) return
  await fileApi.update(file.id, { display_name: displayName })
  await loadFiles()
}

async function renameFolder(folder) {
  const name = await dialog.prompt({ title: 'Rename folder', label: 'New folder name', defaultValue: folder.name })
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
  await dialog.confirm({
    title: 'Saved as receipt',
    message: 'This item now appears in Receipts. OCR will run in the background and you can review fields there.',
    confirmText: 'Open Receipts'
  })
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

async function refreshImportantStatus() {
  const response = await importantDocApi.status()
  importantStatus.value = response.data.data
}

async function loadImportantDocs() {
  if (!importantUnlockToken.value) return
  importantDocsLoading.value = true
  try {
    const response = await importantDocApi.list(importantUnlockToken.value)
    importantDocs.value = response.data.data
  } catch (err) {
    importantUnlockToken.value = ''
    openVaultModal(importantStatus.value.pin_set ? 'unlock' : 'setup')
  } finally {
    importantDocsLoading.value = false
  }
}

async function openImportantDocs() {
  activeFileScope.value = 'important'
  selectedIds.value = new Set()
  activeFile.value = null
  showTrash.value = false
  await refreshImportantStatus()
  if (!importantStatus.value.pin_set || !importantUnlockToken.value) {
    openVaultModal(importantStatus.value.pin_set ? 'unlock' : 'setup')
    return
  }
  await loadImportantDocs()
}

function openAllFiles() {
  activeFileScope.value = 'all'
  activeFile.value = null
}

function toggleTrashPanel() {
  activeFileScope.value = 'all'
  showTrash.value = !showTrash.value
}

function openVaultModal(mode) {
  vaultModalMode.value = mode
  vaultPin.value = ''
  vaultPinConfirm.value = ''
  vaultPinError.value = ''
}

function closeVaultModal() {
  vaultModalMode.value = ''
  vaultPin.value = ''
  vaultPinConfirm.value = ''
  vaultPinError.value = ''
  pendingImportantFile.value = null
}

async function submitVaultPin() {
  const pin = vaultPin.value.trim()
  if (!/^\d{6}$/.test(pin)) {
    vaultPinError.value = 'Enter a 6 digit PIN.'
    return
  }
  if (vaultModalMode.value === 'setup' && pin !== vaultPinConfirm.value.trim()) {
    vaultPinError.value = 'PIN confirmation does not match.'
    return
  }
  try {
    const response = vaultModalMode.value === 'setup'
      ? await importantDocApi.setup(pin)
      : await importantDocApi.unlock(pin)
    importantUnlockToken.value = response.data.data.unlock_token
    vaultModalMode.value = ''
    await refreshImportantStatus()
    if (pendingImportantFile.value) {
      const file = pendingImportantFile.value
      pendingImportantFile.value = null
      await addImportantDoc(file)
      return
    }
    if (activeFileScope.value === 'important') await loadImportantDocs()
  } catch (err) {
    vaultPinError.value = err.response?.data?.error?.message || 'Unable to unlock Important docs.'
  }
}

async function requestAddImportantDoc(file) {
  pendingImportantFile.value = file
  await refreshImportantStatus()
  if (!importantStatus.value.pin_set || !importantUnlockToken.value) {
    openVaultModal(importantStatus.value.pin_set ? 'unlock' : 'setup')
    return
  }
  await addImportantDoc(file)
}

async function addImportantDoc(file) {
  try {
    await importantDocApi.createFromFile(file.id, {
      title: file.display_name,
      document_type: 'other',
      note: `Original file: ${file.original_filename || file.display_name}`
    }, importantUnlockToken.value)
    activeFileScope.value = 'important'
    activeFile.value = null
    await loadFiles()
    await loadImportantDocs()
  } catch (err) {
    if (err.response?.data?.error?.code === 'document_exists') {
      await dialog.confirm({
        title: 'Already in Important docs',
        message: 'This file is already protected there.',
        confirmText: 'OK'
      })
      return
    }
    if (err.response?.status === 401) {
      importantUnlockToken.value = ''
      pendingImportantFile.value = file
      openVaultModal('unlock')
      return
    }
    await dialog.confirm({
      title: 'Unable to add file',
      message: err.response?.data?.error?.message || 'Please try again.',
      confirmText: 'OK'
    })
  }
}

async function downloadImportantDoc(importantDoc) {
  try {
    const response = await importantDocApi.download(importantDoc.id, importantUnlockToken.value)
    const url = URL.createObjectURL(response.data)
    const link = window.document.createElement('a')
    link.href = url
    link.download = importantDoc.title
    link.click()
    URL.revokeObjectURL(url)
  } catch (err) {
    importantUnlockToken.value = ''
    openVaultModal('unlock')
  }
}

function openImportantActions(importantDoc) {
  importantActionDoc.value = importantDoc
}

function closeImportantActions() {
  importantActionDoc.value = null
}

async function removeImportantDoc(importantDoc) {
  const confirmed = await dialog.confirm({
    title: 'Remove from Important docs',
    message: `${importantDoc.title} will return to normal Files.`,
    confirmText: 'Remove'
  })
  if (!confirmed) return
  try {
    await importantDocApi.remove(importantDoc.id, importantUnlockToken.value)
    await loadImportantDocs()
    await loadFiles()
  } catch (err) {
    importantUnlockToken.value = ''
    openVaultModal('unlock')
  }
}

async function runImportantAction(action) {
  const importantDoc = importantActionDoc.value
  if (!importantDoc) return
  closeImportantActions()
  if (action === 'download') await downloadImportantDoc(importantDoc)
  if (action === 'remove') await removeImportantDoc(importantDoc)
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
  if (action === 'important') await requestAddImportantDoc(file)
  if (action === 'delete') await deleteFile(file)
}

async function restoreFile(file) {
  await fileApi.restore(file.id)
  await loadFiles()
}

async function purgeFile(file) {
  const confirmed = await dialog.confirm({
    title: 'Permanently delete',
    message: `${file.display_name} will be removed from encrypted storage.`,
    confirmText: 'Delete forever',
    danger: true
  })
  if (!confirmed) return
  await fileApi.purge(file.id)
  await loadFiles()
}

async function moveFile(file) {
  openMoveModal([file])
}

async function downloadFile(file) {
  const response = await fileApi.download(file.id)
  const url = URL.createObjectURL(response.data)
  const link = document.createElement('a')
  link.href = url
  link.download = file.original_filename || file.display_name
  link.click()
  URL.revokeObjectURL(url)
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
    moveError.value = 'These files are already in that folder.'
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

async function createFolderAndMove() {
  const name = moveNewFolderName.value.trim()
  if (!name) {
    moveError.value = 'Enter a folder name first.'
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
    tagError.value = 'Select one or more files before applying a tag.'
    return
  }
  if (!selectedTagId.value) {
    tagError.value = 'Choose a tag first.'
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
    tagError.value = 'Enter a tag name first.'
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
  folderStack.value.push(folder)
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
    <button class="xb-album-pill" :class="{ 'is-active': activeFileScope === 'important' }" type="button" @click="openImportantDocs">
      <ShieldCheck :size="16" />
      {{ t('pages.files.importantDocs') }}
    </button>
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
        <button class="xb-icon-button" type="button" title="Restore" @click="restoreFile(file)">
          <RotateCcw :size="17" />
        </button>
        <button class="xb-icon-button xb-danger-button" type="button" title="Purge" @click="purgeFile(file)">
          <Trash2 :size="17" />
        </button>
      </div>
    </article>
  </section>

  <div class="xb-workspace-grid">
    <section>
      <template v-if="activeFileScope === 'all'">
      <section class="xb-folder-strip-mobile">
        <button class="xb-album-pill" :class="{ 'is-active': currentFolderId === null }" type="button" @click="openRootFolder">
          <Folder :size="16" />
          {{ t('pages.files.allFiles') }}
        </button>
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
              <span aria-hidden="true">v</span>
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
          <span>{{ formatDate(file.updated_at) }}</span>
          <div class="xb-row-actions">
            <button class="xb-icon-button" type="button" title="Download" @click="downloadFile(file)">
              <Download :size="17" />
            </button>
            <button class="xb-icon-button" type="button" title="Favorite" @click="toggleFavorite(file)">
              <Star :size="17" :fill="file.is_favorite ? 'currentColor' : 'none'" />
            </button>
            <button class="xb-icon-button" type="button" title="Details" @click="openFileDetails(file)">
              <Info :size="17" />
            </button>
            <button class="xb-icon-button" type="button" title="Move" @click="moveFile(file)">
              <MoveRight :size="17" />
            </button>
            <button class="xb-text-button" type="button" @click="renameFile(file)">Rename</button>
            <button class="xb-icon-button" type="button" title="Tag" @click="attachTag(file)">
              <Tag :size="17" />
            </button>
            <button class="xb-icon-button" type="button" title="Add to Important docs" @click="requestAddImportantDoc(file)">
              <ShieldCheck :size="17" />
            </button>
            <button class="xb-icon-button xb-danger-button" type="button" title="Delete" @click="deleteFile(file)">
              <Trash2 :size="17" />
            </button>
            <button class="xb-icon-button xb-file-more-button" type="button" title="More actions" @click="openFileActions(file)">
              <MoreHorizontal :size="18" />
            </button>
          </div>
        </article>
      </div>
      </template>

      <section v-else class="xb-important-docs-panel">
        <div v-if="!importantStatus.pin_set" class="xb-vault-lock-panel">
          <ShieldCheck :size="34" />
          <h3>Set a 6 digit Vault PIN</h3>
          <p>Important docs stays inside Files, but opening or adding items requires this separate PIN.</p>
          <button class="xb-primary-button" type="button" @click="openVaultModal('setup')">Set PIN</button>
        </div>
        <div v-else-if="!importantUnlockToken" class="xb-vault-lock-panel">
          <ShieldCheck :size="34" />
          <h3>Important docs is locked</h3>
          <p>Unlock with your 6 digit Vault PIN to view protected documents.</p>
          <button class="xb-primary-button" type="button" @click="openVaultModal('unlock')">Unlock</button>
        </div>
        <EmptyState v-else-if="!importantDocsLoading && importantDocs.length === 0" title="No important docs yet" description="Use a file's more menu to add IDs, contracts, licenses or other important documents." />
        <div v-else class="xb-file-list">
          <article v-for="document in importantDocs" :key="document.id" class="xb-file-row xb-important-row">
            <ShieldCheck :size="20" />
            <div class="xb-file-main">
              <strong>{{ document.title }}</strong>
              <span>{{ document.document_type }} &middot; {{ document.security_level }}</span>
              <div class="xb-tag-list">
                <span>PIN protected</span>
                <span v-if="document.expires_at">Expires {{ document.expires_at }}</span>
              </div>
            </div>
            <span>{{ formatDate(document.updated_at) }}</span>
            <div class="xb-row-actions">
              <button class="xb-icon-button" type="button" title="Download" @click="downloadImportantDoc(document)">
                <Download :size="17" />
              </button>
              <button class="xb-icon-button xb-danger-button" type="button" title="Remove from Important docs" @click="removeImportantDoc(document)">
                <Trash2 :size="17" />
              </button>
              <button class="xb-icon-button xb-file-more-button" type="button" title="More actions" @click="openImportantActions(document)">
                <MoreHorizontal :size="18" />
              </button>
            </div>
          </article>
        </div>
      </section>
    </section>

    <aside class="xb-detail-drawer" :class="{ 'is-open': activeFile }">
      <template v-if="activeFile">
        <button class="xb-text-button" type="button" @click="activeFile = null">Close</button>
        <h3>{{ activeFile.display_name }}</h3>
        <dl>
          <div><dt>Original</dt><dd>{{ activeFile.original_filename }}</dd></div>
          <div><dt>Location</dt><dd>{{ folderNameById(activeFile.folder_id) }}</dd></div>
          <div><dt>Type</dt><dd>{{ activeFile.mime_type || 'application/octet-stream' }}</dd></div>
          <div><dt>Size</dt><dd>{{ formatSize(activeFile.file_size) }}</dd></div>
          <div><dt>Hash</dt><dd>{{ activeFile.sha256_hash }}</dd></div>
          <div><dt>Created</dt><dd>{{ formatDate(activeFile.created_at) }}</dd></div>
          <div><dt>Updated</dt><dd>{{ formatDate(activeFile.updated_at) }}</dd></div>
        </dl>
        <div class="xb-tag-list">
          <span v-for="tag in tagsFor(activeFile.id)" :key="tag.id" :style="{ borderColor: tag.color, color: tag.color }">{{ tag.name }}</span>
        </div>
        <button class="xb-secondary-button" type="button" @click="attachTag(activeFile)">
          <Tag :size="17" />
          Add tag
        </button>
        <button class="xb-secondary-button" type="button" @click="moveFile(activeFile)">
          <MoveRight :size="17" />
          Move
        </button>
        <button class="xb-secondary-button" type="button" @click="saveFileAsReceipt(activeFile)">
          <ReceiptText :size="17" />
          Save as receipt
        </button>
        <section class="xb-intelligence-panel">
          <div class="xb-intelligence-head">
            <div>
              <strong>Intelligence</strong>
              <span v-if="intelligenceLoading">Loading...</span>
              <span v-else>{{ latestIntelligenceTask?.status || 'not queued' }}</span>
            </div>
            <div class="xb-row-actions">
              <button class="xb-text-button" type="button" @click="openIntelligenceEditor">
                {{ activeFileIntelligence?.profile ? 'Edit' : 'Create profile' }}
              </button>
              <button class="xb-text-button" type="button" @click="retryFileIntelligence">Retry</button>
            </div>
          </div>
          <template v-if="activeFileIntelligence?.profile">
            <dl>
              <div><dt>Type</dt><dd>{{ activeFileIntelligence.profile.document_type }}</dd></div>
              <div><dt>Title</dt><dd>{{ activeFileIntelligence.profile.title || 'Untitled' }}</dd></div>
              <div v-if="activeFileIntelligence.profile.summary"><dt>Summary</dt><dd>{{ activeFileIntelligence.profile.summary }}</dd></div>
              <div v-if="activeFileIntelligence.profile.issuer"><dt>Issuer</dt><dd>{{ activeFileIntelligence.profile.issuer }}</dd></div>
              <div v-if="activeFileIntelligence.profile.counterparty"><dt>Counterparty</dt><dd>{{ activeFileIntelligence.profile.counterparty }}</dd></div>
              <div v-if="activeFileIntelligence.profile.amount"><dt>Amount</dt><dd>{{ activeFileIntelligence.profile.currency }} {{ activeFileIntelligence.profile.amount }}</dd></div>
              <div v-if="activeFileIntelligence.profile.serial_number"><dt>Serial</dt><dd>{{ activeFileIntelligence.profile.serial_number }}</dd></div>
            </dl>
            <div v-if="activeFileIntelligence.profile.labels?.length" class="xb-tag-list">
              <span v-for="label in activeFileIntelligence.profile.labels" :key="label">{{ label }}</span>
            </div>
            <div v-if="intelligenceFields.length" class="xb-intelligence-fields">
              <span v-for="field in intelligenceFields" :key="field.id">
                <strong>{{ field.field_label || field.field_key }}</strong>
                {{ field.field_value }}
              </span>
            </div>
            <p class="xb-inline-help">
              {{ activeFileIntelligence.profile.confirmed_at ? 'Confirmed by you.' : 'Review and confirm fields before relying on them.' }}
            </p>
          </template>
          <p v-else-if="latestIntelligenceTask?.error_message" class="xb-form-error">{{ latestIntelligenceTask.error_message }}</p>
          <p v-else class="xb-muted">Text extraction runs automatically for supported images, PDFs, and text files.</p>
          <details v-if="activeFileIntelligence?.chunks?.length" class="xb-intelligence-text">
            <summary>Extracted text</summary>
            <p v-for="chunk in activeFileIntelligence.chunks.slice(0, 2)" :key="chunk.id">{{ chunk.text }}</p>
          </details>
        </section>
      </template>
      <template v-else>
        <h3>Details</h3>
        <p>Select a file to view details, manage tags, download it, or move it.</p>
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
          <button class="xb-icon-button" type="button" title="Close" @click="closeFileActions">×</button>
        </header>
        <div class="xb-mobile-action-grid">
          <button type="button" @click="runFileAction('download')">
            <Download :size="18" />
            Download
          </button>
          <button type="button" @click="runFileAction('favorite')">
            <Star :size="18" :fill="actionFile.is_favorite ? 'currentColor' : 'none'" />
            {{ actionFile.is_favorite ? 'Unfavorite' : 'Favorite' }}
          </button>
          <button type="button" @click="runFileAction('details')">
            <Info :size="18" />
            Details
          </button>
          <button type="button" @click="runFileAction('move')">
            <MoveRight :size="18" />
            Move
          </button>
          <button type="button" @click="runFileAction('rename')">
            <Pencil :size="18" />
            Rename
          </button>
          <button type="button" @click="runFileAction('tag')">
            <Tag :size="18" />
            Tag
          </button>
          <button type="button" @click="runFileAction('important')">
            <ShieldCheck :size="18" />
            Important docs
          </button>
          <button class="is-danger" type="button" @click="runFileAction('delete')">
            <Trash2 :size="18" />
            Delete
          </button>
        </div>
      </div>
    </section>
  </Teleport>

  <Teleport to="body">
    <section v-if="importantActionDoc" class="xb-mobile-action-backdrop" @click.self="closeImportantActions">
      <div class="xb-mobile-action-sheet">
        <header>
          <div>
            <strong>{{ importantActionDoc.title }}</strong>
            <span>{{ importantActionDoc.document_type }} &middot; PIN protected</span>
          </div>
          <button class="xb-icon-button" type="button" title="Close" @click="closeImportantActions">x</button>
        </header>
        <div class="xb-mobile-action-grid">
          <button type="button" @click="runImportantAction('download')">
            <Download :size="18" />
            Download
          </button>
          <button class="is-danger" type="button" @click="runImportantAction('remove')">
            <Trash2 :size="18" />
            Remove
          </button>
        </div>
      </div>
    </section>
  </Teleport>

  <Teleport to="body">
    <section v-if="vaultModalMode" class="xb-modal-backdrop" @click.self="closeVaultModal">
      <form class="xb-modal xb-vault-modal" @submit.prevent="submitVaultPin">
        <ShieldCheck :size="24" />
        <h3>{{ vaultModalMode === 'setup' ? 'Set Vault PIN' : 'Unlock Important docs' }}</h3>
        <p>{{ vaultModalMode === 'setup' ? 'Create a separate 6 digit PIN for Important docs.' : 'Enter your 6 digit Vault PIN. The unlock is temporary.' }}</p>
        <label>
          Vault PIN
          <input v-model="vaultPin" type="password" inputmode="numeric" pattern="[0-9]*" maxlength="6" placeholder="6 digits" autocomplete="off" />
        </label>
        <label v-if="vaultModalMode === 'setup'">
          Confirm PIN
          <input v-model="vaultPinConfirm" type="password" inputmode="numeric" pattern="[0-9]*" maxlength="6" placeholder="Repeat PIN" autocomplete="off" />
        </label>
        <p v-if="vaultPinError" class="xb-form-error">{{ vaultPinError }}</p>
        <div class="xb-row-actions">
          <button class="xb-primary-button" type="submit">{{ vaultModalMode === 'setup' ? 'Set PIN' : 'Unlock' }}</button>
          <button class="xb-secondary-button" type="button" @click="closeVaultModal">Cancel</button>
        </div>
      </form>
    </section>
  </Teleport>

  <Teleport to="body">
    <section v-if="intelligenceEditorOpen" class="xb-modal-backdrop" @click.self="closeIntelligenceEditor">
      <form class="xb-modal xb-intelligence-editor" @submit.prevent="saveIntelligenceProfile">
        <Info :size="24" />
        <h3>Review intelligence</h3>
        <p>Correct the extracted fields, then confirm this profile for search and future document views.</p>
        <label>
          Type
          <select v-model="intelligenceForm.document_type">
            <option value="receipt">Receipt</option>
            <option value="invoice">Invoice</option>
            <option value="contract">Contract</option>
            <option value="warranty">Warranty</option>
            <option value="manual">Manual</option>
            <option value="statement">Statement</option>
            <option value="general">General</option>
            <option value="unknown">Unknown</option>
          </select>
        </label>
        <label>
          Title
          <input v-model="intelligenceForm.title" maxlength="255" />
        </label>
        <label>
          Summary
          <textarea v-model="intelligenceForm.summary" rows="4" maxlength="4000"></textarea>
        </label>
        <div class="xb-two-column-form">
          <label>
            Issuer
            <input v-model="intelligenceForm.issuer" maxlength="255" />
          </label>
          <label>
            Counterparty
            <input v-model="intelligenceForm.counterparty" maxlength="255" />
          </label>
          <label>
            Date
            <input v-model="intelligenceForm.primary_date" maxlength="32" />
          </label>
          <label>
            Warranty until
            <input v-model="intelligenceForm.warranty_until" maxlength="32" />
          </label>
          <label>
            Amount
            <input v-model="intelligenceForm.amount" maxlength="64" />
          </label>
          <label>
            Currency
            <input v-model="intelligenceForm.currency" maxlength="16" />
          </label>
          <label>
            Serial number
            <input v-model="intelligenceForm.serial_number" maxlength="120" />
          </label>
          <label>
            Labels
            <input v-model="intelligenceForm.labelsText" placeholder="invoice, warranty" />
          </label>
        </div>
        <label>
          Keywords
          <input v-model="intelligenceForm.keywordsText" placeholder="comma separated" />
        </label>
        <div class="xb-row-actions">
          <button class="xb-primary-button" type="submit">Confirm profile</button>
          <button class="xb-secondary-button" type="button" @click="closeIntelligenceEditor">Cancel</button>
        </div>
      </form>
    </section>
  </Teleport>

  <Teleport to="body">
    <section v-if="tagModalOpen" class="xb-modal-backdrop" @click.self="closeTagModal">
      <form class="xb-modal xb-tag-modal" @submit.prevent="saveTagDraft">
        <Tag :size="24" />
        <h3>{{ tagTargetFiles.length ? 'Apply tag' : 'Tags' }}</h3>
        <p>
          {{ tagTargetFiles.length ? 'Choose an existing tag, or create a new one for the selected files.' : 'Create reusable labels here. Select files first when you want to apply a tag.' }}
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
            <button type="button" title="Edit tag" @click="editTag(tag)">
              <Pencil :size="14" />
            </button>
          </div>
        </div>
        <p v-else class="xb-inline-help">No tags yet. Create one below.</p>

        <button
          v-if="tagTargetFiles.length && tags.length"
          class="xb-secondary-button"
          type="button"
          :disabled="!selectedTagId"
          @click="applyExistingTag"
        >
          Apply selected tag
        </button>

        <div class="xb-tag-divider">
          <span>{{ editingTagId ? 'Edit selected tag' : (tags.length ? 'Or create a new tag' : 'Create your first tag') }}</span>
        </div>
        <p v-if="tagError" class="xb-form-error">{{ tagError }}</p>

        <label>
          Tag name
          <input v-model="tagDraft.name" placeholder="Important" autocomplete="off" />
        </label>

        <div class="xb-color-field">
          <span>Color</span>
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
            <input v-model="tagDraft.color" type="color" title="Custom color" />
          </div>
        </div>

        <div class="xb-row-actions">
          <button class="xb-primary-button" type="submit">
            {{ editingTagId ? 'Save tag' : (tagTargetFiles.length ? 'Create and apply' : 'Create tag') }}
          </button>
          <button v-if="editingTagId" class="xb-secondary-button" type="button" @click="resetTagEdit">Cancel edit</button>
          <button class="xb-secondary-button" type="button" @click="closeTagModal">Cancel</button>
        </div>
      </form>
    </section>
  </Teleport>

  <Teleport to="body">
    <section v-if="moveModalOpen" class="xb-modal-backdrop" @click.self="closeMoveModal">
      <form class="xb-modal xb-move-modal" @submit.prevent="applyMoveFolder">
        <MoveRight :size="24" />
        <h3>Move {{ moveTargetFiles.length > 1 ? 'files' : 'file' }}</h3>
        <p>Choose a folder, move to All files, or create a new folder.</p>

        <label>
          Search folders
          <input v-model="moveFolderQuery" placeholder="Type a folder name" autocomplete="off" />
        </label>

        <div class="xb-folder-select">
          <Folder :size="17" />
          <div class="xb-folder-combobox">
            <button type="button" @click="moveFolderMenuOpen = !moveFolderMenuOpen">
              <span>{{ selectedMoveFolderLabel }}</span>
              <span aria-hidden="true">v</span>
            </button>
            <div v-if="moveFolderMenuOpen" class="xb-folder-menu">
              <button type="button" :class="{ 'is-active': moveFolderId === null }" @click="chooseMoveFolder(null)">
                All files
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
          <p v-if="!filteredMoveFolders.length" class="xb-inline-help">No matching folders.</p>
        </div>

        <div class="xb-tag-divider">
          <span>Create and move</span>
        </div>

        <label>
          New folder name
          <input v-model="moveNewFolderName" placeholder="Project files" autocomplete="off" />
        </label>
        <p v-if="moveError" class="xb-form-error">{{ moveError }}</p>

        <div class="xb-row-actions">
          <button class="xb-primary-button" type="submit">Move here</button>
          <button class="xb-secondary-button" type="button" @click="createFolderAndMove">Create folder and move</button>
          <button class="xb-secondary-button" type="button" @click="closeMoveModal">Cancel</button>
        </div>
      </form>
    </section>
  </Teleport>
  </div>
</template>
