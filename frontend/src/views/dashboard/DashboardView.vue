<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  AlertTriangle,
  CheckCircle2,
  CloudUpload,
  FileText,
  FolderOpen,
  HardDrive,
  Image,
  Inbox,
  ReceiptText,
  Send,
  Share2,
  ShieldCheck,
  Upload
} from 'lucide-vue-next'

import { dashboardApi } from '../../api/documentApi'
import { dropApi } from '../../api/dropApi'
import { fileApi } from '../../api/fileApi'
import { inboxApi } from '../../api/inboxApi'
import { photoApi } from '../../api/photoApi'

const router = useRouter()
const summary = ref(null)
const recentFiles = ref([])
const recentPhotos = ref([])
const dropSessions = ref([])
const pendingInbox = ref([])
const loading = ref(false)
const uploadProgress = ref(0)
const draggingFiles = ref(false)
const uploadMessage = ref('')
const uploadError = ref('')

const storageLimitBytes = 2 * 1024 * 1024 * 1024 * 1024
const photoUrls = new Set()

const metrics = computed(() => summary.value?.metrics || {})
const storageUsed = computed(() => metrics.value.storage_bytes || 0)
const storagePercent = computed(() => Math.min(100, Math.round((storageUsed.value / storageLimitBytes) * 100)))
const activeDrop = computed(() => dropSessions.value[0] || null)

const statCards = computed(() => [
  { label: 'Inbox', value: formatNumber(pendingInbox.value.length), hint: 'Awaiting review', icon: Inbox, tone: 'cyan', to: '/inbox' },
  { label: 'Photos', value: formatNumber(metrics.value.photos_count), hint: 'Timeline items', icon: Image, tone: 'purple', to: '/photos' },
  { label: 'Files', value: formatNumber(metrics.value.files_count), hint: 'Encrypted assets', icon: FileText, tone: 'blue', to: '/files' },
  { label: 'Receipts', value: formatNumber(metrics.value.receipts_count), hint: 'OCR capable', icon: ReceiptText, tone: 'orange', to: '/receipts' },
  { label: 'Shares', value: formatNumber(activeDrop.value ? 1 : 0), hint: 'Drop sessions', icon: Share2, tone: 'blue', to: '/shared' }
])

function formatNumber(value = 0) {
  return new Intl.NumberFormat(undefined).format(value || 0)
}

function formatBytes(value) {
  if (!value) return '0 MB'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let size = value
  let unit = 0
  while (size >= 1024 && unit < units.length - 1) {
    size /= 1024
    unit += 1
  }
  return `${size.toFixed(unit < 2 ? 0 : 1)} ${units[unit]}`
}

function formatDate(value) {
  if (!value) return 'No date'
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(new Date(value))
}

function formatFileSize(bytes) {
  if (!bytes) return '0 KB'
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.ceil(bytes / 1024))} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

function fileIconName(file) {
  if (file.mime_type?.startsWith('image/')) return 'Image'
  if (file.mime_type?.includes('pdf')) return 'PDF'
  return 'File'
}

async function hydratePhotos(rows) {
  const limited = rows.slice(0, 6)
  return Promise.all(limited.map(async (photo) => {
    try {
      const response = await photoApi.thumbnailBlob(photo.id)
      const url = URL.createObjectURL(response.data)
      photoUrls.add(url)
      return { ...photo, thumbUrl: url }
    } catch {
      return { ...photo, thumbUrl: '' }
    }
  }))
}

async function loadDashboard() {
  loading.value = true
  try {
    const [summaryResponse, filesResponse, photosResponse, sessionsResponse, inboxResponse] = await Promise.allSettled([
      dashboardApi.summary(),
      fileApi.list(),
      photoApi.list(),
      dropApi.sessions(),
      inboxApi.list()
    ])

    if (summaryResponse.status === 'fulfilled') summary.value = summaryResponse.value.data.data
    if (filesResponse.status === 'fulfilled') {
      recentFiles.value = [...filesResponse.value.data.data]
        .sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at))
        .slice(0, 5)
    }
    if (photosResponse.status === 'fulfilled') recentPhotos.value = await hydratePhotos(photosResponse.value.data.data)
    if (sessionsResponse.status === 'fulfilled') dropSessions.value = sessionsResponse.value.data.data
    if (inboxResponse.status === 'fulfilled') pendingInbox.value = inboxResponse.value.data.data
  } finally {
    loading.value = false
  }
}

