<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Album, CheckSquare, ChevronDown, ChevronLeft, ChevronRight, Download, Edit3, FileCheck2, FolderInput, ImagePlus, ReceiptText, Share2, ShieldCheck, Square, Trash2, Upload, X } from 'lucide-vue-next'
import PageHeader from '../../components/common/PageHeader.vue'
import EmptyState from '../../components/common/EmptyState.vue'
import { importantDocApi } from '../../api/fileApi'
import { albumApi, photoApi } from '../../api/photoApi'
import { receiptApi } from '../../api/receiptApi'
import { useDialogStore } from '../../stores/dialogStore'

const photos = ref([])
const albums = ref([])
const activeAlbumId = ref(null)
const loading = ref(false)
const uploadProgress = ref(0)
const draggingPhotos = ref(false)
const previewIndex = ref(-1)
const previewUrl = ref('')
const selectedIds = ref(new Set())
const editMode = ref(false)
const moveModalOpen = ref(false)
const moveAlbumId = ref('')
const vaultStatus = ref({ pin_set: false, locked_until: null })
const importantUnlockToken = ref('')
const currentPage = ref(1)
const isMobileViewport = ref(window.matchMedia?.('(max-width: 840px)').matches ?? false)
const pageSize = computed(() => isMobileViewport.value ? 24 : 48)
const touchStartX = ref(0)
const thumbUrls = new Map()
let thumbHydrateTimer = 0
let cleanupViewportListener = null
const dialog = useDialogStore()
const router = useRouter()

const totalPages = computed(() => Math.max(1, Math.ceil(photos.value.length / pageSize.value)))
const pageStart = computed(() => (currentPage.value - 1) * pageSize.value)
const pageEnd = computed(() => Math.min(photos.value.length, pageStart.value + pageSize.value))
const activePhotos = computed(() => photos.value.slice(pageStart.value, pageEnd.value))
const selectedPhotos = computed(() => photos.value.filter((photo) => selectedIds.value.has(photo.id)))
const visibleMobileAlbums = computed(() => albums.value.slice(0, 2))
const hiddenMobileAlbums = computed(() => albums.value.slice(2))
const groupedPhotos = computed(() => {
  const groups = new Map()
  for (const photo of activePhotos.value) {
    const date = new Date(photo.taken_at || photo.uploaded_at)
    const key = new Intl.DateTimeFormat(undefined, { month: 'long', year: 'numeric' }).format(date)
    if (!groups.has(key)) groups.set(key, [])
    groups.get(key).push(photo)
  }
  return [...groups.entries()].map(([label, items]) => ({ label, items }))
})
const activePreview = computed(() => previewIndex.value >= 0 ? activePhotos.value[previewIndex.value] : null)

function objectUrlFrom(blobResponse) {
  return URL.createObjectURL(blobResponse.data)
}

function revokeThumbUrls() {
  for (const url of thumbUrls.values()) URL.revokeObjectURL(url)
  thumbUrls.clear()
}

async function hydrateVisibleThumbs() {
  const targets = activePhotos.value.filter((photo) => !photo.thumbUrl && !photo.thumbLoading)
  const concurrency = isMobileViewport.value ? 4 : 8
  let cursor = 0
  async function worker() {
    while (cursor < targets.length) {
      const photo = targets[cursor]
      cursor += 1
      photo.thumbLoading = true
      try {
        const thumb = await photoApi.thumbnailBlob(photo.id)
        const url = objectUrlFrom(thumb)
        thumbUrls.set(photo.id, url)
        photo.thumbUrl = url
      } catch {
        photo.thumbUrl = ''
      } finally {
        photo.thumbLoading = false
      }
    }
  }
  await Promise.all(Array.from({ length: Math.min(concurrency, targets.length) }, worker))
}

function scheduleHydrateVisibleThumbs() {
  window.clearTimeout(thumbHydrateTimer)
  thumbHydrateTimer = window.setTimeout(() => {
    hydrateVisibleThumbs()
  }, 40)
}

