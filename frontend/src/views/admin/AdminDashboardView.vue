<script setup>
import { onMounted, ref } from 'vue'
import { Activity, Archive, DatabaseBackup, RefreshCw, Save, ShieldCheck, Users } from 'lucide-vue-next'

import PageHeader from '../../components/common/PageHeader.vue'
import { adminApi } from '../../api/adminApi'

const activeTab = ref('overview')
const loading = ref(false)
const error = ref('')
const bundle = ref({ overview: null, users: [], invites: [], audit_logs: [], backups: [] })
const editingUser = ref(null)

function formatBytes(value) {
  if (!value) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let size = value
  let unit = 0
  while (size >= 1024 && unit < units.length - 1) {
    size /= 1024
    unit += 1
  }
  return `${size.toFixed(unit < 2 ? 0 : 1)} ${units[unit]}`
}

async function loadAdmin() {
  loading.value = true
  error.value = ''
  try {
    const response = await adminApi.bundle()
    bundle.value = response.data.data
  } catch (err) {
    error.value = err.response?.data?.error?.message || 'Unable to load admin data'
  } finally {
    loading.value = false
  }
}

function startUserEdit(user) {
  editingUser.value = { ...user, storage_limit_bytes: user.storage_limit_bytes ?? '' }
}

async function saveUserEdit() {
  await adminApi.updateUser(editingUser.value.id, {
    role: editingUser.value.role,
    status: editingUser.value.status,
    storage_limit_bytes: editingUser.value.storage_limit_bytes === '' ? null : Number(editingUser.value.storage_limit_bytes)
  })
  editingUser.value = null
  await loadAdmin()
}

async function createBackup() {
  await adminApi.createBackup()
  await loadAdmin()
  activeTab.value = 'backups'
}

onMounted(loadAdmin)
</script>

<template>
  <PageHeader title="Admin" subtitle="System management without direct access to private user content.">
    <button class="xb-secondary-button" type="button" @click="loadAdmin">
      <RefreshCw :size="16" />
      Refresh
    </button>
  </PageHeader>

  <p v-if="error" class="xb-form-error">{{ error }}</p>

  <nav class="xb-tabs xb-admin-tabs">
    <button type="button" :class="{ 'is-active': activeTab === 'overview' }" @click="activeTab = 'overview'">Overview</button>
    <button type="button" :class="{ 'is-active': activeTab === 'users' }" @click="activeTab = 'users'">Users</button>
    <button type="button" :class="{ 'is-active': activeTab === 'invites' }" @click="activeTab = 'invites'">Invites</button>
    <button type="button" :class="{ 'is-active': activeTab === 'audit' }" @click="activeTab = 'audit'">Audit</button>
    <button type="button" :class="{ 'is-active': activeTab === 'backups' }" @click="activeTab = 'backups'">Backups</button>
  </nav>

  <section v-if="activeTab === 'overview'" class="xb-panel-grid">
    <article class="xb-panel">
      <Users :size="22" />
      <h3>{{ bundle.overview?.users_count || 0 }} users</h3>
      <p>{{ bundle.overview?.active_users_count || 0 }} active accounts</p>
    </article>
    <article class="xb-panel">
      <Archive :size="22" />
      <h3>{{ formatBytes(bundle.overview?.storage_bytes) }}</h3>
      <p>{{ bundle.overview?.today_uploads_count || 0 }} uploads today</p>
    </article>
    <article class="xb-panel">
      <Activity :size="22" />
      <h3>{{ bundle.overview?.error_count || 0 }} errors</h3>
      <p>Health: {{ bundle.overview?.service_status?.api || 'loading' }}</p>
    </article>
    <article class="xb-panel">
      <DatabaseBackup :size="22" />
      <h3>{{ bundle.overview?.latest_backup?.status || 'No backup' }}</h3>
      <p>{{ bundle.overview?.latest_backup?.created_at || 'Create a manual backup before server deployment.' }}</p>
    </article>
  </section>

  <section v-if="activeTab === 'users'" class="xb-panel">
    <div class="xb-admin-list">
      <article v-for="user in bundle.users" :key="user.id" class="xb-admin-row">
        <div>
          <strong>{{ user.username }}</strong>
          <span>{{ user.email }} · {{ user.role }} · {{ user.status }}</span>
        </div>
        <button class="xb-text-button" type="button" @click="startUserEdit(user)">Edit</button>
      </article>
    </div>
  </section>

  <section v-if="activeTab === 'invites'" class="xb-panel">
    <div class="xb-admin-list">
      <article v-for="invite in bundle.invites" :key="invite.id" class="xb-admin-row">
        <div>
          <strong>{{ invite.invite_code }}</strong>
          <span>{{ invite.role_to_assign }} · {{ invite.used_count }}/{{ invite.max_uses }} · {{ invite.is_active ? 'active' : 'inactive' }}</span>
        </div>
        <span>{{ invite.expires_at || 'No expiry' }}</span>
      </article>
    </div>
  </section>

  <section v-if="activeTab === 'audit'" class="xb-panel">
    <div class="xb-admin-list">
      <article v-for="log in bundle.audit_logs" :key="log.id" class="xb-admin-row">
        <div>
          <strong>{{ log.action }}</strong>
          <span>{{ log.target_type || 'system' }} · {{ log.target_id || 'none' }}</span>
        </div>
        <span>{{ log.created_at }}</span>
      </article>
    </div>
  </section>

  <section v-if="activeTab === 'backups'" class="xb-panel">
    <div class="xb-action-bar">
      <div>
        <strong>Migration backups</strong>
        <span>Database export, encrypted storage, safe config copy, and restore notes.</span>
      </div>
      <button class="xb-primary-button" type="button" :disabled="loading" @click="createBackup">
        <DatabaseBackup :size="16" />
        Manual Backup
      </button>
    </div>
    <div class="xb-admin-list">
      <article v-for="backup in bundle.backups" :key="backup.id" class="xb-admin-row">
        <div>
          <strong>{{ backup.status }}</strong>
          <span>{{ backup.backup_path || backup.error_message || 'pending' }}</span>
        </div>
        <span>{{ formatBytes(backup.file_size) }}</span>
      </article>
    </div>
  </section>

  <section v-if="editingUser" class="xb-modal-backdrop" @click.self="editingUser = null">
    <form class="xb-modal" @submit.prevent="saveUserEdit">
      <h3>Edit user</h3>
      <label>
        Role
        <select v-model="editingUser.role">
          <option value="owner">Owner</option>
          <option value="admin">Admin</option>
          <option value="user">User</option>
          <option value="guest">Guest</option>
        </select>
      </label>
      <label>
        Status
        <select v-model="editingUser.status">
          <option value="active">Active</option>
          <option value="disabled">Disabled</option>
        </select>
      </label>
      <label>Storage limit bytes <input v-model="editingUser.storage_limit_bytes" type="number" min="0" /></label>
      <div class="xb-row-actions">
        <button class="xb-primary-button" type="submit">
          <Save :size="16" />
          Save
        </button>
        <button class="xb-secondary-button" type="button" @click="editingUser = null">Cancel</button>
      </div>
    </form>
  </section>
</template>
