<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { BrainCircuit, FileText, Image, ReceiptText, Search, ShieldCheck } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import PageHeader from '../../components/common/PageHeader.vue'
import { searchApi } from '../../api/searchApi'

const route = useRoute()
const loading = ref(false)
const error = ref('')
const results = ref([])
const q = computed(() => String(route.query.q || '').trim())
const { t } = useI18n()

const resultGroups = computed(() => {
  const labels = {
    file: t('pages.search.typeLabels.file'),
    photo: t('pages.search.typeLabels.photo'),
    receipt: t('pages.search.typeLabels.receipt'),
    document: t('pages.search.typeLabels.document'),
    intelligence: t('pages.search.typeLabels.intelligence'),
    ocr: t('pages.search.typeLabels.ocr')
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
    filename: t('pages.search.labelFile'),
    photo: t('pages.search.labelPhoto'),
    'receipt-fields': t('pages.search.labelReceipFields'),
    'document-fields': t('pages.search.labelDocumentFields'),
    profile: t('pages.search.labelAIProfile'),
    'ocr-text': t('pages.search.labelOcrText')
  }
  return labels[source] || source || t('pages.search.labelMatch')
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
    error.value = err.response?.data?.message || t('pages.search.unavailable')
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
    :title="t('pages.search.title')"
    :subtitle="q ? `${route.query.q} ${t('common.status.loadingDots')}` : t('pages.search.subtitle')"
  />

  <section class="xb-search-page">
    <div v-if="loading" class="xb-empty-state">
      <div>
        <strong>{{ t('pages.search.searching') }}</strong>
        <p>{{ t('pages.search.searchingText') }}</p>
      </div>
    </div>

    <div v-else-if="error" class="xb-empty-state">
      <div>
        <strong>{{ t('pages.search.unavailable') }}</strong>
        <p>{{ error }}</p>
      </div>
    </div>

    <div v-else-if="!q" class="xb-empty-state">
      <div>
        <strong>{{ t('pages.search.startHintTitle') }}</strong>
        <p>{{ t('pages.search.startHint') }}</p>
      </div>
    </div>

    <div v-else-if="!results.length" class="xb-empty-state">
      <div>
        <strong>{{ t('pages.search.noResult') }}</strong>
        <p>{{ t('pages.search.noResultText') }}</p>
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
