<script setup>
import { computed, onMounted, ref } from 'vue'
import { Download, LockKeyhole } from 'lucide-vue-next'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'

import { shareApi } from '../../api/shareApi'

const route = useRoute()
const { t } = useI18n()
const token = computed(() => route.params.token)
const metadata = ref(null)
const password = ref('')
const verified = ref(false)
const shareAccessToken = ref('')
const loading = ref(false)
const error = ref('')

async function loadMetadata() {
  loading.value = true
  error.value = ''
  try {
    const response = await shareApi.publicMetadata(token.value)
    metadata.value = response.data.data
  } catch (err) {
    error.value = err.response?.data?.error?.message || t('pages.publicShare.unavailable')
  } finally {
    loading.value = false
  }
}

async function verifyPassword() {
  error.value = ''
  try {
    const response = await shareApi.verifyPassword(token.value, password.value)
    shareAccessToken.value = response.data.data.access_token
    verified.value = true
    password.value = ''
  } catch (err) {
    error.value = err.response?.data?.error?.message || t('pages.publicShare.failPassword')
  }
}

async function downloadShare() {
  error.value = ''
  try {
    const response = await shareApi.publicDownload(token.value, shareAccessToken.value)
    const blobUrl = URL.createObjectURL(response.data)
    const anchor = document.createElement('a')
    anchor.href = blobUrl
    anchor.download = metadata.value?.target_name || 'xuanbox-share'
    anchor.click()
    URL.revokeObjectURL(blobUrl)
    await loadMetadata()
  } catch (err) {
    error.value = err.response?.data?.error?.message || t('pages.publicShare.failDownload')
  }
}

function formatDate(value) {
  if (!value) return t('common.file.noExpiry')
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
        <p>{{ t('pages.publicShare.downloadedFrom', { owner: metadata.owner_name, type: metadata.target_type }) }}</p>
        <div class="xb-public-share-meta">
          <span>{{ metadata.permission }}</span>
          <span>{{ t('pages.publicShare.maxDownloads', { count: metadata.download_count, limit: metadata.max_downloads || t('common.states.unlimited') }) }}</span>
          <span>{{ formatDate(metadata.expires_at) }}</span>
        </div>
        <form v-if="metadata.requires_password && !verified" class="xb-public-share-password" @submit.prevent="verifyPassword">
          <input v-model="password" type="password" :placeholder="t('pages.publicShare.password')" />
          <button class="xb-primary-button" type="submit">{{ t('pages.publicShare.unlock') }}</button>
        </form>
        <button v-else class="xb-primary-button" type="button" @click="downloadShare">
          <Download :size="16" />
          {{ t('pages.publicShare.download') }}
        </button>
      </template>
      <p v-else-if="loading">{{ t('pages.publicShare.loading') }}</p>
      <p v-if="error" class="xb-form-error">{{ error }}</p>
    </section>
  </main>
</template>
