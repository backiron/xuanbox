<script setup>
import { computed, onMounted, ref } from 'vue'
import { Album, ChevronLeft, ChevronRight, Download, ImagePlus, Star, Upload, X } from 'lucide-vue-next'
import PageHeader from '../../components/common/PageHeader.vue'
import EmptyState from '../../components/common/EmptyState.vue'
import { albumApi, photoApi } from '../../api/photoApi'

const photos = ref([])
const albums = ref([])
const activeAlbumId = ref(null)
const loading = ref(false)
const uploadProgress = ref(0)
const previewIndex = ref(-1)
const previewUrl = ref('')
const touchStartX = ref(0)

const activePhotos = computed(() => photos.value)
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

async function hydrateThumbs(rows) {
  return Promise.all(rows.map(async (photo) => {
    const thumb = await photoApi.thumbnailBlob(photo.id)
    return { ...photo, thumbUrl: objectUrlFrom(thumb) }
  }))
}

async function loadAlbums() {
  const response = await albumApi.list()
  albums.value = response.data.data
}

async function loadPhotos() {
  loading.value = true
  try {
    await loadAlbums()
    const response = activeAlbumId.value ? await albumApi.photos(activeAlbumId.value) : await photoApi.list()
    photos.value = await hydrateThumbs(response.data.data)
  } finally {
    loading.value = false
  }
}

async function onPhotoChange(event) {
  const pickedFiles = Array.from(event.target.files || [])
  if (!pickedFiles.length) return
  uploadProgress.value = 1
  for (const pickedFile of pickedFiles) {
    const formData = new FormData()
    formData.append('file', pickedFile)
    await photoApi.upload(formData, {
      onUploadProgress(progressEvent) {
        if (progressEvent.total) uploadProgress.value = Math.round((progressEvent.loaded / progressEvent.total) * 100)
      }
    })
  }
  event.target.value = ''
  uploadProgress.value = 0
  await loadPhotos()
}

async function createAlbum() {
  const title = window.prompt('Album name')
  if (!title) return
  await albumApi.create({ title })
  await loadAlbums()
}

async function addToAlbum(photo) {
  if (!albums.value.length) {
    await createAlbum()
    if (!albums.value.length) return
  }
  const title = window.prompt('Add to album', albums.value[0]?.title || '')
  if (!title) return
  let album = albums.value.find((item) => item.title.toLowerCase() === title.toLowerCase())
  if (!album) {
    const response = await albumApi.create({ title })
    album = response.data.data
    await loadAlbums()
  }
  await albumApi.addPhoto(album.id, photo.id)
}

async function toggleFavorite(photo) {
  await photoApi.favorite(photo.id, !photo.is_favorite)
  await loadPhotos()
}

async function openPreview(photo) {
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
  closePreview()
  await loadPhotos()
}

onMounted(loadPhotos)
</script>

<template>
  <PageHeader title="Photos" subtitle="Timeline, thumbnails, previews, albums and original downloads all load through protected APIs.">
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

  <section class="xb-album-strip">
    <button class="xb-album-pill" :class="{ 'is-active': activeAlbumId === null }" type="button" @click="selectAlbum(null)">
      <Album :size="16" />
      Timeline
    </button>
    <button v-for="album in albums" :key="album.id" class="xb-album-pill" :class="{ 'is-active': activeAlbumId === album.id }" type="button" @click="selectAlbum(album.id)">
      <Album :size="16" />
      {{ album.title }}
    </button>
  </section>

  <EmptyState v-if="!loading && photos.length === 0" title="No photos yet" description="Upload your first photo to start building your private timeline." />

  <section v-else class="xb-timeline">
    <div v-for="group in groupedPhotos" :key="group.label" class="xb-timeline-group">
      <h3>{{ group.label }}</h3>
      <div class="xb-photo-grid">
        <article v-for="photo in group.items" :key="photo.id" class="xb-photo-card">
          <button type="button" @click="openPreview(photo)">
            <img :src="photo.thumbUrl" alt="" />
          </button>
          <span>{{ photo.width }} x {{ photo.height }}</span>
          <div class="xb-photo-actions">
            <button class="xb-icon-button" type="button" title="Favorite" @click="toggleFavorite(photo)">
              <Star :size="16" :fill="photo.is_favorite ? 'currentColor' : 'none'" />
            </button>
            <button class="xb-icon-button" type="button" title="Add to album" @click="addToAlbum(photo)">
              <Album :size="16" />
            </button>
          </div>
        </article>
      </div>
    </div>
  </section>

  <section v-if="activePreview" class="xb-lightbox" @click.self="closePreview" @touchstart="onTouchStart" @touchend="onTouchEnd">
    <div class="xb-lightbox-toolbar">
      <button class="xb-icon-button" type="button" @click="stepPreview(-1)">
        <ChevronLeft :size="20" />
      </button>
      <strong>{{ activePreview.width }} x {{ activePreview.height }}</strong>
      <button class="xb-icon-button" type="button" title="Download original" @click="downloadOriginal(activePreview)">
        <Download :size="19" />
      </button>
      <button class="xb-icon-button" type="button" @click="stepPreview(1)">
        <ChevronRight :size="20" />
      </button>
      <button class="xb-icon-button" type="button" @click="closePreview">
        <X :size="20" />
      </button>
    </div>
    <button class="xb-lightbox-edge left" type="button" @click="stepPreview(-1)">
      <ChevronLeft :size="34" />
    </button>
    <img :src="previewUrl" alt="" />
    <button class="xb-lightbox-edge right" type="button" @click="stepPreview(1)">
      <ChevronRight :size="34" />
    </button>
  </section>
</template>
