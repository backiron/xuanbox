<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { Camera, Download, FileImage, FileSearch, MoreHorizontal, ReceiptText, RotateCcw, Save, Search, Trash2, Upload, X } from 'lucide-vue-next'
import PageHeader from '../../components/common/PageHeader.vue'
import EmptyState from '../../components/common/EmptyState.vue'
import { fileApi } from '../../api/fileApi'
import { receiptApi } from '../../api/receiptApi'
import { useDialogStore } from '../../stores/dialogStore'

const receipts = ref([])
const loading = ref(false)
const uploadProgress = ref(0)
const draggingReceipts = ref(false)
const filters = ref({ q: '', category: '', merchant: '', year: '' })
const draft = ref({ merchant: '', category: '', amount: '', currency: 'USD', purchase_date: '', warranty_until: '', notes: '' })
const manualEntryOpen = ref(false)
const editing = ref(null)
const ocrReview = ref(null)
const receiptSheet = ref(null)
const rawTextOpen = ref(false)
const activePreview = ref({ url: '', type: '', loading: false, error: '' })
const dialog = useDialogStore()

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

function receiptStatusLabel(receipt) {
  const labels = {
    not_started: 'Needs OCR',
    pending: 'Queued',
    processing: 'Reading',
    completed: 'Needs review',
    confirmed: 'Confirmed',
    failed: 'Failed'
  }
  return labels[receipt.ocr_status] || receipt.ocr_status
}

function cleanupPreview() {
  if (activePreview.value.url) URL.revokeObjectURL(activePreview.value.url)
  activePreview.value = { url: '', type: '', loading: false, error: '' }
}

function closeOcrReview() {
  ocrReview.value = null
  rawTextOpen.value = false
  cleanupPreview()
}

function openReceiptSheet(receipt) {
  receiptSheet.value = receipt
}

