<script setup>
import { computed, onMounted, ref } from 'vue'
import {
  ArrowLeft,
  Download,
  Folder,
  FolderPlus,
  Info,
  MoveRight,
  RotateCcw,
  Star,
  Tag,
  Trash2,
  Upload
} from 'lucide-vue-next'
import PageHeader from '../../components/common/PageHeader.vue'
import EmptyState from '../../components/common/EmptyState.vue'
import { fileApi, folderApi, tagApi } from '../../api/fileApi'

const files = ref([])
const folders = ref([])
const allFolders = ref([])
const trash = ref([])
const tags = ref([])
const tagLinks = ref([])
const loading = ref(false)
const currentFolderId = ref(null)
const folderStack = ref([])
const showTrash = ref(false)
const selectedIds = ref(new Set())
const activeFile = ref(null)
const uploadProgress = ref(0)

const currentFolderName = computed(() => folderStack.value.at(-1)?.name || 'All files')
const selectedFiles = computed(() => files.value.filter((file) => selectedIds.value.has(file.id)))

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
    files.value = fileResponse.data.data
    folders.value = folderResponse.data.data
    trash.value = trashResponse.data.data
    tags.value = tagResponse.data.data
    tagLinks.value = linkResponse.data.data
    allFolders.value = rootFolderResponse.data.data
    selectedIds.value = new Set([...selectedIds.value].filter((id) => files.value.some((file) => file.id === id)))
    if (activeFile.value) activeFile.value = files.value.find((file) => file.id === activeFile.value.id) || activeFile.value
  } finally {
    loading.value = false
  }
}

async function onFileChange(event) {
  const pickedFiles = Array.from(event.target.files || [])
  if (!pickedFiles.length) return
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
  event.target.value = ''
  uploadProgress.value = 0
  await loadFiles()
}

async function createFolder() {
  const name = window.prompt('Folder name')
  if (!name) return
  await folderApi.create({ name, parent_id: currentFolderId.value })
  await loadFiles()
}

async function renameFile(file) {
  const displayName = window.prompt('New name', file.display_name)
  if (!displayName) return
  await fileApi.update(file.id, { display_name: displayName })
  await loadFiles()
}