async function loadAlbums() {
  const response = await albumApi.list()
  albums.value = [...response.data.data].sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at))
}

async function loadPhotos() {
  loading.value = true
  try {
    await loadAlbums()
    const response = activeAlbumId.value ? await albumApi.photos(activeAlbumId.value) : await photoApi.list()
    revokeThumbUrls()
    photos.value = response.data.data.map((photo) => ({ ...photo, thumbUrl: '', thumbLoading: false }))
    currentPage.value = Math.min(currentPage.value, totalPages.value)
    selectedIds.value = new Set([...selectedIds.value].filter((id) => photos.value.some((photo) => photo.id === id)))
    scheduleHydrateVisibleThumbs()
  } finally {
    loading.value = false
  }
}

async function uploadPhotoFiles(files) {
  const pickedFiles = Array.from(files || []).filter((file) => file.type.startsWith('image/'))
  if (!pickedFiles.length) return
  uploadProgress.value = 1
  for (const pickedFile of pickedFiles) {
    const formData = new FormData()
    formData.append('file', pickedFile)
    const response = await photoApi.upload(formData, {
      onUploadProgress(progressEvent) {
        if (progressEvent.total) uploadProgress.value = Math.round((progressEvent.loaded / progressEvent.total) * 100)
      }
    })
    const uploadedPhoto = response.data.data
    if (activeAlbumId.value && uploadedPhoto?.id) {
      await albumApi.addPhoto(activeAlbumId.value, uploadedPhoto.id)
    }
  }
  uploadProgress.value = 0
  currentPage.value = 1
  await loadPhotos()
}

async function onPhotoChange(event) {
  await uploadPhotoFiles(event.target.files)
  event.target.value = ''
}

function onDragEnter(event) {
  if (!event.dataTransfer?.types?.includes('Files')) return
  draggingPhotos.value = true
}

function onDragLeave(event) {
  if (event.currentTarget.contains(event.relatedTarget)) return
  draggingPhotos.value = false
}

async function onPhotoDrop(event) {
  draggingPhotos.value = false
  await uploadPhotoFiles(event.dataTransfer?.files)
}

async function createAlbum() {
  const title = await dialog.prompt({ title: 'New album', label: 'Album name', placeholder: 'Japan trip' })
  if (!title) return
  const response = await albumApi.create({ title })
  await loadAlbums()
  return response.data.data
}

async function ensureAlbumForMove() {
  if (!albums.value.length) {
    const createdAlbum = await createAlbum()
    if (!createdAlbum) return null
    return createdAlbum
  }
  return null
}

async function openMoveModal() {
  if (!selectedPhotos.value.length) return
  const createdAlbum = await ensureAlbumForMove()
  if (!albums.value.length && !createdAlbum) return
  moveAlbumId.value = activeAlbumId.value || createdAlbum?.id || albums.value[0]?.id || ''
  moveModalOpen.value = true
}

function shareSelectedPhotos() {
  if (!selectedPhotos.value.length) return
  router.push({
    name: 'shared',
    query: {
      type: 'photo',
      ids: selectedPhotos.value.map((photo) => photo.id).join(',')
    }
  })
}

function closeMoveModal() {
  moveModalOpen.value = false
  moveAlbumId.value = ''
}

async function moveSelectedToAlbum() {
  if (!moveAlbumId.value || !selectedPhotos.value.length) return
  await Promise.all(selectedPhotos.value.map((photo) => albumApi.addPhoto(moveAlbumId.value, photo.id)))
  closeMoveModal()
  clearSelection()
  await loadPhotos()
}

function toggleSelected(photo) {
  if (!editMode.value) return
  const next = new Set(selectedIds.value)
  if (next.has(photo.id)) next.delete(photo.id)
  else next.add(photo.id)
  selectedIds.value = next
}

