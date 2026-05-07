<script setup>
import { computed, onMounted, ref } from 'vue'
import { Download, LockKeyhole } from 'lucide-vue-next'
import { useRoute } from 'vue-router'

import { shareApi } from '../../api/shareApi'

const route = useRoute()
const token = computed(() => route.params.token)
const metadata = ref(null)
const password = ref('')
const verified = ref(false)
const loading = ref(false)
const error = ref('')

async function loadMetadata() {
  loading.value = true
  error.value = ''
  try {
    const response = await shareApi.publicMetadata(token.value)
    metadata.value = response.data.data
  } catch (err) {
    error.value = err.response?.data?.error?.message || 'Share is unavailable'
  } finally {
    loading.value = false
  }
}

async function verifyPassword() {
  error.value = ''
  try {
    await shareApi.verifyPassword(token.value, password.value)
    verified.value = true
  } catch (err) {
    error.value = err.response?.data?.error?.message || 'Password check failed'
  }
}

async function downloadShare() {
  error.value = ''
  try {
    const response = await shareApi.publicDownload(token.value, password.value)
    const blobUrl = URL.createObjectURL(response.data)
    const anchor = document.createElement('a')
    anchor.href = blobUrl
    anchor.download = metadata.value?.target_name || 'xuanbox-share'
    anchor.click()
    URL.revokeObjectURL(blobUrl)
    await loadMetadata()
  } catch (err) {
    error.value = err.response?.data?.error?.message || 'Download failed'
  }
}

function formatDate(value) {
  if (!value) return 'No expiry'
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))
}

onMounted(loadMetadata)
</script>

<template>
  <main class="xb-public-drop">
    <section class="xb-public-drop-panel xb-public-share-panel">
      <LockKeyhole :size="34" />
      <template v-if="metadata">
        <h1>{{ metadata.target_name }}</h1>
        <p>{{ metadata.owner_name }} shared this {{ metadata.target_type }} through XuanBox.</p>
        <div class="xb-public-share-meta">
          <span>{{ metadata.permission }}</span>
          <span>{{ metadata.download_count }} / {{ metadata.max_downloads || '∞' }} downloads</span>
          <span>{{ formatDate(metadata.expires_at) }}</span>
        </div>
        <form v-if="metadata.requires_password && !verified" class="xb-public-share-password" @submit.prevent="verifyPassword">
          <input v-model="password" type="password" placeholder="Password" />
          <button class="xb-primary-button" type="submit">Unlock</button>
        </form>
        <button v-else class="xb-primary-button" type="button" @click="downloadShare">
          <Download :size="16" />
          Download
        </button>
      </template>
      <p v-else-if="loading">Loading share...</p>
      <p v-if="error" class="xb-form-error">{{ error }}</p>
    </section>
  </main>
</template>