async function renameFolder(folder) {
  const name = window.prompt('New folder name', folder.name)
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

async function restoreFile(file) {
  await fileApi.restore(file.id)
  await loadFiles()
}

async function purgeFile(file) {
  if (!window.confirm(`Permanently delete ${file.display_name}?`)) return
  await fileApi.purge(file.id)
  await loadFiles()
}

async function moveFile(file) {
  const target = window.prompt('Move to folder id. Leave blank for root.', currentFolderId.value || '')
  if (target === null) return
  await fileApi.update(file.id, { folder_id: target.trim() || null })
  await loadFiles()
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
  const target = window.prompt('Move selected files to folder id. Leave blank for root.', currentFolderId.value || '')
  if (target === null) return
  await Promise.all(selectedFiles.value.map((file) => fileApi.update(file.id, { folder_id: target.trim() || null })))
  selectedIds.value = new Set()
  await loadFiles()
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

async function createTag() {
  const name = window.prompt('Tag name')
  if (!name) return
  const color = window.prompt('Tag color', '#1E3A5F') || '#1E3A5F'
  await tagApi.create({ name, color })
  await loadFiles()
}

async function attachTag(file) {
  if (!tags.value.length) {
    await createTag()
    if (!tags.value.length) return
  }
  const tagName = window.prompt('Attach tag by name', tags.value[0]?.name || '')
  if (!tagName) return
  let tag = tags.value.find((item) => item.name.toLowerCase() === tagName.toLowerCase())
  if (!tag) {
    const color = window.prompt('New tag color', '#1E3A5F') || '#1E3A5F'
    const response = await tagApi.create({ name: tagName, color })
    tag = response.data.data
  }
  await tagApi.attach(tag.id, { target_type: 'file', target_id: file.id })
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

function goBack() {
  folderStack.value.pop()
  currentFolderId.value = folderStack.value.at(-1)?.id || null
  activeFile.value = null
  loadFiles()
}

onMounted(loadFiles)
</script>

<template>
  <PageHeader :title="currentFolderName" subtitle="Encrypted file storage with folders, tags, trash and protected downloads.">
    <button v-if="currentFolderId" class="xb-secondary-button" type="button" @click="goBack">
      <ArrowLeft :size="18" />
      Back
    </button>
    <button class="xb-secondary-button" type="button" @click="showTrash = !showTrash">
      <Trash2 :size="18" />
      Trash
    </button>
    <button class="xb-secondary-button" type="button" @click="createTag">
      <Tag :size="18" />
      Tag
    </button>
    <button class="xb-secondary-button" type="button" @click="createFolder">
      <FolderPlus :size="18" />
      Folder
    </button>
    <label class="xb-upload-button">
      <Upload :size="18" />
      Upload
      <input type="file" multiple @change="onFileChange" />
    </label>
  </PageHeader>

  <div v-if="uploadProgress" class="xb-progress">
    <span :style="{ width: `${uploadProgress}%` }"></span>
  </div>

  <section v-if="selectedFiles.length" class="xb-action-bar">
    <strong>{{ selectedFiles.length }} selected</strong>
    <button class="xb-text-button" type="button" @click="bulkFavorite">Favorite</button>
    <button class="xb-text-button" type="button" @click="bulkMove">Move</button>
    <button class="xb-text-button xb-danger-button" type="button" @click="bulkDelete">Delete</button>
  </section>

  <section v-if="showTrash" class="xb-panel xb-trash-panel">
    <h3>Trash</h3>
    <p v-if="trash.length === 0">Trash is empty.</p>
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
      <div v-if="folders.length" class="xb-folder-grid">
        <article v-for="folder in folders" :key="folder.id" class="xb-folder-card">
          <button type="button" @click="openFolder(folder)">
            <Folder :size="20" />
            {{ folder.name }}
          </button>
          <button class="xb-text-button" type="button" @click="renameFolder(folder)">Rename</button>
        </article>
      </div>

      <EmptyState v-if="!loading && files.length === 0 && folders.length === 0" title="No files here" description="Upload a small local test file to verify the encrypted storage chain." />

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
            <button class="xb-icon-button" type="button" title="Details" @click="activeFile = file">
              <Info :size="17" />
            </button>
            <button class="xb-icon-button" type="button" title="Move" @click="moveFile(file)">
              <MoveRight :size="17" />
            </button>
            <button class="xb-text-button" type="button" @click="renameFile(file)">Rename</button>
            <button class="xb-icon-button" type="button" title="Tag" @click="attachTag(file)">
              <Tag :size="17" />
            </button>
            <button class="xb-icon-button xb-danger-button" type="button" title="Delete" @click="deleteFile(file)">
              <Trash2 :size="17" />
            </button>
          </div>
        </article>
      </div>
    </section>

    <aside class="xb-detail-drawer" :class="{ 'is-open': activeFile }">
      <template v-if="activeFile">
        <button class="xb-text-button" type="button" @click="activeFile = null">Close</button>
        <h3>{{ activeFile.display_name }}</h3>
        <dl>
          <div><dt>Original</dt><dd>{{ activeFile.original_filename }}</dd></div>
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
      </template>
      <template v-else>
        <h3>Details</h3>
        <p>Select a file to inspect metadata, tags and actions.</p>
      </template>
    </aside>
  </div>

  <section class="xb-panel xb-folder-reference">
    <h3>Folder ids for moving</h3>
    <p v-if="allFolders.length === 0">No folders yet.</p>
    <div v-else class="xb-id-list">
      <span v-for="folder in allFolders" :key="folder.id">{{ folder.name }} · {{ folder.id }}</span>
    </div>
  </section>
</template>
