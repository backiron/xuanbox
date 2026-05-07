<script setup>
import { onMounted, ref } from 'vue'
import { FolderPlus, RotateCcw, Star, Trash2, Upload } from 'lucide-vue-next'
import PageHeader from '../../components/common/PageHeader.vue'
import EmptyState from '../../components/common/EmptyState.vue'
import { fileApi, folderApi } from '../../api/fileApi'

const files = ref([])
const folders = ref([])
const trash = ref([])
const loading = ref(false)
const currentFolderId = ref(null)
const showTrash = ref(false)

async function loadFiles() {
  loading.value = true
  try {
    const response = await fileApi.list(currentFolderId.value ? { folder_id: currentFolderId.value } : {})
    files.value = response.data.data
    const folderResponse = await folderApi.list(currentFolderId.value ? { parent_id: currentFolderId.value } : {})
    folders.value = folderResponse.data.data
    const trashResponse = await fileApi.trash()
    trash.value = trashResponse.data.data
  } finally {
    loading.value = false
  }
}

async function onFileChange(event) {
  const file = event.target.files?.[0]
  if (!file) return
  const formData = new FormData()
  formData.append('file', file)
  if (currentFolderId.value) formData.append('folder_id', currentFolderId.value)
  await fileApi.upload(formData)
  event.target.value = ''
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

async function toggleFavorite(file) {
  await fileApi.update(file.id, { is_favorite: !file.is_favorite })
  await loadFiles()
}

async function deleteFile(file) {
  await fileApi.remove(file.id)
  await loadFiles()
}

async function restoreFile(file) {
  await fileApi.restore(file.id)
  await loadFiles()
}

onMounted(loadFiles)
</script>

<template>
  <PageHeader title="Files" subtitle="Encrypted file storage with owner-only access.">
    <button class="xb-secondary-button" type="button" @click="showTrash = !showTrash">
      <Trash2 :size="18" />
      Trash
    </button>
    <button class="xb-secondary-button" type="button" @click="createFolder">
      <FolderPlus :size="18" />
      Folder
    </button>
    <label class="xb-upload-button">
      <Upload :size="18" />
      Upload
      <input type="file" @change="onFileChange" />
    </label>
  </PageHeader>
  <section v-if="showTrash" class="xb-panel">
    <h3>Trash</h3>
    <p v-if="trash.length === 0">Trash is empty.</p>
    <article v-for="file in trash" :key="file.id" class="xb-file-row">
      <div>
        <strong>{{ file.display_name }}</strong>
        <span>Deleted file</span>
      </div>
      <button class="xb-icon-button" type="button" @click="restoreFile(file)">
        <RotateCcw :size="17" />
      </button>
    </article>
  </section>
  <div v-if="folders.length" class="xb-folder-grid">
    <button v-for="folder in folders" :key="folder.id" class="xb-folder-card" type="button" @click="currentFolderId = folder.id; loadFiles()">
      <FolderPlus :size="20" />
      {{ folder.name }}
    </button>
  </div>
  <EmptyState v-if="!loading && files.length === 0 && folders.length === 0" title="No files yet" description="Upload a small local test file to verify the encrypted storage chain." />
  <div v-else class="xb-file-list">
    <article v-for="file in files" :key="file.id" class="xb-file-row">
      <div>
        <strong>{{ file.display_name }}</strong>
        <span>{{ file.mime_type || 'application/octet-stream' }}</span>
      </div>
      <span>{{ Math.ceil(file.file_size / 1024) }} KB</span>
      <div class="xb-row-actions">
        <button class="xb-icon-button" type="button" @click="toggleFavorite(file)">
          <Star :size="17" :fill="file.is_favorite ? 'currentColor' : 'none'" />
        </button>
        <button class="xb-text-button" type="button" @click="renameFile(file)">Rename</button>
        <button class="xb-icon-button xb-danger-button" type="button" @click="deleteFile(file)">
          <Trash2 :size="17" />
        </button>
      </div>
    </article>
  </div>
</template>
