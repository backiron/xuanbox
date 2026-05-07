<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { Check, Copy, Link, RefreshCw, Trash2 } from 'lucide-vue-next'

import PageHeader from '../../components/common/PageHeader.vue'
import EmptyState from '../../components/common/EmptyState.vue'
import { fileApi } from '../../api/fileApi'
import { shareApi } from '../../api/shareApi'

const activeTab = ref('created')
const createdShares = ref([])
const receivedShares = ref([])
const files = ref([])
const loading = ref(false)
const copiedId = ref(null)
const error = ref('')

const form = reactive({
  target_type: 'file',
  target_id: '',
  shared_with_username: '',
  permission: 'download',
  password: '',
  max_downloads: '',
  expires_at: ''
})

const visibleShares = computed(() => (activeTab.value === 'created' ? createdShares.value : receivedShares.value))

function shareUrl(share) {
  return `${window.location.origin}/public-share/${share.public_token}`
}

async function loadAll() {
  loading.value = true
  error.value = ''
  try {
    const [created, received, fileResponse] = await Promise.all([
      shareApi.list('created'),
      shareApi.list('received'),
      fileApi.list()
    ])
    createdShares.value = created.data.data
    receivedShares.value = received.data.data
    files.value = fileResponse.data.data
    if (!form.target_id && files.value.length) form.target_id = files.value[0].id
  } catch (err) {
    error.value = err.response?.data?.error?.message || 'Unable to load shares'
  } finally {
    loading.value = false
  }
}

async function createShare() {
  if (!form.target_id) return
  error.value = ''
  try {
    const payload = {
      target_type: form.target_type,
      target_id: form.target_id,
      permission: form.permission,
      shared_with_username: form.shared_with_username || null,
      password: form.password || null,
      max_downloads: form.max_downloads ? Number(form.max_downloads) : null,
      expires_at: form.expires_at ? new Date(form.expires_at).toISOString() : null
    }
    await shareApi.create(payload)
    form.password = ''
    await loadAll()
  } catch (err) {
    error.value = err.response?.data?.error?.message || 'Unable to create share'
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

function formatDate(value) {
  if (!value) return 'No expiry'
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))
}

onMounted(loadAll)
</script>

<template>
  <PageHeader title="Shared" subtitle="Create temporary links, review access limits, and cancel shares when they are no longer needed.">
    <button class="xb-secondary-button" type="button" @click="loadAll">
      <RefreshCw :size="16" />
      Refresh
    </button>
  </PageHeader>

  <section class="xb-shared-layout">
    <form class="xb-panel xb-share-form" @submit.prevent="createShare">
      <h3>Create share</h3>
      <label>
        Target
        <select v-model="form.target_id">
          <option v-for="file in files" :key="file.id" :value="file.id">{{ file.display_name }}</option>
        </select>
      </label>
      <label>
        Permission
        <select v-model="form.permission">
          <option value="download">Download</option>
          <option value="read">Read</option>
        </select>
      </label>
      <label>
        Share with user
        <input v-model.trim="form.shared_with_username" placeholder="username or email" />
      </label>
      <label>
        Password
        <input v-model="form.password" type="password" placeholder="optional" />
      </label>
      <div class="xb-share-form-grid">
        <label>
          Max downloads
          <input v-model="form.max_downloads" min="1" type="number" placeholder="optional" />
        </label>
        <label>
          Expires
          <input v-model="form.expires_at" type="datetime-local" />
        </label>
      </div>
      <button class="xb-primary-button" type="submit" :disabled="!form.target_id">Create link</button>
      <p v-if="error" class="xb-form-error">{{ error }}</p>
    </form>

    <section>
      <div class="xb-tabs">
        <button type="button" :class="{ 'is-active': activeTab === 'created' }" @click="activeTab = 'created'">My shares</button>
        <button type="button" :class="{ 'is-active': activeTab === 'received' }" @click="activeTab = 'received'">Shared with me</button>
      </div>

      <EmptyState v-if="!loading && visibleShares.length === 0" title="No shares yet" description="Create a link for a file when you are ready to send it." />

      <div v-else class="xb-share-list">
        <article v-for="share in visibleShares" :key="share.id" class="xb-share-card">
          <div class="xb-share-card-main">
            <Link :size="20" />
            <div>
              <strong>{{ share.target_name || share.target_id }}</strong>
              <span>{{ share.target_type }} · {{ share.permission }} · {{ share.download_count }} / {{ share.max_downloads || '∞' }} downloads</span>
              <small>{{ formatDate(share.expires_at) }}</small>
            </div>
          </div>
          <div class="xb-row-actions">
            <button class="xb-text-button" type="button" @click="copyShare(share)">
              <component :is="copiedId === share.id ? Check : Copy" :size="16" />
              {{ copiedId === share.id ? 'Copied' : 'Copy link' }}
            </button>
            <button v-if="activeTab === 'created' && share.is_active" class="xb-text-button xb-danger-button" type="button" @click="cancelShare(share)">
              <Trash2 :size="16" />
              Cancel
            </button>
            <span v-if="!share.is_active" class="xb-share-status">Inactive</span>
          </div>
        </article>
      </div>
    </section>
  </section>
</template>
