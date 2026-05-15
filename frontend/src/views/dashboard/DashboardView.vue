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
import { useI18n } from 'vue-i18n'

import { dashboardApi } from '../../api/documentApi'
import { dropApi } from '../../api/dropApi'
import { fileApi } from '../../api/fileApi'
import { inboxApi } from '../../api/inboxApi'
import { photoApi } from '../../api/photoApi'

const router = useRouter()
const { t } = useI18n()
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

const photoUrls = new Set()

const metrics = computed(() => summary.value?.metrics || {})
const storageUsed = computed(() => metrics.value.storage_bytes || 0)
const storageLimit = computed(() => metrics.value.storage_limit_bytes)
const storageLimitLabel = computed(() => storageLimit.value == null ? t('common.states.unlimited') : formatBytes(storageLimit.value))
const storagePercent = computed(() => {
  if (!storageLimit.value) return 0
  return Math.min(100, Math.round((storageUsed.value / storageLimit.value) * 100))
})
const activeDrop = computed(() => dropSessions.value[0] || null)

const statCards = computed(() => [
  { label: t('routes.inbox'), value: formatNumber(pendingInbox.value.length), hint: t('pages.dashboard.statAwaitingReview'), icon: Inbox, tone: 'cyan', to: '/inbox' },
  { label: t('routes.photos'), value: formatNumber(metrics.value.photos_count), hint: t('pages.dashboard.statTimelineItems'), icon: Image, tone: 'purple', to: '/photos' },
  { label: t('routes.files'), value: formatNumber(metrics.value.files_count), hint: t('pages.dashboard.statEncryptedAssets'), icon: FileText, tone: 'blue', to: '/files' },
  { label: t('routes.receipts'), value: formatNumber(metrics.value.receipts_count), hint: t('pages.dashboard.statOcrCapable'), icon: ReceiptText, tone: 'orange', to: '/receipts' },
  { label: t('pages.dashboard.shares'), value: formatNumber(activeDrop.value ? 1 : 0), hint: t('pages.dashboard.statDropSessions'), icon: Share2, tone: 'blue', to: '/shared' }
])