function closeReceiptSheet() {
  receiptSheet.value = null
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

async function uploadReceiptFiles(files) {
  const pickedFiles = Array.from(files || [])
  if (!pickedFiles.length) return
  uploadProgress.value = 1
  for (const file of pickedFiles) {
    const formData = new FormData()
    formData.append('file', file)
    for (const [key, value] of Object.entries(cleanPayload(draft.value))) {
      if (value !== null) formData.append(key, value)
    }
    await receiptApi.upload(formData, {
      onUploadProgress(progressEvent) {
        if (progressEvent.total) uploadProgress.value = Math.round((progressEvent.loaded / progressEvent.total) * 100)
      }
    })
  }
  uploadProgress.value = 0
  draft.value = { merchant: '', category: '', amount: '', currency: 'USD', purchase_date: '', warranty_until: '', notes: '' }
  await loadReceipts()
  window.setTimeout(loadReceipts, 2000)
}

async function onReceiptFile(event) {
  await uploadReceiptFiles(event.target.files)
  event.target.value = ''
}

function onDragEnter(event) {
  if (!event.dataTransfer?.types?.includes('Files')) return
  draggingReceipts.value = true
}

function onDragLeave(event) {
  if (event.currentTarget.contains(event.relatedTarget)) return
  draggingReceipts.value = false
}

async function onReceiptDrop(event) {
  draggingReceipts.value = false
  await uploadReceiptFiles(event.dataTransfer?.files)
}

function startEdit(receipt) {
  closeReceiptSheet()
  editing.value = { ...receipt, amount: receipt.amount ?? '' }
}

async function saveEdit() {
  await receiptApi.update(editing.value.id, cleanPayload(editing.value))
  editing.value = null
  await loadReceipts()
}

async function deleteReceipt(receipt) {
  const wasSheetOpen = receiptSheet.value?.id === receipt.id
  if (wasSheetOpen) closeReceiptSheet()
  const confirmed = await dialog.confirm({
    title: 'Delete receipt',
    message: 'This removes the receipt record and OCR review data. The original file stays in storage if it is used elsewhere.',
    confirmText: 'Delete',
    danger: true
  })
  if (!confirmed && wasSheetOpen && receipts.value.some((item) => item.id === receipt.id)) {
    openReceiptSheet(receipt)
  }
  if (!confirmed) return
  await receiptApi.remove(receipt.id)
  receipts.value = receipts.value.filter((item) => item.id !== receipt.id)
  if (editing.value?.id === receipt.id) editing.value = null
  if (ocrReview.value?.receipt?.id === receipt.id) closeOcrReview()
  await loadReceipts()
}

async function startOcr(receipt) {
  closeReceiptSheet()
  await receiptApi.startOcr(receipt.id)
  await loadReceipts()
  window.setTimeout(loadReceipts, 2000)
}

async function loadReceiptPreview(receipt) {
  cleanupPreview()
  activePreview.value.loading = true
  try {
    const response = await fileApi.download(receipt.file_id)
    const blob = response.data
    activePreview.value = {
      url: URL.createObjectURL(blob),
      type: blob.type || '',
      loading: false,
      error: ''
    }
  } catch (error) {
    activePreview.value = { url: '', type: '', loading: false, error: 'Preview unavailable.' }
  }
}

async function loadOcrReview(receipt) {
  closeReceiptSheet()
  rawTextOpen.value = false
  await loadReceiptPreview(receipt)
  const response = await receiptApi.ocrTasks(receipt.id)
  const task = response.data.data[0]
  if (!task) {
    ocrReview.value = {
      receipt,
      task: null,
      merchant: receipt.merchant || '',
      category: receipt.category || '',
      amount: receipt.amount || '',
      currency: receipt.currency || 'USD',
      purchase_date: receipt.purchase_date || '',
      warranty_until: receipt.warranty_until || '',
      notes: receipt.notes || '',
      raw_text: '',
      error_message: ''
    }
    return
  }
  const parsed = task.parsed_json || {}
  ocrReview.value = {
    receipt,
    task,
    merchant: parsed.merchant || receipt.merchant || '',
    category: parsed.category || receipt.category || '',
    amount: parsed.amount || receipt.amount || '',
    currency: parsed.currency || receipt.currency || 'USD',
    purchase_date: parsed.purchase_date || receipt.purchase_date || '',
    warranty_until: parsed.warranty_until || receipt.warranty_until || '',
    notes: parsed.notes || receipt.notes || '',
    raw_text: task.raw_text || '',
    error_message: task.error_message || ''
  }
}

async function confirmOcr() {
  await receiptApi.confirmOcr(ocrReview.value.receipt.id, ocrReview.value.task.id, cleanPayload(ocrReview.value))
  closeOcrReview()
  await loadReceipts()
}

async function retryOcr() {
  await receiptApi.retryOcr(ocrReview.value.receipt.id, ocrReview.value.task.id)
  closeOcrReview()
  await loadReceipts()
  window.setTimeout(loadReceipts, 2000)
}

async function downloadOriginal(receipt) {
  closeReceiptSheet()
  const response = await fileApi.download(receipt.file_id)
  const url = URL.createObjectURL(response.data)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = `${receipt.merchant || 'receipt'}-${receipt.purchase_date || receipt.id}`
  anchor.click()
  URL.revokeObjectURL(url)
}

onMounted(loadReceipts)
onBeforeUnmount(cleanupPreview)
</script>

<template>
  <div
    class="xb-upload-page xb-receipts-page"
    :class="{ 'is-dragging': draggingReceipts }"
    @dragenter.prevent="onDragEnter"
    @dragover.prevent="draggingReceipts = true"
    @dragleave="onDragLeave"
    @drop.prevent="onReceiptDrop"
  >
    <PageHeader title="Receipts" subtitle="Encrypted receipt captures with automatic OCR, review, original attachments, filters, and search.">
      <label class="xb-secondary-button">
        <Camera :size="18" />
        Take Photo
        <input type="file" accept="image/*" capture="environment" @change="onReceiptFile" />
      </label>
      <label class="xb-upload-button xb-receipt-upload-pill">
        <Upload :size="18" />
        Upload
        <input type="file" accept="image/*,.pdf" multiple @change="onReceiptFile" />
      </label>
      <button class="xb-secondary-button xb-receipt-manual-pill" type="button" @click="manualEntryOpen = true">
        <ReceiptText :size="18" />
        Manual Add
      </button>
    </PageHeader>

    <div v-if="uploadProgress" class="xb-progress">
      <span :style="{ width: `${uploadProgress}%` }"></span>
    </div>

    <section class="xb-upload-drop-hint" :class="{ 'is-visible': draggingReceipts }">
      <Upload :size="18" />
      <strong>Drop receipts to upload</strong>
      <span>Images and PDFs are encrypted, attached, and queued for OCR.</span>
    </section>

    <section class="xb-receipt-layout">
      <aside class="xb-panel xb-receipt-form">
        <h3>Manual receipt</h3>
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
            <input v-model="filters.q" placeholder="Search receipts and OCR text" @keyup.enter="loadReceipts" />
          </div>
          <button class="xb-secondary-button xb-filter-submit" type="button" aria-label="Search receipts" @click="loadReceipts">
            <Search :size="16" />
          </button>
        </div>

        <EmptyState v-if="!loading && receipts.length === 0" title="No receipts yet" description="Upload a receipt photo or PDF, then review the detected fields." />

        <div v-else class="xb-receipt-list">
          <article v-for="receipt in receipts" :key="receipt.id" class="xb-receipt-row" @click="openReceiptSheet(receipt)">
            <div class="xb-receipt-row-main">
              <strong>{{ receipt.merchant || 'Unknown merchant' }}</strong>
              <span>{{ receipt.category || 'Uncategorized' }} / {{ receipt.purchase_date || 'No date' }}</span>
            </div>
            <strong class="xb-receipt-row-amount">{{ formatMoney(receipt) }}</strong>
            <div class="xb-receipt-row-meta">
              <span>{{ receiptStatusLabel(receipt) }}</span>
              <span>{{ receipt.warranty_until ? `Warranty ${receipt.warranty_until}` : 'No warranty' }}</span>
            </div>
            <button class="xb-icon-button xb-receipt-more-button" type="button" title="Receipt actions" @click.stop="openReceiptSheet(receipt)">
              <MoreHorizontal :size="18" />
            </button>
            <div class="xb-row-actions xb-receipt-inline-actions">
              <button class="xb-text-button" type="button" @click.stop="loadOcrReview(receipt)">
                <FileImage :size="16" />
                View
              </button>
              <button v-if="receipt.ocr_status === 'not_started'" class="xb-text-button" type="button" @click.stop="startOcr(receipt)">
                <FileSearch :size="16" />
                OCR
              </button>
              <button v-else class="xb-text-button" type="button" @click.stop="loadOcrReview(receipt)">
                <RotateCcw v-if="receipt.ocr_status === 'failed'" :size="16" />
                <FileSearch v-else :size="16" />
                {{ receiptStatusLabel(receipt) }}
              </button>
              <button class="xb-text-button" type="button" @click.stop="startEdit(receipt)">Edit</button>
              <button class="xb-text-button xb-danger-button" type="button" @click.stop="deleteReceipt(receipt)">
                <Trash2 :size="16" />
                Delete
              </button>
            </div>
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

    <section v-if="manualEntryOpen" class="xb-modal-backdrop" @click.self="manualEntryOpen = false">
      <form class="xb-modal" @submit.prevent="manualEntryOpen = false">
        <h3>Manual receipt</h3>
        <label>Merchant <input v-model="draft.merchant" /></label>
        <label>Category <input v-model="draft.category" placeholder="Fuel, electronics, groceries" /></label>
        <label>Amount <input v-model="draft.amount" type="number" step="0.01" /></label>
        <label>Currency <input v-model="draft.currency" maxlength="8" /></label>
        <label>Purchase date <input v-model="draft.purchase_date" type="date" /></label>
        <label>Warranty until <input v-model="draft.warranty_until" type="date" /></label>
        <label>Notes <textarea v-model="draft.notes" rows="4"></textarea></label>
        <div class="xb-row-actions">
          <button class="xb-primary-button" type="submit">
            <Save :size="17" />
            Done
          </button>
          <button class="xb-secondary-button" type="button" @click="manualEntryOpen = false">Close</button>
        </div>
      </form>
    </section>

    <Teleport to="body">
      <section v-if="receiptSheet" class="xb-modal-backdrop xb-receipt-sheet-backdrop" @click.self="closeReceiptSheet">
        <aside class="xb-receipt-action-sheet">
          <div class="xb-receipt-sheet-handle"></div>
          <header class="xb-receipt-sheet-head">
            <div>
              <strong>{{ receiptSheet.merchant || 'Unknown merchant' }}</strong>
              <span>{{ receiptSheet.category || 'Uncategorized' }} / {{ receiptSheet.purchase_date || 'No date' }}</span>
            </div>
            <button class="xb-icon-button" type="button" title="Close" @click="closeReceiptSheet">
              <X :size="18" />
            </button>
          </header>
          <div class="xb-receipt-sheet-summary">
            <span>{{ formatMoney(receiptSheet) }}</span>
            <span>{{ receiptStatusLabel(receiptSheet) }}</span>
            <span>{{ receiptSheet.warranty_until ? `Warranty ${receiptSheet.warranty_until}` : 'No warranty' }}</span>
          </div>
          <div class="xb-receipt-sheet-actions">
            <button class="xb-secondary-button" type="button" @click="loadOcrReview(receiptSheet)">
              <FileImage :size="17" />
              Review details
            </button>
            <button v-if="receiptSheet.ocr_status === 'not_started'" class="xb-secondary-button" type="button" @click="startOcr(receiptSheet)">
              <FileSearch :size="17" />
              Run OCR
            </button>
            <button v-else class="xb-secondary-button" type="button" @click="loadOcrReview(receiptSheet)">
              <FileSearch :size="17" />
              OCR result
            </button>
            <button class="xb-secondary-button" type="button" @click="startEdit(receiptSheet)">
              <ReceiptText :size="17" />
              Edit fields
            </button>
            <button class="xb-secondary-button" type="button" @click="downloadOriginal(receiptSheet)">
              <Download :size="17" />
              Original
            </button>
            <button class="xb-secondary-button xb-danger-button" type="button" @click="deleteReceipt(receiptSheet)">
              <Trash2 :size="17" />
              Delete
            </button>
          </div>
        </aside>
      </section>

      <section v-if="ocrReview" class="xb-modal-backdrop xb-receipt-review-backdrop" @click.self="closeOcrReview">
        <form class="xb-modal xb-receipt-review-modal" @submit.prevent="confirmOcr">
          <div class="xb-receipt-review-head">
            <h3>Receipt capture</h3>
            <div class="xb-row-actions">
              <button class="xb-secondary-button" type="button" @click="downloadOriginal(ocrReview.receipt)">
                <Download :size="17" />
                Original
              </button>
              <button class="xb-icon-button" type="button" title="Close" @click="closeOcrReview">
                <X :size="18" />
              </button>
            </div>
          </div>
          <div class="xb-receipt-review-grid">
            <aside class="xb-receipt-preview">
              <span v-if="activePreview.loading">Loading preview...</span>
              <span v-else-if="activePreview.error">{{ activePreview.error }}</span>
              <img v-else-if="activePreview.type.startsWith('image/')" :src="activePreview.url" alt="Receipt preview" />
              <iframe v-else-if="activePreview.type === 'application/pdf'" :src="activePreview.url" title="Receipt preview"></iframe>
              <span v-else>Preview is available as original download.</span>
            </aside>
            <section class="xb-receipt-review-fields">
              <p v-if="ocrReview.error_message" class="xb-form-error">{{ ocrReview.error_message }}</p>
              <label>Merchant <input v-model="ocrReview.merchant" /></label>
              <label>Category <input v-model="ocrReview.category" /></label>
              <div class="xb-two-column-fields">
                <label>Amount <input v-model="ocrReview.amount" type="number" step="0.01" /></label>
                <label>Currency <input v-model="ocrReview.currency" maxlength="8" /></label>
              </div>
              <div class="xb-two-column-fields">
                <label>Purchase date <input v-model="ocrReview.purchase_date" type="date" /></label>
                <label>Warranty until <input v-model="ocrReview.warranty_until" type="date" /></label>
              </div>
              <label>Notes <textarea v-model="ocrReview.notes" rows="3"></textarea></label>
              <section class="xb-ocr-raw-panel">
                <button class="xb-secondary-button" type="button" @click="rawTextOpen = !rawTextOpen">
                  <FileSearch :size="16" />
                  {{ rawTextOpen ? 'Hide OCR text' : 'Show OCR text' }}
                </button>
                <label v-if="rawTextOpen">Raw OCR text <textarea v-model="ocrReview.raw_text" rows="5" readonly></textarea></label>
              </section>
            </section>
          </div>
          <div class="xb-row-actions">
            <button v-if="ocrReview.task && (ocrReview.task.status === 'completed' || ocrReview.task.status === 'confirmed')" class="xb-primary-button" type="submit">
              <Save :size="17" />
              Confirm
            </button>
            <button v-if="ocrReview.task && !['pending', 'processing'].includes(ocrReview.task.status)" class="xb-secondary-button" type="button" @click="retryOcr">
              <RotateCcw :size="17" />
              Re-run OCR
            </button>
            <button class="xb-secondary-button" type="button" @click="closeOcrReview">Close</button>
          </div>
        </form>
      </section>
    </Teleport>
  </div>
</template>
