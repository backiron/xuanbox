<script setup>
import { onMounted, ref } from 'vue'
import { Download, FileLock2, Filter, Save, Search, ShieldAlert, Upload } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'

import PageHeader from '../../components/common/PageHeader.vue'
import EmptyState from '../../components/common/EmptyState.vue'
import { documentApi } from '../../api/documentApi'
import { useDialogStore } from '../../stores/dialogStore'
import { findUploadLimitError } from '../../utils/uploadLimits'

const documents = ref([])
const loading = ref(false)
const uploadProgress = ref(0)
const draggingDocuments = ref(false)
const filters = ref({ q: '', document_type: '', security_level: '' })
const editing = ref(null)
const error = ref('')
const dialog = useDialogStore()
const { t } = useI18n()
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

function titleFromFile(file) {
  return file.name.replace(/\.[^/.]+$/, '') || 'Document'
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

async function uploadDocumentFiles(files) {
  const pickedFiles = Array.from(files || [])
  if (!pickedFiles.length) return
  const limitError = findUploadLimitError(pickedFiles, t)
  if (limitError) {
    error.value = limitError
    return
  }
  uploadProgress.value = 1
  for (const file of pickedFiles) {
    const payload = cleanPayload({
      ...draft.value,
      title: draft.value.title || titleFromFile(file)
    })
    const formData = new FormData()
    formData.append('file', file)
    for (const [key, value] of Object.entries(payload)) {
      if (value !== null) formData.append(key, value)
    }
    await documentApi.upload(formData, {
      onUploadProgress(progressEvent) {
        if (progressEvent.total) uploadProgress.value = Math.round((progressEvent.loaded / progressEvent.total) * 100)
      }
    })
  }
  uploadProgress.value = 0
  draft.value = { document_type: 'contract', title: '', issuer: '', issued_date: '', expires_at: '', security_level: 'normal', note: '' }
  await loadDocuments()
}

async function onDocumentFile(event) {
  await uploadDocumentFiles(event.target.files)
  event.target.value = ''
}

function onDragEnter(event) {
  if (!event.dataTransfer?.types?.includes('Files')) return
  draggingDocuments.value = true
}

function onDragLeave(event) {
  if (event.currentTarget.contains(event.relatedTarget)) return
  draggingDocuments.value = false
}

async function onDocumentDrop(event) {
  draggingDocuments.value = false
  await uploadDocumentFiles(event.dataTransfer?.files)
}

function startEdit(document) {
  editing.value = { ...document }
}

async function saveEdit() {
  await documentApi.update(editing.value.id, cleanPayload(editing.value))
  editing.value = null
  await loadDocuments()
}

async function downloadDocument(item) {
  let password = ''
  if (item.security_level === 'high_sensitive' || item.security_level === 'vault_locked') {
    password = await dialog.prompt({ title: t('pages.documents.passwordRequired'), label: t('pages.documents.accountPassword'), inputType: 'password' }) || ''
    if (!password) return
  }
  const response = await documentApi.download(item.id, password)
  const blobUrl = URL.createObjectURL(response.data)
  const anchor = window.document.createElement('a')
  anchor.href = blobUrl
  anchor.download = item.title
  anchor.click()
  URL.revokeObjectURL(blobUrl)
  await loadDocuments()
}

onMounted(loadDocuments)
</script>

<template>
  <div
    class="xb-upload-page"
    :class="{ 'is-dragging': draggingDocuments }"
    @dragenter.prevent="onDragEnter"
    @dragover.prevent="draggingDocuments = true"
    @dragleave="onDragLeave"
    @drop.prevent="onDocumentDrop"
  >
  <PageHeader :title="t('pages.documents.title')" :subtitle="t('pages.documents.subtitle')">
    <label class="xb-upload-button">
      <Upload :size="18" />
      {{ t('pages.documents.uploadDocument') }}
      <input type="file" accept="image/*,.pdf,.doc,.docx,.txt" multiple @change="onDocumentFile" />
    </label>
  </PageHeader>

  <div v-if="uploadProgress" class="xb-progress">
    <span :style="{ width: `${uploadProgress}%` }"></span>
  </div>

  <section class="xb-upload-drop-hint" :class="{ 'is-visible': draggingDocuments }">
    <Upload :size="18" />
    <strong>{{ t('pages.documents.dropLabel') }}</strong>
    <span>{{ draft.title ? t('pages.documents.dropWithDetails') : t('pages.documents.dropWithoutDetails') }}</span>
  </section>

  <section class="xb-document-layout">
    <aside class="xb-panel xb-document-form">
      <h3>{{ t('pages.documents.detailsTitle') }}</h3>
      <label>{{ t('pages.documents.titleLabel') }} <input v-model.trim="draft.title" :placeholder="t('pages.documents.titlePlaceholder')" /></label>
      <label>
        {{ t('pages.documents.type') }}
        <select v-model="draft.document_type">
          <option v-for="[value, label] in documentTypes" :key="value" :value="value">{{ label }}</option>
        </select>
      </label>
      <label>{{ t('pages.documents.issuer') }} <input v-model.trim="draft.issuer" :placeholder="t('pages.documents.issuerPlaceholder')" /></label>
      <label>{{ t('pages.documents.issuedDate') }} <input v-model="draft.issued_date" type="date" /></label>
      <label>{{ t('pages.documents.expiresAt') }} <input v-model="draft.expires_at" type="date" /></label>
      <label>
        {{ t('pages.documents.security') }}
        <select v-model="draft.security_level">
          <option v-for="[value, label] in securityLevels" :key="value" :value="value">{{ label }}</option>
        </select>
      </label>
      <label>{{ t('pages.documents.note') }} <textarea v-model="draft.note" rows="4"></textarea></label>
    </aside>

    <section>
      <div class="xb-filter-bar xb-document-filter-bar">
        <div class="xb-filter-field">
          <Search :size="16" />
          <input v-model="filters.q" :placeholder="t('pages.documents.placeholderSearch')" @keyup.enter="loadDocuments" />
        </div>
        <div class="xb-filter-field">
          <Filter :size="16" />
          <input v-model="filters.document_type" :placeholder="t('pages.documents.type')" @keyup.enter="loadDocuments" />
        </div>
        <div class="xb-filter-field">
          <ShieldAlert :size="16" />
          <input v-model="filters.security_level" :placeholder="t('pages.documents.security')" @keyup.enter="loadDocuments" />
        </div>
        <button class="xb-secondary-button" type="button" @click="loadDocuments">{{ t('pages.documents.apply') }}</button>
      </div>

      <p v-if="error" class="xb-form-error">{{ error }}</p>
      <EmptyState v-if="!loading && documents.length === 0" :title="t('pages.documents.noData')" :description="t('pages.documents.noDataHint')" />

      <div v-else class="xb-document-grid">
        <article v-for="item in documents" :key="item.id" class="xb-document-card" :class="`level-${item.security_level}`">
          <div class="xb-document-card-head">
            <FileLock2 :size="20" />
            <span>{{ levelLabel(item.security_level) }}</span>
          </div>
          <h3>{{ item.title }}</h3>
          <p>{{ item.issuer || t('pages.documents.noIssuer') }}</p>
          <div class="xb-document-meta">
            <span>{{ item.document_type }}</span>
            <strong v-if="item.expires_at">{{ daysUntil(item.expires_at) }} days</strong>
            <span v-else>{{ t('common.file.noExpiry') }}</span>
          </div>
          <small>{{ item.expires_at ? t('pages.documents.expiresValue', { date: item.expires_at }) : t('pages.documents.noReminderDate') }}</small>
          <div class="xb-row-actions">
            <button class="xb-text-button" type="button" @click="downloadDocument(item)">
              <Download :size="16" />
              {{ t('common.actions.download') }}
            </button>
            <button class="xb-text-button" type="button" @click="startEdit(item)">{{ t('common.actions.edit') }}</button>
          </div>
        </article>
      </div>
    </section>
  </section>

  <section v-if="editing" class="xb-modal-backdrop" @click.self="editing = null">
    <form class="xb-modal" @submit.prevent="saveEdit">
      <h3>{{ t('pages.documents.editTitle') }}</h3>
      <label>{{ t('pages.documents.titleLabel') }} <input v-model="editing.title" /></label>
      <label>
        {{ t('pages.documents.type') }}
        <select v-model="editing.document_type">
          <option v-for="[value, label] in documentTypes" :key="value" :value="value">{{ label }}</option>
        </select>
      </label>
      <label>{{ t('pages.documents.issuer') }} <input v-model="editing.issuer" /></label>
      <label>{{ t('pages.documents.issuedDate') }} <input v-model="editing.issued_date" type="date" /></label>
      <label>{{ t('pages.documents.expiresAt') }} <input v-model="editing.expires_at" type="date" /></label>
      <label>
        {{ t('pages.documents.security') }}
        <select v-model="editing.security_level">
          <option v-for="[value, label] in securityLevels" :key="value" :value="value">{{ label }}</option>
        </select>
      </label>
      <label>{{ t('pages.documents.note') }} <textarea v-model="editing.note" rows="4"></textarea></label>
      <div class="xb-row-actions">
        <button class="xb-primary-button" type="submit">
          <Save :size="17" />
          {{ t('common.actions.save') }}
        </button>
        <button class="xb-secondary-button" type="button" @click="editing = null">{{ t('common.actions.cancel') }}</button>
      </div>
    </form>
  </section>
  </div>
</template>