function clearSelection() {
  selectedIds.value = new Set()
}

function toggleEditMode() {
  editMode.value = !editMode.value
  if (!editMode.value) clearSelection()
}

async function deletePhotos(targetPhotos = selectedPhotos.value) {
  if (!targetPhotos.length) return
  const confirmed = await dialog.confirm({
    title: targetPhotos.length === 1 ? 'Delete photo' : 'Delete selected photos',
    message: targetPhotos.length === 1
      ? 'This photo will be removed from Photos.'
      : `${targetPhotos.length} photos will be removed from Photos.`,
    confirmText: 'Delete',
    danger: true
  })
  if (!confirmed) return
  const ids = new Set(targetPhotos.map((photo) => photo.id))
  await Promise.all(targetPhotos.map((photo) => photoApi.remove(photo.id)))
  selectedIds.value = new Set([...selectedIds.value].filter((id) => !ids.has(id)))
  if (activePreview.value && ids.has(activePreview.value.id)) closePreview()
  await loadPhotos()
}

function goToPage(page) {
  currentPage.value = Math.min(Math.max(page, 1), totalPages.value)
  clearSelection()
  closePreview()
  scheduleHydrateVisibleThumbs()
  document.querySelector('.xb-photo-page')?.scrollIntoView({ block: 'start', behavior: 'smooth' })
}

async function openPreview(photo) {
  if (editMode.value) {
    toggleSelected(photo)
    return
  }
  previewIndex.value = activePhotos.value.findIndex((item) => item.id === photo.id)
  await loadPreview()
}

async function loadPreview() {
  if (!activePreview.value) return
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
  const response = await photoApi.previewBlob(activePreview.value.id)
  previewUrl.value = objectUrlFrom(response)
}

async function stepPreview(direction) {
  if (!activePhotos.value.length) return
  previewIndex.value = (previewIndex.value + direction + activePhotos.value.length) % activePhotos.value.length
  await loadPreview()
}

function closePreview() {
  previewIndex.value = -1
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
  previewUrl.value = ''
}

async function downloadOriginal(photo) {
  const response = await photoApi.originalBlob(photo.id)
  const url = URL.createObjectURL(response.data)
  const link = document.createElement('a')
  link.href = url
  link.download = `photo-${photo.id}`
  link.click()
  URL.revokeObjectURL(url)
}

async function savePhotoAsReceipt(photo = activePreview.value) {
  if (!photo?.file_id) return
  const receipt = await receiptApi.createFromFile(photo.file_id, { category: 'photo import' })
  await dialog.confirm({
    title: 'Saved as receipt',
    message: 'This photo now appears in Receipts. OCR will run in the background and you can review fields there.',
    confirmText: 'Open Receipts'
  })
  closePreview()
  await router.push('/receipts')
  return receipt
}

async function addPhotoToImportantDocs(photo = activePreview.value) {
  if (!photo?.file_id) return
  if (!vaultStatus.value.pin_set) {
    const pin = await dialog.prompt({ title: 'Set Important docs PIN', label: '6 digit PIN', placeholder: '123456' })
    if (!pin) return
    const response = await importantDocApi.setup(pin)
    importantUnlockToken.value = response.data.data.unlock_token
    await loadVaultStatus()
  } else if (!importantUnlockToken.value) {
    const pin = await dialog.prompt({ title: 'Unlock Important docs', label: 'Vault PIN', placeholder: '6 digits' })
    if (!pin) return
    const response = await importantDocApi.unlock(pin)
    importantUnlockToken.value = response.data.data.unlock_token
  }
  await importantDocApi.createFromFile(photo.file_id, {
    title: `Photo document ${new Date(photo.uploaded_at || Date.now()).toLocaleDateString()}`,
    document_type: 'photo_document',
    security_level: 'vault_locked',
    note: 'Created from Photos'
  }, importantUnlockToken.value)
  await dialog.confirm({
    title: 'Added to Important docs',
    message: 'The original photo is now also protected in Important docs.',
    confirmText: 'OK'
  })
}

