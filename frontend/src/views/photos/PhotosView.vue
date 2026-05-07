<script setup>
import { onMounted, ref } from 'vue'
import { Upload } from 'lucide-vue-next'
import PageHeader from '../../components/common/PageHeader.vue'
import EmptyState from '../../components/common/EmptyState.vue'
import { photoApi } from '../../api/photoApi'

const photos = ref([])
const loading = ref(false)

async function loadPhotos() {
  loading.value = true
  try {
    const response = await photoApi.list()
    const rows = response.data.data
    photos.value = await Promise.all(rows.map(async (photo) => {
      const thumb = await photoApi.thumbnailBlob(photo.id)
      return { ...photo, thumbUrl: URL.createObjectURL(thumb.data) }
    }))
  } finally {
    loading.value = false
  }
}

async function onPhotoChange(event) {
  const file = event.target.files?.[0]
  if (!file) return
  const formData = new FormData()
  formData.append('file', file)
  await photoApi.upload(formData)
  event.target.value = ''
  await loadPhotos()
}

onMounted(loadPhotos)
</script>

<template>
  <PageHeader title="Photos" subtitle="Timeline, thumbnails, previews, and albums all load through protected APIs.">
    <label class="xb-upload-button">
      <Upload :size="18" />
      Upload Photo
      <input type="file" accept="image/*" @change="onPhotoChange" />
    </label>
  </PageHeader>
  <EmptyState v-if="!loading && photos.length === 0" title="No photos yet" description="Upload your first photo to start building your private timeline." />
  <section v-else class="xb-photo-grid">
    <article v-for="photo in photos" :key="photo.id" class="xb-photo-card">
      <img :src="photo.thumbUrl" alt="" />
      <span>{{ photo.width }} x {{ photo.height }}</span>
    </article>
  </section>
</template>
