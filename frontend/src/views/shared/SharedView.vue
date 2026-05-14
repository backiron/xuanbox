<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Archive, Check, Copy, FileText, Image, Link, LockKeyhole, RefreshCw, ReceiptText, Shield, Trash2, UserRound, X } from 'lucide-vue-next'

import PageHeader from '../../components/common/PageHeader.vue'
import EmptyState from '../../components/common/EmptyState.vue'
import { fileApi } from '../../api/fileApi'
import { photoApi } from '../../api/photoApi'
import { receiptApi } from '../../api/receiptApi'
import { shareApi } from '../../api/shareApi'

const route = useRoute()
const { t } = useI18n()
const activeTab = ref('created')
const shareMode = ref('public')
const targetType = ref('file')
const createdShares = ref([])
const receivedShares = ref([])
const archivedShares = ref([])
const files = ref([])
const photos = ref([])
const receipts = ref([])
const loading = ref(false)
const creating = ref(false)
const copiedId = ref(null)
const error = ref('')
const success = ref('')
const shareQueueKeys = ref([])

const form = reactive({
  target_key: '',
  shared_with_username: '',
  permission: 'download',
  password: '',
  max_downloads: '3',
  expires_at: defaultExpiry()
})

const targetTypes = [
  { value: 'file', labelKey: 'pages.shared.targetTypeFile', icon: FileText },
  { value: 'photo', labelKey: 'pages.shared.targetTypePhoto', icon: Image },
  { value: 'receipt', labelKey: 'pages.shared.targetTypeReceipt', icon: ReceiptText }
]

function permissionLabel(value) {
  return value === 'read' ? t('pages.shared.downloadText') : t('pages.shared.download')
}

function defaultExpiry() {
  const value = new Date()
  value.setDate(value.getDate() + 7)
  value.setMinutes(value.getMinutes() - value.getTimezoneOffset())
  return value.toISOString().slice(0, 16)
}

const visibleShares = computed(() => {
  if (activeTab.value === 'received') return receivedShares.value
  if (activeTab.value === 'archived') return archivedShares.value
  return createdShares.value
})
const targetOptions = computed(() => {
  if (targetType.value === 'photo') {
    return photos.value.map((photo) => ({
      key: `photo:${photo.id}`,
      id: photo.id,
      type: 'photo',
      label: photoLabel(photo),
      meta: [photo.width && photo.height ? `${photo.width} x ${photo.height}` : null, formatDate(photo.uploaded_at)].filter(Boolean).join(' · '),
      thumbUrl: photo.thumbUrl
    }))
  }
  if (targetType.value === 'receipt') {
    return receipts.value.map((receipt) => ({
      key: `receipt:${receipt.id}`,
      id: receipt.id,
      type: 'receipt',
      label: receipt.merchant || 'Receipt',
      meta: [receipt.category, receipt.amount ? `${receipt.currency} ${receipt.amount}` : null].filter(Boolean).join(' · ')
    }))
  }
  return files.value.map((file) => ({
    key: `file:${file.id}`,
    id: file.id,
    type: 'file',
    label: file.display_name,
    meta: `${file.file_category} · ${formatSize(file.file_size)}`
  }))
})
const selectedTargets = computed(() => {
  const keys = shareQueueKeys.value.length ? shareQueueKeys.value : [form.target_key]
  return keys.map((key) => targetOptions.value.find((target) => target.key === key)).filter(Boolean)
})
const inactiveShareCount = computed(() => createdShares.value.filter((share) => statusFor(share) !== 'Active').length)

function photoLabel(photo) {
  return `${t('pages.shared.targetTypePhoto')} ${formatDate(photo.taken_at || photo.uploaded_at)}`
}