async function loadVaultStatus() {
  try {
    const response = await importantDocApi.status()
    vaultStatus.value = response.data.data
  } catch {
    vaultStatus.value = { pin_set: false, locked_until: null }
  }
}

function onTouchStart(event) {
  touchStartX.value = event.changedTouches[0]?.clientX || 0
}

async function onTouchEnd(event) {
  const endX = event.changedTouches[0]?.clientX || 0
  const delta = endX - touchStartX.value
  if (Math.abs(delta) < 48) return
  await stepPreview(delta > 0 ? -1 : 1)
}

async function selectAlbum(albumId) {
  activeAlbumId.value = albumId
  currentPage.value = 1
  clearSelection()
  editMode.value = false
  closePreview()
  await loadPhotos()
}

onMounted(async () => {
  const mediaQuery = window.matchMedia?.('(max-width: 840px)')
  const updateViewportMode = () => {
    isMobileViewport.value = mediaQuery?.matches ?? false
    currentPage.value = Math.min(currentPage.value, totalPages.value)
    scheduleHydrateVisibleThumbs()
  }
  mediaQuery?.addEventListener?.('change', updateViewportMode)
  cleanupViewportListener = () => mediaQuery?.removeEventListener?.('change', updateViewportMode)
  await Promise.all([loadPhotos(), loadVaultStatus()])
})
watch(currentPage, scheduleHydrateVisibleThumbs)
watch(activePreview, (photo) => {
  document.body.classList.toggle('xb-lightbox-open', Boolean(photo))
})
onBeforeUnmount(() => {
  document.body.classList.remove('xb-lightbox-open')
  window.clearTimeout(thumbHydrateTimer)
  cleanupViewportListener?.()
  revokeThumbUrls()
  closePreview()
})
</script>

