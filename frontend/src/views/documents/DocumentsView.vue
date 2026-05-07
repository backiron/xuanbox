<script setup>
import { onMounted, ref } from 'vue'
import { Download, FileLock2, Filter, Save, Search, ShieldAlert, Upload } from 'lucide-vue-next'

import PageHeader from '../../components/common/PageHeader.vue'
import EmptyState from '../../components/common/EmptyState.vue'
import { documentApi } from '../../api/documentApi'

const documents = ref([])
const loading = ref(false)
const uploadProgress = ref(0)
const filters = ref({ q: '', document_type: '', security_level: '' })
const editing = ref(null)
const error = ref('')
const draft = ref({
  document_type: 'contract',
  title: '',
  issuer: '',
  issued_date: '',
  expires_at: '',
  security_level: 'normal',
  note: ''
})

const documentTypes = [
  ['identity', 'Identity'],
  ['passport', 'Passport'],
  ['driver_license', 'Driver license'],
  ['visa', 'Visa'],
  ['pr_card', 'PR card'],
  ['insurance', 'Insurance'],
  ['tax', 'Tax'],
  ['bank', 'Bank'],
  ['contract', 'Contract'],
  ['home', 'Home'],
  ['vehicle', 'Vehicle'],
  ['medical', 'Medical'],
  ['school', 'School'],
  ['software_license', 'Software license'],
  ['other', 'Other']
]

const securityLevels = [
  ['normal', 'Normal'],
  ['sensitive', 'Sensitive'],
  ['high_sensitive', 'High sensitive'],
  ['vault_locked', 'Vault locked']
]

function cleanPayload(source) {
  return {
    document_type: source.document_type || 'other',
    title: source.title,
    issuer: source.issuer || null,
    issued_date: source.issued_date || null,
    expires_at: source.expires_at || null,
    security_level: source.security_level || 'normal',
    note: source.note || null
  }
}

function levelLabel(level) {
  return securityLevels.find(([value]) => value === level)?.[1] || level
}

function daysUntil(value) {
  if (!value) return null
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const expiry = new Date(value)
  expiry.setHours(0, 0, 0, 0)
  return Math.ceil((expiry - today) / 86400000)
}

async function loadDocuments() {
  loading.value = true
  error.value = ''
  try {
    const params = Object.fromEntries(Object.entries(filters.value).filter(([, value]) => value))
    const response = await documentApi.list(params)
    documents.value = response.data.data
  } catch (err) {
    error.value = err.response?.data?.error?.message || 'Unable to load documents'
  } finally {
    loading.value = false
  }
}

async function onDocumentFile(event) {
  const file = event.target.files?.[0]
  if (!file || !draft.value.title) return
  const formData = new FormData()
  formData.append('file', file)
  for (const [key, value] of Object.entries(cleanPayload(draft.value))) {
    if (value !== null) formData.append(key, value)
  }
  uploadProgress.value = 1
  await documentApi.upload(formData, {
    onUploadProgress(progressEvent) {
      if (progressEvent.total) uploadProgress.value = Math.round((progressEvent.loaded / progressEvent.total) * 100)
    }
  })
  uploadProgress.value = 0
  event.target.value = ''
  draft.value = { document_type: 'contract', title: '', issuer: '', issued_date: '', expires_at: '', security_level: 'normal', note: '' }
  await loadDocuments()
}

function startEdit(document) {
  editing.value = { ...document }
}

async function saveEdit() {
  await documentApi.update(editing.value.id, cleanPayload(editing.value))
  editing.value = null
  await loadDocuments()
}

async function downloadDocument(document) {
  let password = ''
  if (document.security_level === 'high_sensitive' || document.security_level === 'vault_locked') {
    password = window.prompt('Password required') || ''
    if (!password) return
  }
  const response = await documentApi.download(document.id, password)
  const blobUrl = URL.createObjectURL(response.data)
  const anchor = document.createElement('a')
  anchor.href = blobUrl
  anchor.download = document.title
  anchor.click()
  URL.revokeObjectURL(blobUrl)
  await loadDocuments()
}

onMounted(loadDocuments)
</script>