function formatSize(bytes) {
  if (!bytes) return '0 KB'
  if (bytes < 1024 * 1024) return `${Math.ceil(bytes / 1024)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

function formatDate(value) {
  if (!value) return t('common.file.noExpiry')
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))
}

function shareUrl(share) {
  return `${window.location.origin}/public-share/${share.public_token}`
}

function selectedTarget() {
  return targetOptions.value.find((target) => target.key === form.target_key)
}

function applyRouteSelection() {
  if (route.query.type !== 'photo' || !route.query.ids) return
  targetType.value = 'photo'
  const ids = String(route.query.ids).split(',').map((id) => id.trim()).filter(Boolean)
  shareQueueKeys.value = ids.map((id) => `photo:${id}`)
}

function applyDefaultTarget() {
  const options = targetOptions.value
  if (shareQueueKeys.value.length) {
    shareQueueKeys.value = shareQueueKeys.value.filter((key) => options.some((target) => target.key === key))
    form.target_key = shareQueueKeys.value[0] || options[0]?.key || ''
    return
  }
  if (!options.some((target) => target.key === form.target_key)) {
    form.target_key = options[0]?.key || ''
  }
}

function setTargetType(type) {
  targetType.value = type
  form.target_key = ''
  shareQueueKeys.value = []
  applyDefaultTarget()
}

function selectPhotoTarget(target) {
  form.target_key = target.key
  shareQueueKeys.value = [target.key]
}

function removeQueuedTarget(key) {
  shareQueueKeys.value = shareQueueKeys.value.filter((item) => item !== key)
  form.target_key = shareQueueKeys.value[0] || targetOptions.value[0]?.key || ''
}

function setShareMode(mode) {
  shareMode.value = mode
  if (mode === 'public') {
    if (!form.max_downloads) form.max_downloads = '3'
    if (!form.expires_at) form.expires_at = defaultExpiry()
  }
}

function statusFor(share) {
  if (!share.is_active) return 'Inactive'
  if (share.expires_at && new Date(share.expires_at) <= new Date()) return 'Expired'
  if (share.max_downloads && share.download_count >= share.max_downloads) return 'Limit reached'
  return 'Active'
}

function statusLabel(share) {
  const status = statusFor(share)
  if (status === 'Active') return t('pages.shared.statusActive')
  if (status === 'Expired') return t('pages.shared.statusExpired')
  if (status === 'Limit reached') return t('pages.shared.statusLimitReached')
  return t('pages.shared.statusInactive')
}

function shareMeta(share) {
  const limit = share.max_downloads ? `${share.download_count} / ${share.max_downloads}` : `${share.download_count} / unlimited`
  return `${share.target_type} · ${permissionLabel(share.permission)} · ${limit} ${t('pages.shared.downloads')}`
}

async function hydratePhotoThumbs(rows) {
  return Promise.all(rows.map(async (photo) => {
    try {
      const response = await photoApi.thumbnailBlob(photo.id)
      return { ...photo, thumbUrl: URL.createObjectURL(response.data) }
    } catch {
      return photo
    }
  }))
}

async function loadAll() {
  loading.value = true
  error.value = ''
  try {
    const [created, received, archived, fileResponse, photoResponse, receiptResponse] = await Promise.all([
      shareApi.list('created'),
      shareApi.list('received'),
      shareApi.list('archived'),
      fileApi.list(),
      photoApi.list(),
      receiptApi.list()
    ])
    for (const photo of photos.value) {
      if (photo.thumbUrl) URL.revokeObjectURL(photo.thumbUrl)
    }
    createdShares.value = created.data.data
    receivedShares.value = received.data.data
    archivedShares.value = archived.data.data
    files.value = fileResponse.data.data
    photos.value = await hydratePhotoThumbs(photoResponse.data.data)
    receipts.value = receiptResponse.data.data
    applyRouteSelection()
    applyDefaultTarget()
  } catch (err) {
    error.value = err.response?.data?.error?.message || t('pages.shared.loadError')
  } finally {
    loading.value = false
  }
}

async function createShare() {
  const targets = selectedTargets.value
  if (!targets.length) return
  error.value = ''
  success.value = ''
  creating.value = true
  try {
    const payloadBase = {
      permission: form.permission,
      shared_with_username: shareMode.value === 'user' ? form.shared_with_username || null : null,
      password: form.password || null,
      max_downloads: form.max_downloads ? Number(form.max_downloads) : null,
      expires_at: form.expires_at ? new Date(form.expires_at).toISOString() : null
    }
    const responses = []
    for (const target of targets) {
      responses.push(await shareApi.create({ ...payloadBase, target_type: target.type, target_id: target.id }))
    }
    form.password = ''
    if (shareMode.value !== 'user') form.shared_with_username = ''
    success.value = targets.length > 1 ? t('pages.shared.sharesCreated', { count: targets.length }) : (shareMode.value === 'user' ? t('pages.shared.userCreated') : t('pages.shared.publicCreated'))
    await loadAll()
    await copyShare(responses[0].data.data)
  } catch (err) {
    error.value = err.response?.data?.error?.message || t('pages.shared.createError')
  } finally {
    creating.value = false
  }
}

async function copyShare(share) {
  await navigator.clipboard.writeText(shareUrl(share))
  copiedId.value = share.id
  window.setTimeout(() => {
    if (copiedId.value === share.id) copiedId.value = null
  }, 1600)
}

async function cancelShare(share) {
  await shareApi.remove(share.id)
  await loadAll()
}

async function archiveShare(share) {
  await shareApi.archive(share.id)
  await loadAll()
}

async function archiveInactiveShares() {
  if (!inactiveShareCount.value) return
  const response = await shareApi.archiveInactive()
  success.value = t('pages.shared.archivedCount', { count: response.data.data.count })
  await loadAll()
}

onMounted(loadAll)
onBeforeUnmount(() => {
  for (const photo of photos.value) {
    if (photo.thumbUrl) URL.revokeObjectURL(photo.thumbUrl)
  }
})
</script>

<template>
  <PageHeader :title="t('pages.shared.title')" :subtitle="t('pages.shared.subtitle')">
    <button class="xb-secondary-button" type="button" @click="loadAll">
      <RefreshCw :size="16" />
      {{ t('common.actions.refresh') }}
    </button>
  </PageHeader>

  <section class="xb-shared-layout">
    <form class="xb-panel xb-share-form xb-share-builder" @submit.prevent="createShare">
      <div class="xb-share-form-head">
        <Shield :size="22" />
        <div>
          <h3>{{ t('pages.shared.createTitle') }}</h3>
          <p>{{ t('pages.shared.createDesc') }}</p>
        </div>
      </div>

      <div class="xb-share-mode">
        <button type="button" :class="{ 'is-active': shareMode === 'public' }" @click="setShareMode('public')">
          <Link :size="16" />
          {{ t('pages.shared.publicLink') }}
        </button>
        <button type="button" :class="{ 'is-active': shareMode === 'user' }" @click="setShareMode('user')">
          <UserRound :size="16" />
          {{ t('pages.shared.userLink') }}
        </button>
      </div>

      <div class="xb-share-target-tabs">
        <button v-for="type in targetTypes" :key="type.value" type="button" :class="{ 'is-active': targetType === type.value }" @click="setTargetType(type.value)">
          <component :is="type.icon" :size="16" />
          {{ t(type.labelKey) }}
        </button>
      </div>

      <label>
        {{ t('pages.shared.item') }}
        <select v-if="targetType !== 'photo'" v-model="form.target_key">
          <option v-for="target in targetOptions" :key="target.key" :value="target.key">
            {{ target.label }}{{ target.meta ? ` · ${target.meta}` : '' }}
          </option>
        </select>
      </label>

      <div v-if="targetType === 'photo'" class="xb-share-photo-picker">
        <button v-for="target in targetOptions" :key="target.key" type="button" :class="{ 'is-active': shareQueueKeys.includes(target.key) || form.target_key === target.key }" @click="selectPhotoTarget(target)">
          <img v-if="target.thumbUrl" :src="target.thumbUrl" alt="" />
          <Image v-else :size="16" />
          <span>{{ target.meta }}</span>
        </button>
      </div>

      <div v-if="selectedTargets.length > 1" class="xb-share-selected-list">
        <article v-for="target in selectedTargets" :key="target.key">
          <img v-if="target.thumbUrl" :src="target.thumbUrl" alt="" />
          <div>
            <strong>{{ target.label }}</strong>
            <span>{{ target.meta }}</span>
          </div>
          <button type="button" title="Remove" @click="removeQueuedTarget(target.key)">
            <X :size="14" />
          </button>
        </article>
      </div>

      <div v-else-if="selectedTarget()" class="xb-share-selected" :class="{ 'has-thumb': selectedTarget().thumbUrl }">
        <img v-if="selectedTarget().thumbUrl" :src="selectedTarget().thumbUrl" alt="" />
        <strong>{{ selectedTarget().label }}</strong>
        <span>{{ selectedTarget().meta || selectedTarget().type }}</span>
      </div>

      <label>
        {{ t('pages.shared.permission') }}
        <select v-model="form.permission">
          <option value="download">{{ t('pages.shared.download') }}</option>
          <option value="read">{{ t('pages.shared.downloadText') }}</option>
        </select>
      </label>

      <label v-if="shareMode === 'user'">
        {{ t('pages.shared.shareWithUser') }}
        <input v-model.trim="form.shared_with_username" :placeholder="t('common.placeholders.usernameOrEmail')" />
      </label>

      <div class="xb-share-form-grid">
        <label>
          {{ t('pages.shared.withPassword') }}
          <input v-model="form.password" type="password" :placeholder="t('common.placeholders.optional')" />
        </label>
        <label>
          {{ t('pages.shared.maxDownloads') }}
          <input v-model="form.max_downloads" min="1" type="number" :placeholder="t('common.states.unlimited')" />
        </label>
      </div>

      <label>
        {{ t('pages.shared.expires') }}
        <input v-model="form.expires_at" type="datetime-local" />
      </label>

      <div class="xb-share-security-note">
        <LockKeyhole :size="16" />
        <span>{{ shareMode === 'public' ? t('pages.shared.publicSecurityNote') : t('pages.shared.userSecurityNote') }}</span>
      </div>

      <button class="xb-primary-button" type="submit" :disabled="creating || !selectedTargets.length || (shareMode === 'user' && !form.shared_with_username)">
        <LockKeyhole :size="16" />
        {{ creating ? t('pages.shared.creating') : (selectedTargets.length > 1 ? t('pages.shared.createLinks', { count: selectedTargets.length }) : t('pages.shared.createAndCopy')) }}
      </button>
      <p v-if="success" class="xb-form-success">{{ success }}</p>
      <p v-if="error" class="xb-form-error">{{ error }}</p>
    </form>

    <section class="xb-share-results">
      <div class="xb-tabs xb-share-tabs">
        <button type="button" :class="{ 'is-active': activeTab === 'created' }" @click="activeTab = 'created'">{{ t('pages.shared.myShares') }}</button>
        <button type="button" :class="{ 'is-active': activeTab === 'received' }" @click="activeTab = 'received'">{{ t('pages.shared.received') }}</button>
        <button type="button" :class="{ 'is-active': activeTab === 'archived' }" @click="activeTab = 'archived'">{{ t('pages.shared.archived') }}</button>
      </div>

      <button v-if="activeTab === 'created' && inactiveShareCount" class="xb-secondary-button xb-share-archive-all" type="button" @click="archiveInactiveShares">
        <Archive :size="16" />
        {{ t('pages.shared.archiveInactive') }}
      </button>

      <EmptyState v-if="!loading && visibleShares.length === 0" :title="t('pages.shared.noShares')" :description="t('pages.shared.noSharesDesc')" />

      <div v-else class="xb-share-list">
        <article v-for="share in visibleShares" :key="share.id" class="xb-share-card" :class="{ 'is-inactive': statusFor(share) !== 'Active' }">
          <div class="xb-share-card-main">
            <Link :size="20" />
            <div>
              <strong>{{ share.target_name || share.target_id }}</strong>
              <span>{{ shareMeta(share) }}</span>
              <small>{{ formatDate(share.expires_at) }}</small>
            </div>
          </div>
          <div class="xb-share-card-side">
            <span class="xb-share-status" :class="{ 'is-active': statusFor(share) === 'Active' }">{{ statusLabel(share) }}</span>
            <div class="xb-row-actions">
              <button class="xb-text-button" type="button" @click="copyShare(share)">
                <component :is="copiedId === share.id ? Check : Copy" :size="16" />
                {{ copiedId === share.id ? t('pages.shared.copied') : t('pages.shared.copyLink') }}
              </button>
              <button v-if="activeTab === 'created' && share.is_active" class="xb-text-button xb-danger-button" type="button" @click="cancelShare(share)">
                <Trash2 :size="16" />
                {{ t('pages.shared.cancel') }}
              </button>
              <button v-if="activeTab === 'created' && statusFor(share) !== 'Active'" class="xb-text-button" type="button" @click="archiveShare(share)">
                <Archive :size="16" />
                {{ t('pages.shared.archive') }}
              </button>
            </div>
          </div>
        </article>
      </div>
    </section>
  </section>
</template>