<template>
  <div
    class="xb-photo-page"
    :class="{ 'is-dragging': draggingPhotos }"
    @dragenter.prevent="onDragEnter"
    @dragover.prevent="draggingPhotos = true"
    @dragleave="onDragLeave"
    @drop.prevent="onPhotoDrop"
  >
    <PageHeader title="Photos" subtitle="Timeline, thumbnails, previews, albums and original downloads all load through protected APIs.">
      <button class="xb-secondary-button" type="button" :class="{ 'is-active': editMode }" @click="toggleEditMode">
        <Edit3 :size="18" />
        {{ editMode ? 'Done' : 'Edit' }}
      </button>
      <button class="xb-secondary-button" type="button" @click="createAlbum">
        <ImagePlus :size="18" />
        Album
      </button>
      <label class="xb-upload-button">
        <Upload :size="18" />
        Upload Photo
        <input type="file" accept="image/*" multiple @change="onPhotoChange" />
      </label>
    </PageHeader>

    <div v-if="uploadProgress" class="xb-progress">
      <span :style="{ width: `${uploadProgress}%` }"></span>
    </div>

    <section class="xb-photo-drop-hint" :class="{ 'is-visible': draggingPhotos }">
      <Upload :size="18" />
      <strong>Drop photos to upload</strong>
      <span>{{ activeAlbumId ? 'They will also be added to this album.' : 'They will appear in Timeline.' }}</span>
    </section>

    <section v-if="editMode" class="xb-action-bar xb-photo-manage-bar">
      <strong>{{ selectedPhotos.length ? `${selectedPhotos.length} selected` : 'Select photos' }}</strong>
      <button v-if="selectedPhotos.length" class="xb-text-button" type="button" @click="clearSelection">Clear</button>
      <button v-if="selectedPhotos.length" class="xb-text-button" type="button" @click="shareSelectedPhotos">
        <Share2 :size="16" />
        Share
      </button>
      <button v-if="selectedPhotos.length" class="xb-text-button" type="button" @click="openMoveModal">
        <FolderInput :size="16" />
        Move to
      </button>
      <button v-if="selectedPhotos.length" class="xb-text-button xb-danger-button" type="button" @click="deletePhotos()">
        <Trash2 :size="16" />
        Delete
      </button>
    </section>

    <section class="xb-album-strip xb-album-strip-desktop">
      <button class="xb-album-pill" :class="{ 'is-active': activeAlbumId === null }" type="button" @click="selectAlbum(null)">
        <Album :size="16" />
        Timeline
      </button>
      <button v-for="album in albums" :key="album.id" class="xb-album-pill" :class="{ 'is-active': activeAlbumId === album.id }" type="button" @click="selectAlbum(album.id)">
        <Album :size="16" />
        {{ album.title }}
      </button>
    </section>

    <section class="xb-album-strip xb-album-strip-mobile">
      <button class="xb-album-pill" :class="{ 'is-active': activeAlbumId === null }" type="button" @click="selectAlbum(null)">
        <Album :size="16" />
        Timeline
      </button>
      <button v-for="album in visibleMobileAlbums" :key="album.id" class="xb-album-pill" :class="{ 'is-active': activeAlbumId === album.id }" type="button" @click="selectAlbum(album.id)">
        <Album :size="16" />
        {{ album.title }}
      </button>
      <details v-if="hiddenMobileAlbums.length" class="xb-album-more">
        <summary class="xb-album-pill" :class="{ 'is-active': hiddenMobileAlbums.some((album) => album.id === activeAlbumId) }">
          <span>... More</span>
          <ChevronDown :size="15" />
        </summary>
        <nav>
          <button v-for="album in hiddenMobileAlbums" :key="album.id" type="button" :class="{ 'is-active': activeAlbumId === album.id }" @click="selectAlbum(album.id)">
            {{ album.title }}
          </button>
        </nav>
      </details>
    </section>

    <EmptyState v-if="!loading && photos.length === 0" title="No photos yet" description="Upload your first photo to start building your private timeline." />

    <section v-else class="xb-timeline">
      <div v-for="group in groupedPhotos" :key="group.label" class="xb-timeline-group">
        <h3>{{ group.label }}</h3>
        <div class="xb-photo-grid">
          <article v-for="photo in group.items" :key="photo.id" class="xb-photo-card" :class="{ 'is-selected': selectedIds.has(photo.id), 'is-editing': editMode }">
            <button class="xb-photo-open" type="button" @click="openPreview(photo)">
              <img v-if="photo.thumbUrl" :src="photo.thumbUrl" alt="" loading="lazy" decoding="async" />
              <ImagePlus v-else :size="22" />
            </button>
            <span>{{ photo.width }} x {{ photo.height }}</span>
            <div v-if="editMode" class="xb-photo-actions">
              <button class="xb-icon-button" type="button" :title="selectedIds.has(photo.id) ? 'Deselect' : 'Select'" @click="toggleSelected(photo)">
                <component :is="selectedIds.has(photo.id) ? CheckSquare : Square" :size="16" />
              </button>
            </div>
          </article>
        </div>
      </div>
    </section>

    <nav v-if="photos.length > pageSize" class="xb-pagination" aria-label="Photo pages">
      <div class="xb-pagination-meta">
        <span>{{ pageStart + 1 }}-{{ pageEnd }} / {{ photos.length }}</span>
        <strong>Page {{ currentPage }} of {{ totalPages }}</strong>
      </div>
      <button class="xb-secondary-button" type="button" :disabled="currentPage === 1" @click="goToPage(currentPage - 1)">
        <ChevronLeft :size="17" />
        Prev
      </button>
      <button class="xb-secondary-button" type="button" :disabled="currentPage === totalPages" @click="goToPage(currentPage + 1)">
        Next
        <ChevronRight :size="17" />
      </button>
    </nav>

    <section v-if="moveModalOpen" class="xb-modal-backdrop" @click.self="closeMoveModal">
      <form class="xb-modal xb-photo-move-modal" @submit.prevent="moveSelectedToAlbum">
        <FolderInput :size="24" />
        <h3>Move to album</h3>
        <p>{{ selectedPhotos.length }} selected photo{{ selectedPhotos.length > 1 ? 's' : '' }} will stay in Timeline and appear in the chosen album.</p>
        <label>
          Album
          <select v-model="moveAlbumId" required>
            <option v-for="album in albums" :key="album.id" :value="album.id">{{ album.title }}</option>
          </select>
        </label>
        <div class="xb-modal-actions">
          <button class="xb-primary-button" type="submit">
            <FolderInput :size="16" />
            Move
          </button>
          <button class="xb-secondary-button" type="button" @click="closeMoveModal">Cancel</button>
        </div>
      </form>
    </section>

    <Teleport to="body">
      <section v-if="activePreview" class="xb-lightbox" @click.self="closePreview" @touchstart="onTouchStart" @touchend="onTouchEnd">
        <div class="xb-lightbox-toolbar">
          <button class="xb-icon-button" type="button" title="Previous photo" @click="stepPreview(-1)">
            <ChevronLeft :size="20" />
          </button>
          <strong>{{ activePreview.width }} x {{ activePreview.height }}</strong>
          <button class="xb-icon-button" type="button" title="Download original" @click="downloadOriginal(activePreview)">
            <Download :size="19" />
          </button>
          <button class="xb-icon-button" type="button" title="Save as receipt" @click="savePhotoAsReceipt(activePreview)">
            <ReceiptText :size="19" />
          </button>
          <button class="xb-icon-button" type="button" title="Add to Important docs" @click="addPhotoToImportantDocs(activePreview)">
            <ShieldCheck :size="19" />
          </button>
          <button class="xb-icon-button xb-danger-button" type="button" title="Delete photo" @click="deletePhotos([activePreview])">
            <Trash2 :size="19" />
          </button>
          <button class="xb-icon-button" type="button" title="Next photo" @click="stepPreview(1)">
            <ChevronRight :size="20" />
          </button>
          <button class="xb-icon-button xb-lightbox-close-button" type="button" title="Close preview" @click="closePreview">
            <X :size="20" />
            <span class="xb-lightbox-close-label">Close</span>
          </button>
        </div>
        <button class="xb-lightbox-edge left" type="button" @click="stepPreview(-1)">
          <ChevronLeft :size="34" />
        </button>
        <div class="xb-lightbox-stage" @click.self="closePreview">
          <img :src="previewUrl" alt="" />
        </div>
        <button class="xb-lightbox-edge right" type="button" @click="stepPreview(1)">
          <ChevronRight :size="34" />
        </button>
        <div class="xb-lightbox-mobile-nav">
          <button class="xb-secondary-button" type="button" @click="downloadOriginal(activePreview)">
            <Download :size="18" />
          </button>
          <button class="xb-secondary-button" type="button" @click="savePhotoAsReceipt(activePreview)">
            <ReceiptText :size="18" />
            Receipt
          </button>
          <button class="xb-secondary-button" type="button" @click="addPhotoToImportantDocs(activePreview)">
            <FileCheck2 :size="18" />
            Important
          </button>
          <button class="xb-secondary-button xb-danger-button" type="button" @click="deletePhotos([activePreview])">
            <Trash2 :size="18" />
          </button>
          <button class="xb-secondary-button" type="button" @click="stepPreview(-1)">
            <ChevronLeft :size="18" />
            Prev
          </button>
          <button class="xb-secondary-button" type="button" @click="stepPreview(1)">
            Next
            <ChevronRight :size="18" />
          </button>
        </div>
      </section>
    </Teleport>
  </div>
</template>