async function uploadFiles(files) {
  const pickedFiles = Array.from(files || [])
  if (!pickedFiles.length) return
  uploadProgress.value = 1
  uploadMessage.value = ''
  uploadError.value = ''
  let uploadedCount = 0
  try {
    for (const pickedFile of pickedFiles) {
      const formData = new FormData()
      formData.append('file', pickedFile)
      await inboxApi.upload(formData, {
        onUploadProgress(progressEvent) {
          if (progressEvent.total) uploadProgress.value = Math.round((progressEvent.loaded / progressEvent.total) * 100)
        }
      })
      uploadedCount += 1
    }
  } catch (err) {
    uploadError.value = err.response?.data?.message || 'Upload did not finish. Check Inbox for any uploaded items.'
  } finally {
    uploadProgress.value = 0
  }
  if (uploadedCount > 0) {
    uploadMessage.value = `${uploadedCount} item${uploadedCount > 1 ? 's' : ''} added to Inbox for review.`
    try {
      await router.push({ path: '/inbox', query: { uploaded: String(Date.now()) } })
    } catch {
      window.location.assign('/inbox')
    }
  } else {
    await loadDashboard()
  }
}

async function onFileChange(event) {
  await uploadFiles(event.target.files)
  event.target.value = ''
}

function resetFileInput(event) {
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

onMounted(loadDashboard)
onBeforeUnmount(() => {
  for (const url of photoUrls) URL.revokeObjectURL(url)
  photoUrls.clear()
})
</script>

<template>
  <section
    class="xb-dashboard xb-upload-page"
    :class="{ 'is-dragging': draggingFiles }"
    @dragenter.prevent="onDragEnter"
    @dragover.prevent="draggingFiles = true"
    @dragleave="onDragLeave"
    @drop.prevent="onFileDrop"
  >
    <div class="xb-dashboard-head">
      <div>
        <h2>Overview</h2>
        <p>Private vault status, recent activity, quick upload, and device transfer.</p>
      </div>
      <div class="xb-dashboard-head-actions">
        <router-link to="/files" class="xb-secondary-button">
          <FolderOpen :size="16" />
          Browse vault
        </router-link>
        <label class="xb-upload-button">
          <Upload :size="16" />
          Upload
          <input type="file" multiple @click="resetFileInput" @change="onFileChange" />
        </label>
      </div>
    </div>

    <div v-if="uploadProgress" class="xb-progress xb-dashboard-upload-progress">
      <span :style="{ width: `${uploadProgress}%` }"></span>
    </div>
    <p v-if="uploadMessage" class="xb-muted xb-dashboard-upload-message">{{ uploadMessage }}</p>
    <p v-if="uploadError" class="xb-status-note is-error">{{ uploadError }}</p>

    <section class="xb-upload-drop-hint" :class="{ 'is-visible': draggingFiles }">
      <Upload :size="18" />
      <strong>Drop files to upload</strong>
          <span>Files will wait in Inbox until you choose where they belong.</span>
    </section>

    <section class="xb-dashboard-overview">
      <article class="xb-storage-card">
        <div class="xb-card-kicker">
          <HardDrive :size="18" />
          Storage
        </div>
        <div class="xb-storage-value">
          <strong>{{ formatBytes(storageUsed) }}</strong>
          <span>/ 2.00 TB</span>
        </div>
        <div class="xb-storage-meta">
          <span>Used {{ storagePercent }}%</span>
          <span>{{ loading ? 'Syncing' : 'Encrypted' }}</span>
        </div>
        <div class="xb-storage-bar">
          <span :style="{ width: `${storagePercent}%` }"></span>
        </div>
      </article>

      <router-link v-for="card in statCards" :key="card.label" :to="card.to" class="xb-dashboard-stat" :class="`tone-${card.tone}`">
        <div class="xb-stat-icon">
          <component :is="card.icon" :size="18" />
        </div>
        <span>{{ card.label }}</span>
        <strong>{{ card.value }}</strong>
        <small>{{ card.hint }}</small>
      </router-link>
    </section>

    <section class="xb-dashboard-grid">
      <router-link v-if="pendingInbox.length" to="/inbox" class="xb-dashboard-panel xb-inbox-alert">
        <Inbox :size="28" />
        <div>
          <strong>{{ pendingInbox.length }} upload{{ pendingInbox.length > 1 ? 's' : '' }} waiting in Inbox</strong>
          <span>Open Inbox to save them as Photos, Files, or Receipts.</span>
        </div>
      </router-link>

      <article class="xb-dashboard-panel xb-recent-panel">
        <div class="xb-panel-title">
          <h3>Recent Files</h3>
          <router-link to="/files">View all</router-link>
        </div>
        <div v-if="recentFiles.length" class="xb-dashboard-list">
          <router-link v-for="file in recentFiles" :key="file.id" to="/files" class="xb-dashboard-file">
            <span class="xb-file-badge">{{ fileIconName(file) }}</span>
            <div>
              <strong>{{ file.display_name }}</strong>
              <small>{{ file.mime_type || 'application/octet-stream' }} / {{ formatFileSize(file.file_size) }}</small>
            </div>
            <time>{{ formatDate(file.updated_at) }}</time>
          </router-link>
        </div>
        <p v-else class="xb-muted">{{ loading ? 'Loading files...' : 'No files uploaded yet.' }}</p>
      </article>

      <article class="xb-dashboard-panel">
        <div class="xb-panel-title">
          <h3>Recent Photos</h3>
          <router-link to="/photos">View all</router-link>
        </div>
        <div v-if="recentPhotos.length" class="xb-dashboard-photos">
          <router-link v-for="photo in recentPhotos" :key="photo.id" to="/photos" class="xb-dashboard-photo">
            <img v-if="photo.thumbUrl" :src="photo.thumbUrl" alt="" />
            <Image v-else :size="24" />
          </router-link>
        </div>
        <p v-else class="xb-muted">{{ loading ? 'Loading photos...' : 'No photos in the timeline yet.' }}</p>
      </article>

      <article class="xb-dashboard-panel xb-upload-drop">
        <div class="xb-panel-title">
          <h3>Quick Upload</h3>
          <router-link to="/inbox">Inbox</router-link>
        </div>
        <label class="xb-drop-upload-target">
          <CloudUpload :size="34" />
          <strong>Drop files or photos into XuanBox</strong>
          <span>Uploads go to Inbox first, then you choose Photo, File, or Receipt.</span>
          <input type="file" multiple @click="resetFileInput" @change="onFileChange" />
        </label>
      </article>

      <article class="xb-dashboard-panel xb-xuandrop-card">
        <div class="xb-panel-title">
          <h3>XuanDrop</h3>
          <router-link to="/drop">Open</router-link>
        </div>
        <div class="xb-device-transfer">
          <div class="xb-phone-glyph"></div>
          <Send :size="28" />
          <div>
            <strong>{{ activeDrop?.title || 'Ready for nearby devices' }}</strong>
            <span>{{ activeDrop ? `Expires ${formatDate(activeDrop.expires_at)}` : 'Create a session to receive files from another device.' }}</span>
          </div>
        </div>
      </article>
    </section>

    <section class="xb-dashboard-footer">
      <router-link to="/files" class="xb-footer-action">
        <ShieldCheck :size="20" />
        <div>
          <strong>Important docs</strong>
          <span v-if="summary?.expiring_documents?.length">{{ summary.expiring_documents.length }} item needs attention</span>
          <span v-else>No documents expiring in the next 90 days.</span>
        </div>
        <AlertTriangle v-if="summary?.expiring_documents?.length" :size="18" />
        <CheckCircle2 v-else :size="18" />
      </router-link>
      <router-link to="/shared" class="xb-footer-action">
        <Share2 :size="20" />
        <div>
          <strong>Secure Sharing</strong>
          <span>Create password-protected links with limits and expiry.</span>
        </div>
      </router-link>
      <router-link to="/settings" class="xb-footer-action">
        <ShieldCheck :size="20" />
        <div>
          <strong>Device Security</strong>
          <span>Review trusted devices and account sessions.</span>
        </div>
      </router-link>
    </section>
  </section>
</template>