function pluralSuffix(count) {
  return count === 1 ? '' : 's'
}

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
    uploadError.value = err.response?.data?.message || t('pages.dashboard.uploadFailed')
  } finally {
    uploadProgress.value = 0
  }
  if (uploadedCount > 0) {
    uploadMessage.value = t('pages.dashboard.uploadAdded', { count: uploadedCount, plural: pluralSuffix(uploadedCount) })
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
        <h2>{{ t('pages.dashboard.title') }}</h2>
        <p>{{ t('pages.dashboard.subtitle') }}</p>
      </div>
      <div class="xb-dashboard-head-actions">
        <router-link to="/files" class="xb-secondary-button">
          <FolderOpen :size="16" />
          {{ t('pages.dashboard.browseVault') }}
        </router-link>
        <label
          class="xb-upload-button"
          @dragenter.prevent="onDragEnter"
          @dragover.prevent="draggingFiles = true"
          @drop.prevent="onFileDrop"
        >
          <Upload :size="16" />
          {{ t('pages.dashboard.quickUpload') }}
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
      <strong>{{ t('pages.dashboard.dropFilesHint') }}</strong>
      <span>{{ t('pages.dashboard.dropFilesDescription') }}</span>
    </section>

    <section class="xb-dashboard-overview">
      <article class="xb-storage-card">
        <div class="xb-card-kicker">
          <HardDrive :size="18" />
          {{ t('pages.dashboard.storage') }}
        </div>
        <div class="xb-storage-value">
          <strong>{{ formatBytes(storageUsed) }}</strong>
          <span>/ {{ storageLimitLabel }}</span>
        </div>
        <div class="xb-storage-meta">
          <span>{{ t('pages.dashboard.usedPercent', { count: storagePercent }) }}</span>
          <span>{{ loading ? t('common.states.syncing') : t('common.states.encrypted') }}</span>
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
          <strong>{{ t('pages.dashboard.waitingInInbox', { count: pendingInbox.length, plural: pluralSuffix(pendingInbox.length) }) }}</strong>
          <span>{{ t('pages.dashboard.openInboxHint') }}</span>
        </div>
      </router-link>

      <article class="xb-dashboard-panel xb-recent-panel">
        <div class="xb-panel-title">
          <h3>{{ t('pages.dashboard.files') }}</h3>
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
        <p v-else class="xb-muted">{{ loading ? t('pages.dashboard.loadingFiles') : t('pages.dashboard.noFilesYet') }}</p>
      </article>

      <article class="xb-dashboard-panel">
        <div class="xb-panel-title">
          <h3>{{ t('pages.dashboard.photos') }}</h3>
          <router-link to="/photos">View all</router-link>
        </div>
        <div v-if="recentPhotos.length" class="xb-dashboard-photos">
          <router-link v-for="photo in recentPhotos" :key="photo.id" to="/photos" class="xb-dashboard-photo">
            <img v-if="photo.thumbUrl" :src="photo.thumbUrl" alt="" />
            <Image v-else :size="24" />
          </router-link>
        </div>
        <p v-else class="xb-muted">{{ loading ? t('pages.dashboard.loadingPhotos') : t('pages.dashboard.noPhotosYet') }}</p>
      </article>

      <article class="xb-dashboard-panel xb-upload-drop">
        <div class="xb-panel-title">
          <h3>{{ t('pages.dashboard.quickUpload') }}</h3>
          <router-link to="/inbox">{{ t('routes.inbox') }}</router-link>
        </div>
        <label
          class="xb-drop-upload-target"
          @dragenter.prevent="onDragEnter"
          @dragover.prevent="draggingFiles = true"
          @drop.prevent="onFileDrop"
        >
          <CloudUpload :size="34" />
          <strong>{{ t('pages.dashboard.dropHint') }}</strong>
          <span>{{ t('pages.dashboard.dropHintDesc') }}</span>
          <input type="file" multiple @click="resetFileInput" @change="onFileChange" />
        </label>
      </article>

      <article class="xb-dashboard-panel xb-xuandrop-card">
        <div class="xb-panel-title">
          <h3>{{ t('routes.drop') }}</h3>
          <router-link to="/drop">{{ t('common.actions.open') }}</router-link>
        </div>
        <div class="xb-device-transfer">
          <div class="xb-phone-glyph"></div>
          <Send :size="28" />
          <div>
            <strong>{{ activeDrop?.title || t('pages.dashboard.readyForNearby') }}</strong>
            <span>{{ activeDrop ? `${t('pages.dashboard.expiresPrefix', { date: formatDate(activeDrop.expires_at) })}` : t('pages.dashboard.transferHint') }}</span>
          </div>
        </div>
      </article>
    </section>

    <section class="xb-dashboard-footer">
      <router-link to="/files" class="xb-footer-action">
        <ShieldCheck :size="20" />
        <div>
          <strong>{{ t('pages.dashboard.importantDocs') }}</strong>
          <span v-if="summary?.expiring_documents?.length">{{ t('pages.dashboard.expiringDocsSuffix', { count: summary.expiring_documents.length }) }}</span>
          <span v-else>{{ t('pages.dashboard.noExpiringDocs') }}</span>
        </div>
        <AlertTriangle v-if="summary?.expiring_documents?.length" :size="18" />
        <CheckCircle2 v-else :size="18" />
      </router-link>
      <router-link to="/shared" class="xb-footer-action">
        <Share2 :size="20" />
        <div>
          <strong>{{ t('pages.dashboard.secureSharing') }}</strong>
          <span>{{ t('pages.dashboard.secureSharingHint') }}</span>
        </div>
      </router-link>
      <router-link to="/settings" class="xb-footer-action">
        <ShieldCheck :size="20" />
        <div>
          <strong>{{ t('pages.dashboard.deviceSecurity') }}</strong>
          <span>{{ t('pages.dashboard.deviceSecurityHint') }}</span>
        </div>
      </router-link>
    </section>
  </section>
</template>
