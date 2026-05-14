<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { BrainCircuit, FileText, Image, ReceiptText, Search, ShieldCheck } from 'lucide-vue-next'
import PageHeader from '../../components/common/PageHeader.vue'
import { searchApi } from '../../api/searchApi'

const route = useRoute()
const loading = ref(false)
const error = ref('')
const results = ref([])
const q = computed(() => String(route.query.q || '').trim())

const resultGroups = computed(() => {
  const labels = {
    file: 'Files',
    photo: 'Photos',
    receipt: 'Receipts',
    document: 'Important docs',
    intelligence: 'Document intelligence',
    ocr: 'OCR text'
  }
  const icons = {
    file: FileText,
    photo: Image,
    receipt: ReceiptText,
    document: ShieldCheck,
    intelligence: BrainCircuit,
    ocr: Search
  }
  const groups = new Map()
  for (const item of results.value) {
    const type = item.type || 'file'
    if (!groups.has(type)) {
      groups.set(type, {
        type,
        label: labels[type] || 'Results',
        icon: icons[type] || FileText,
        items: []
      })
    }
    groups.get(type).items.push(item)
  }
  return Array.from(groups.values())
})

function sourceLabel(source) {
  const labels = {
    filename: 'Filename',
    photo: 'Photo',
    'receipt-fields': 'Receipt fields',
    'document-fields': 'Document fields',
    profile: 'AI profile',
    'ocr-text': 'Extracted text'
  }
  return labels[source] || source || 'Match'
}

function resultKey(item) {
  return `${item.type}-${item.id}-${item.source}`
}

async function load() {
  if (!q.value) {
    results.value = []
    error.value = ''
    return
  }
  loading.value = true
  error.value = ''
  try {
    const response = await searchApi.query(q.value, { limit: 60 })
    results.value = response.data.data.results || []
  } catch (err) {
    error.value = err.response?.data?.message || 'Search failed.'
    results.value = []
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(() => route.query.q, load)
</script>

<template>
  <PageHeader
    title="Search"
    :subtitle="q ? `Results for ${route.query.q}` : 'Search filenames, receipts, document fields, and OCR text.'"
  />

  <section class="xb-search-page">
    <div v-if="loading" class="xb-empty-state">
      <div>
        <strong>Searching...</strong>
        <p>Checking filenames, structured fields, and extracted document text.</p>
      </div>
    </div>

    <div v-else-if="error" class="xb-empty-state">
      <div>
        <strong>Search unavailable</strong>
        <p>{{ error }}</p>
      </div>
    </div>

    <div v-else-if="!q" class="xb-empty-state">
      <div>
        <strong>Start with the search box above</strong>
        <p>Results can include OCR matches from uploaded files and photos.</p>
      </div>
    </div>

    <div v-else-if="!results.length" class="xb-empty-state">
      <div>
        <strong>No results found</strong>
        <p>No filename, receipt, document field, or OCR text matched this search.</p>
      </div>
    </div>

    <div v-else class="xb-search-results">
      <article v-for="group in resultGroups" :key="group.type" class="xb-panel xb-search-group">
        <h3>
          <component :is="group.icon" :size="18" />
          {{ group.label }}
          <span>{{ group.items.length }}</span>
        </h3>
        <router-link v-for="item in group.items" :key="resultKey(item)" :to="item.route" class="xb-search-result-row">
          <div class="xb-search-result-main">
            <strong>{{ item.title }}</strong>
            <span>{{ item.subtitle || sourceLabel(item.source) }}</span>
          </div>
          <p v-if="item.snippet">{{ item.snippet }}</p>
          <small>{{ sourceLabel(item.source) }}</small>
        </router-link>
      </article>
    </div>
  </section>
</template>