<template>
  <PageHeader title="Documents" subtitle="Save IDs, contracts, licenses, and other important documents with expiry reminders and security levels.">
    <label class="xb-upload-button" :class="{ 'is-disabled': !draft.title }">
      <Upload :size="18" />
      Upload Document
      <input type="file" accept="image/*,.pdf,.doc,.docx,.txt" :disabled="!draft.title" @change="onDocumentFile" />
    </label>
  </PageHeader>

  <div v-if="uploadProgress" class="xb-progress">
    <span :style="{ width: `${uploadProgress}%` }"></span>
  </div>

  <section class="xb-document-layout">
    <aside class="xb-panel xb-document-form">
      <h3>Document details</h3>
      <label>Title <input v-model.trim="draft.title" placeholder="Passport, lease, insurance policy" /></label>
      <label>
        Type
        <select v-model="draft.document_type">
          <option v-for="[value, label] in documentTypes" :key="value" :value="value">{{ label }}</option>
        </select>
      </label>
      <label>Issuer <input v-model.trim="draft.issuer" placeholder="Government, bank, school" /></label>
      <label>Issued date <input v-model="draft.issued_date" type="date" /></label>
      <label>Expires at <input v-model="draft.expires_at" type="date" /></label>
      <label>
        Security
        <select v-model="draft.security_level">
          <option v-for="[value, label] in securityLevels" :key="value" :value="value">{{ label }}</option>
        </select>
      </label>
      <label>Note <textarea v-model="draft.note" rows="4"></textarea></label>
    </aside>

    <section>
      <div class="xb-filter-bar xb-document-filter-bar">
        <div class="xb-filter-field">
          <Search :size="16" />
          <input v-model="filters.q" placeholder="Search documents" @keyup.enter="loadDocuments" />
        </div>
        <div class="xb-filter-field">
          <Filter :size="16" />
          <input v-model="filters.document_type" placeholder="Type" @keyup.enter="loadDocuments" />
        </div>
        <div class="xb-filter-field">
          <ShieldAlert :size="16" />
          <input v-model="filters.security_level" placeholder="Security" @keyup.enter="loadDocuments" />
        </div>
        <button class="xb-secondary-button" type="button" @click="loadDocuments">Apply</button>
      </div>

      <p v-if="error" class="xb-form-error">{{ error }}</p>
      <EmptyState v-if="!loading && documents.length === 0" title="No documents yet" description="Fill the details, then upload an encrypted ID, contract, or license." />

      <div v-else class="xb-document-grid">
        <article v-for="item in documents" :key="item.id" class="xb-document-card" :class="`level-${item.security_level}`">
          <div class="xb-document-card-head">
            <FileLock2 :size="20" />
            <span>{{ levelLabel(item.security_level) }}</span>
          </div>
          <h3>{{ item.title }}</h3>
          <p>{{ item.issuer || 'No issuer' }}</p>
          <div class="xb-document-meta">
            <span>{{ item.document_type }}</span>
            <strong v-if="item.expires_at">{{ daysUntil(item.expires_at) }} days</strong>
            <span v-else>No expiry</span>
          </div>
          <small>{{ item.expires_at ? `Expires ${item.expires_at}` : 'No reminder date' }}</small>
          <div class="xb-row-actions">
            <button class="xb-text-button" type="button" @click="downloadDocument(item)">
              <Download :size="16" />
              Download
            </button>
            <button class="xb-text-button" type="button" @click="startEdit(item)">Edit</button>
          </div>
        </article>
      </div>
    </section>
  </section>

  <section v-if="editing" class="xb-modal-backdrop" @click.self="editing = null">
    <form class="xb-modal" @submit.prevent="saveEdit">
      <h3>Edit document</h3>
      <label>Title <input v-model="editing.title" /></label>
      <label>
        Type
        <select v-model="editing.document_type">
          <option v-for="[value, label] in documentTypes" :key="value" :value="value">{{ label }}</option>
        </select>
      </label>
      <label>Issuer <input v-model="editing.issuer" /></label>
      <label>Issued date <input v-model="editing.issued_date" type="date" /></label>
      <label>Expires at <input v-model="editing.expires_at" type="date" /></label>
      <label>
        Security
        <select v-model="editing.security_level">
          <option v-for="[value, label] in securityLevels" :key="value" :value="value">{{ label }}</option>
        </select>
      </label>
      <label>Note <textarea v-model="editing.note" rows="4"></textarea></label>
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
