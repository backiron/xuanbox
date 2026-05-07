<script setup>
import { onMounted, ref } from 'vue'
import { CalendarClock, Filter, ReceiptText, Save, Search, Upload } from 'lucide-vue-next'
import PageHeader from '../../components/common/PageHeader.vue'
import EmptyState from '../../components/common/EmptyState.vue'
import { receiptApi } from '../../api/receiptApi'

const receipts = ref([])
const loading = ref(false)
const uploadProgress = ref(0)
const filters = ref({ q: '', category: '', merchant: '', year: '' })
const draft = ref({ merchant: '', category: '', amount: '', currency: 'USD', purchase_date: '', warranty_until: '', notes: '' })
const editing = ref(null)

function cleanPayload(source) {
  return {
    merchant: source.merchant || null,
    category: source.category || null,
    amount: source.amount === '' || source.amount === null ? null : source.amount,
    currency: source.currency || 'USD',
    purchase_date: source.purchase_date || null,
    warranty_until: source.warranty_until || null,
    notes: source.notes || null
  }
}

function formatMoney(receipt) {
  if (receipt.amount === null || receipt.amount === undefined) return 'No amount'
  return `${receipt.currency} ${Number(receipt.amount).toFixed(2)}`
}

async function loadReceipts() {
  loading.value = true
  try {
    const params = Object.fromEntries(Object.entries(filters.value).filter(([, value]) => value))
    const response = await receiptApi.list(params)
    receipts.value = response.data.data
  } finally {
    loading.value = false
  }
}

async function onReceiptFile(event) {
  const file = event.target.files?.[0]
  if (!file) return
  const formData = new FormData()
  formData.append('file', file)
  for (const [key, value] of Object.entries(cleanPayload(draft.value))) {
    if (value !== null) formData.append(key, value)
  }
  uploadProgress.value = 1
  await receiptApi.upload(formData, {
    onUploadProgress(progressEvent) {
      if (progressEvent.total) uploadProgress.value = Math.round((progressEvent.loaded / progressEvent.total) * 100)
    }
  })
  uploadProgress.value = 0
  event.target.value = ''
  draft.value = { merchant: '', category: '', amount: '', currency: 'USD', purchase_date: '', warranty_until: '', notes: '' }
  await loadReceipts()
}

function startEdit(receipt) {
  editing.value = { ...receipt, amount: receipt.amount ?? '' }
}

async function saveEdit() {
  await receiptApi.update(editing.value.id, cleanPayload(editing.value))
  editing.value = null
  await loadReceipts()
}

onMounted(loadReceipts)
</script>

<template>
  <PageHeader title="Receipts" subtitle="Encrypted receipt captures with merchant, amount, date, warranty, filters and search.">
    <label class="xb-upload-button">
      <Upload :size="18" />
      Upload Receipt
      <input type="file" accept="image/*,.pdf" @change="onReceiptFile" />
    </label>
  </PageHeader>

  <div v-if="uploadProgress" class="xb-progress">
    <span :style="{ width: `${uploadProgress}%` }"></span>
  </div>

  <section class="xb-receipt-layout">
    <aside class="xb-panel xb-receipt-form">
      <h3>Receipt details</h3>
      <label>Merchant <input v-model="draft.merchant" /></label>
      <label>Category <input v-model="draft.category" placeholder="Fuel, electronics, groceries" /></label>
      <label>Amount <input v-model="draft.amount" type="number" step="0.01" /></label>
      <label>Currency <input v-model="draft.currency" maxlength="8" /></label>
      <label>Purchase date <input v-model="draft.purchase_date" type="date" /></label>
      <label>Warranty until <input v-model="draft.warranty_until" type="date" /></label>
      <label>Notes <textarea v-model="draft.notes" rows="4"></textarea></label>
    </aside>

    <section>
      <div class="xb-filter-bar">
        <div class="xb-filter-field">
          <Search :size="16" />
          <input v-model="filters.q" placeholder="Search receipts" @keyup.enter="loadReceipts" />
        </div>
        <div class="xb-filter-field">
          <Filter :size="16" />
          <input v-model="filters.category" placeholder="Category" @keyup.enter="loadReceipts" />
        </div>
        <div class="xb-filter-field">
          <ReceiptText :size="16" />
          <input v-model="filters.merchant" placeholder="Merchant" @keyup.enter="loadReceipts" />
        </div>
        <div class="xb-filter-field">
          <CalendarClock :size="16" />
          <input v-model="filters.year" type="number" placeholder="Year" @keyup.enter="loadReceipts" />
        </div>
        <button class="xb-secondary-button" type="button" @click="loadReceipts">Apply</button>
      </div>

      <EmptyState v-if="!loading && receipts.length === 0" title="No receipts yet" description="Upload a receipt photo or PDF, then edit its structured fields." />

      <div v-else class="xb-receipt-list">
        <article v-for="receipt in receipts" :key="receipt.id" class="xb-receipt-row">
          <div>
            <strong>{{ receipt.merchant || 'Unknown merchant' }}</strong>
            <span>{{ receipt.category || 'Uncategorized' }} · {{ receipt.purchase_date || 'No date' }}</span>
          </div>
          <strong>{{ formatMoney(receipt) }}</strong>
          <span>{{ receipt.warranty_until ? `Warranty ${receipt.warranty_until}` : 'No warranty' }}</span>
          <button class="xb-text-button" type="button" @click="startEdit(receipt)">Edit</button>
        </article>
      </div>
    </section>
  </section>

  <section v-if="editing" class="xb-modal-backdrop" @click.self="editing = null">
    <form class="xb-modal" @submit.prevent="saveEdit">
      <h3>Edit receipt</h3>
      <label>Merchant <input v-model="editing.merchant" /></label>
      <label>Category <input v-model="editing.category" /></label>
      <label>Amount <input v-model="editing.amount" type="number" step="0.01" /></label>
      <label>Currency <input v-model="editing.currency" maxlength="8" /></label>
      <label>Purchase date <input v-model="editing.purchase_date" type="date" /></label>
      <label>Warranty until <input v-model="editing.warranty_until" type="date" /></label>
      <label>Notes <textarea v-model="editing.notes" rows="4"></textarea></label>
      <div class="xb-row-actions">
        <button class="xb-primary-button" type="submit">
          <Save :size="17" />
          Save
        </button>
        <button class="xb-secondary-button" type="button" @click="editing = null">Cancel</button>
      </div>
    </form>
  </section>
</template>
