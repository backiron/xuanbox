<script setup>
import { computed, onMounted, ref } from 'vue'
import { AlertTriangle } from 'lucide-vue-next'

import PageHeader from '../../components/common/PageHeader.vue'
import { dashboardApi } from '../../api/documentApi'

const summary = ref(null)
const loading = ref(false)

const cards = computed(() => {
  const metrics = summary.value?.metrics || {}
  return [
    { label: 'Storage', value: formatBytes(metrics.storage_bytes || 0), hint: 'Local encrypted vault' },
    { label: 'Photos', value: metrics.photos_count || 0, hint: 'Timeline ready' },
    { label: 'Files', value: metrics.files_count || 0, hint: 'Encrypted storage' },
    { label: 'Documents', value: metrics.documents_count || 0, hint: 'Expiry reminders' },
    { label: 'OCR', value: metrics.pending_ocr_count || 0, hint: 'Pending confirmation' }
  ]
})

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

async function loadSummary() {
  loading.value = true
  try {
    const response = await dashboardApi.summary()
    summary.value = response.data.data
  } finally {
    loading.value = false
  }
}

onMounted(loadSummary)
</script>

<template>
  <PageHeader title="Dashboard" subtitle="Your private space is isolated, encrypted, and ready for local testing." />
  <section class="xb-metric-grid">
    <article v-for="card in cards" :key="card.label" class="xb-metric-card">
      <span>{{ card.label }}</span>
      <strong>{{ card.value }}</strong>
      <p>{{ card.hint }}</p>
    </article>
  </section>
  <section class="xb-panel-grid">
    <article class="xb-panel">
      <h3>Document Reminders</h3>
      <div v-if="summary?.expiring_documents?.length" class="xb-reminder-list">
        <router-link v-for="item in summary.expiring_documents" :key="item.id" to="/documents" class="xb-reminder-row">
          <AlertTriangle :size="17" />
          <span>{{ item.title }}</span>
          <strong>{{ item.expires_at }}</strong>
        </router-link>
      </div>
      <p v-else>{{ loading ? 'Loading reminders...' : 'No documents expiring in the next 90 days.' }}</p>
    </article>
    <article class="xb-panel">
      <h3>XuanDrop</h3>
      <p>Device transfer is ready for quick mobile uploads into the vault.</p>
    </article>
    <article class="xb-panel">
      <h3>Security</h3>
      <p>High-sensitive documents require password verification before download.</p>
    </article>
  </section>
</template>
