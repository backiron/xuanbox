<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  Activity,
  Bell,
  ClipboardList,
  CreditCard,
  DatabaseBackup,
  Gauge,
  LogOut,
  RefreshCw,
  Save,
  ServerCog,
  Settings,
  ShieldCheck,
  Ticket,
  Users
} from 'lucide-vue-next'

import { adminApi } from '../../api/adminApi'
import { authApi } from '../../api/authApi'
import { inviteApi } from '../../api/inviteApi'
import XbAssetIcon from '../../components/common/XbAssetIcon.vue'
import { useAuthStore } from '../../stores/authStore'

const router = useRouter()
const authStore = useAuthStore()
const activeTab = ref('overview')
const loading = ref(false)
const error = ref('')
const bundle = ref({ overview: null, users: [], invites: [], audit_logs: [], backups: [], plans: [], worker: null, system_settings: {} })
const editingUser = ref(null)
const inviteDraft = ref({ role_to_assign: 'user', max_uses: 1, expires_at: '', note: '' })
const messageDraft = reactive({ title: '', body: '', level: 'info', recipient_username: '' })
const systemDraft = reactive({ registration_mode: 'invite_only', default_free_storage_mb: 500 })

const tabs = [
  { key: 'overview', label: 'Overview', icon: Gauge },
  { key: 'users', label: 'Users', icon: Users },
  { key: 'plans', label: 'Plans', icon: CreditCard },
  { key: 'invites', label: 'Invites', icon: Ticket },
  { key: 'messages', label: 'Messages', icon: Bell },
  { key: 'system', label: 'System', icon: Settings },
  { key: 'audit', label: 'Audit', icon: ClipboardList },
  { key: 'backups', label: 'Backups', icon: DatabaseBackup },
  { key: 'worker', label: 'Worker', icon: ServerCog }
]

const activeTabLabel = computed(() => tabs.find((tab) => tab.key === activeTab.value)?.label || 'Admin Console')

function formatBytes(value) {
  if (!value) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let size = Number(value)
  let unit = 0
  while (size >= 1024 && unit < units.length - 1) {
    size /= 1024
    unit += 1
  }
  return `${size.toFixed(unit < 2 ? 0 : 1)} ${units[unit]}`
}

function bytesToMb(value) {
  if (value == null) return ''
  return Math.round(Number(value) / 1024 / 1024)
}

function formatDate(value) {
  if (!value) return 'Never'
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))
}

function quotaLabel(user) {
  return user.storage_limit_bytes == null ? 'Unlimited' : formatBytes(user.storage_limit_bytes)
}

function usagePercent(user) {
  if (!user.storage_limit_bytes) return 0
  return Math.min(100, Math.round((user.storage_used_bytes / user.storage_limit_bytes) * 100))
}

async function loadAdmin() {
  loading.value = true
  error.value = ''
  try {
    const response = await adminApi.bundle()
    bundle.value = response.data.data
    systemDraft.registration_mode = bundle.value.system_settings?.registration_mode || 'invite_only'
    systemDraft.default_free_storage_mb = bundle.value.system_settings?.default_free_storage_mb ?? 500
  } catch (err) {
    error.value = err.response?.data?.error?.message || 'Unable to load admin data'
  } finally {
    loading.value = false
  }
}

function startUserEdit(user) {
  editingUser.value = { ...user, storage_limit_mb: bytesToMb(user.storage_limit_bytes) }
}

async function saveUserEdit() {
  error.value = ''
  try {
    await adminApi.updateUser(editingUser.value.id, {
      role: editingUser.value.role,
      plan: editingUser.value.plan,
      status: editingUser.value.status,
      storage_limit_mb: editingUser.value.storage_limit_mb === '' ? null : Number(editingUser.value.storage_limit_mb)
    })
    editingUser.value = null
    await loadAdmin()
  } catch (err) {
    error.value = err.response?.data?.error?.message || 'Unable to update user'
  }
}

async function saveSystemSettings() {
  error.value = ''
  try {
    const response = await adminApi.updateSystemSettings({
      registration_mode: systemDraft.registration_mode,
      default_free_storage_mb: Number(systemDraft.default_free_storage_mb)
    })
    bundle.value.system_settings = response.data.data
  } catch (err) {
    error.value = err.response?.data?.error?.message || 'Unable to update system settings'
  }
}

async function createBackup() {
  await adminApi.createBackup()
  await loadAdmin()
  activeTab.value = 'backups'
}

async function createInvite() {
  await inviteApi.create({
    role_to_assign: inviteDraft.value.role_to_assign,
    max_uses: Number(inviteDraft.value.max_uses) || 1,
    expires_at: inviteDraft.value.expires_at ? new Date(inviteDraft.value.expires_at).toISOString() : null,
    note: inviteDraft.value.note || null
  })
  inviteDraft.value = { role_to_assign: 'user', max_uses: 1, expires_at: '', note: '' }
  await loadAdmin()
  activeTab.value = 'invites'
}

async function createMessage() {
  error.value = ''
  try {
    await adminApi.createMessage({
      title: messageDraft.title,
      body: messageDraft.body,
      level: messageDraft.level,
      recipient_username: messageDraft.recipient_username || null
    })
    messageDraft.title = ''
    messageDraft.body = ''
    messageDraft.level = 'info'
    messageDraft.recipient_username = ''
    await loadAdmin()
    activeTab.value = 'messages'
  } catch (err) {
    error.value = err.response?.data?.error?.message || 'Unable to send message'
  }
}

async function archiveMessage(message) {
  await adminApi.archiveMessage(message.id)
  await loadAdmin()
}

async function logoutAdmin() {
  try {
    await authApi.logout(authStore.refreshToken)
  } finally {
    authStore.logoutLocal()
    await router.push('/admin/login')
  }
}

onMounted(loadAdmin)
</script>

<template>
  <main class="xb-admin-console">
    <aside class="xb-admin-rail">
      <router-link to="/admin-console" class="xb-admin-brand">
        <XbAssetIcon name="logo" :size="34" />
        <div>
          <strong>XuanBox</strong>
          <span>Admin Console</span>
        </div>
      </router-link>

      <nav class="xb-admin-nav">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          type="button"
          :class="{ 'is-active': activeTab === tab.key }"
          @click="activeTab = tab.key"
        >
          <component :is="tab.icon" :size="18" />
          <span>{{ tab.label }}</span>
        </button>
      </nav>

      <div class="xb-admin-rail-footer">
        <span>{{ authStore.user?.display_name || authStore.user?.username || 'Admin' }}</span>
        <button type="button" class="xb-secondary-button" @click="logoutAdmin">
          <LogOut :size="15" />
          Sign out
        </button>
      </div>
    </aside>

    <section class="xb-admin-main">
      <header class="xb-admin-header">
        <div>
          <p>System management</p>
          <h1>{{ activeTabLabel }}</h1>
        </div>
        <div class="xb-admin-header-actions">
          <span class="xb-admin-status"><span></span> API healthy</span>
          <button class="xb-secondary-button" type="button" :disabled="loading" @click="loadAdmin">
            <RefreshCw :size="16" />
            Refresh
          </button>
        </div>
      </header>

      <p v-if="error" class="xb-form-error">{{ error }}</p>

      <section v-if="activeTab === 'overview'" class="xb-panel-grid">
        <article class="xb-panel">
          <Users :size="22" />
          <h3>{{ bundle.overview?.users_count || 0 }} users</h3>
          <p>{{ bundle.overview?.active_users_count || 0 }} active accounts</p>
        </article>
        <article class="xb-panel">
          <DatabaseBackup :size="22" />
          <h3>{{ formatBytes(bundle.overview?.storage_bytes) }}</h3>
          <p>{{ bundle.overview?.today_uploads_count || 0 }} uploads today</p>
        </article>
        <article class="xb-panel">
          <Activity :size="22" />
          <h3>{{ bundle.overview?.error_count || 0 }} errors</h3>
          <p>Health: {{ bundle.overview?.service_status?.api || 'loading' }}</p>
        </article>
        <article class="xb-panel">
          <ShieldCheck :size="22" />
          <h3>{{ bundle.overview?.latest_backup?.status || 'No backup' }}</h3>
          <p>{{ bundle.overview?.latest_backup?.created_at ? formatDate(bundle.overview.latest_backup.created_at) : 'Create a backup before deployment.' }}</p>
        </article>
      </section>

      <section v-if="activeTab === 'users'" class="xb-panel xb-admin-section">
        <div class="xb-action-bar">
          <div>
            <strong>User accounts</strong>
            <span>Manage role, plan, account status, and storage limits without opening private content.</span>
          </div>
        </div>
        <div class="xb-admin-user-table">
          <article v-for="user in bundle.users" :key="user.id" class="xb-admin-user-row">
            <div class="xb-admin-user-id">
              <strong>{{ user.display_name || user.username }}</strong>
              <span>{{ user.username }} · {{ user.email }}</span>
            </div>
            <div>
              <span class="xb-admin-pill">{{ user.role }}</span>
              <span class="xb-admin-pill">{{ user.plan }}</span>
              <span class="xb-admin-pill" :class="{ 'is-muted': user.status !== 'active' }">{{ user.status }}</span>
            </div>
            <div class="xb-admin-usage">
              <div>
                <span>{{ formatBytes(user.storage_used_bytes) }}</span>
                <span>{{ quotaLabel(user) }}</span>
              </div>
              <progress :value="usagePercent(user)" max="100"></progress>
            </div>
            <button class="xb-text-button" type="button" @click="startUserEdit(user)">Edit</button>
          </article>
        </div>
      </section>

      <section v-if="activeTab === 'plans'" class="xb-panel xb-admin-section">
        <div class="xb-action-bar">
          <div>
            <strong>Plan policies</strong>
            <span>Current product limits used for account planning and commercial packaging.</span>
          </div>
        </div>
        <div class="xb-plan-grid">
          <article v-for="plan in bundle.plans" :key="plan.key" class="xb-plan-card">
            <strong>{{ plan.name }}</strong>
            <span>{{ formatBytes(plan.storage_limit_bytes) }} storage</span>
            <span>{{ plan.max_public_shares ?? 'Unlimited' }} public shares</span>
            <span>{{ plan.max_share_downloads ?? 'Unlimited' }} downloads/link</span>
            <div>
              <span class="xb-admin-pill">{{ plan.ocr_enabled ? 'OCR on' : 'OCR off' }}</span>
              <span class="xb-admin-pill">{{ plan.ai_enabled ? 'AI on' : 'AI off' }}</span>
            </div>
          </article>
        </div>
      </section>

      <section v-if="activeTab === 'system'" class="xb-panel xb-admin-section">
        <div class="xb-action-bar">
          <div>
            <strong>System settings</strong>
            <span>Control registration, default storage, and the free/pro account base.</span>
          </div>
        </div>
        <form class="xb-admin-system-form" @submit.prevent="saveSystemSettings">
          <label>
            Registration mode
            <select v-model="systemDraft.registration_mode">
              <option value="invite_only">Invite only</option>
              <option value="open">Open registration + invite</option>
              <option value="closed">Closed</option>
            </select>
          </label>
          <label>
            Default free storage (MB)
            <input v-model="systemDraft.default_free_storage_mb" type="number" min="0" step="1" />
          </label>
          <div class="xb-system-summary">
            <span>New free users start with {{ systemDraft.default_free_storage_mb || 0 }} MB.</span>
            <span>Free keeps OCR basics. Pro unlocks local AI assistance.</span>
          </div>
          <button class="xb-primary-button" type="submit">
            <Save :size="16" />
            Save settings
          </button>
        </form>
      </section>

      <section v-if="activeTab === 'invites'" class="xb-panel xb-admin-section">
        <form class="xb-admin-invite-form" @submit.prevent="createInvite">
          <label>
            Role
            <select v-model="inviteDraft.role_to_assign">
              <option v-if="authStore.user?.role === 'owner'" value="admin">Admin</option>
              <option value="user">User</option>
              <option value="guest">Guest</option>
            </select>
          </label>
          <label>Max uses <input v-model="inviteDraft.max_uses" type="number" min="1" max="100" /></label>
          <label>Expires <input v-model="inviteDraft.expires_at" type="datetime-local" /></label>
          <label>Note <input v-model="inviteDraft.note" /></label>
          <button class="xb-primary-button" type="submit">Create invite</button>
        </form>
        <div class="xb-admin-list">
          <article v-for="invite in bundle.invites" :key="invite.id" class="xb-admin-row">
            <div>
              <strong>{{ invite.invite_code }}</strong>
              <span>{{ invite.role_to_assign }} · {{ invite.used_count }}/{{ invite.max_uses }} · {{ invite.is_active ? 'active' : 'inactive' }}</span>
            </div>
            <span>{{ invite.expires_at ? formatDate(invite.expires_at) : 'No expiry' }}</span>
          </article>
        </div>
      </section>

      <section v-if="activeTab === 'messages'" class="xb-admin-messages">
        <form class="xb-panel xb-admin-message-form" @submit.prevent="createMessage">
          <div>
            <strong>Send message</strong>
            <span>Leave recipient empty to broadcast to every user.</span>
          </div>
          <label>Title <input v-model="messageDraft.title" maxlength="160" required /></label>
          <label>Recipient <input v-model="messageDraft.recipient_username" placeholder="username or email, optional" /></label>
          <label>
            Level
            <select v-model="messageDraft.level">
              <option value="info">Info</option>
              <option value="success">Success</option>
              <option value="warning">Warning</option>
              <option value="critical">Critical</option>
            </select>
          </label>
          <label>Body <textarea v-model="messageDraft.body" rows="5" maxlength="4000" required></textarea></label>
          <button class="xb-primary-button" type="submit">Send message</button>
        </form>
        <section class="xb-panel xb-admin-section">
          <div class="xb-admin-list">
            <article v-for="message in bundle.messages || []" :key="message.id" class="xb-admin-row">
              <div>
                <strong>{{ message.title }}</strong>
                <span>{{ message.scope }} · {{ message.level }} · {{ formatDate(message.created_at) }}</span>
                <small>{{ message.body }}</small>
              </div>
              <button class="xb-text-button xb-danger-button" type="button" @click="archiveMessage(message)">Archive</button>
            </article>
            <p v-if="!(bundle.messages || []).length" class="xb-muted">No messages yet.</p>
          </div>
        </section>
      </section>

      <section v-if="activeTab === 'audit'" class="xb-panel xb-admin-section">
        <div class="xb-admin-list">
          <article v-for="log in bundle.audit_logs" :key="log.id" class="xb-admin-row">
            <div>
              <strong>{{ log.action }}</strong>
              <span>{{ log.target_type || 'system' }} · {{ log.target_id || 'none' }}</span>
            </div>
            <span>{{ formatDate(log.created_at) }}</span>
          </article>
        </div>
      </section>

      <section v-if="activeTab === 'backups'" class="xb-panel xb-admin-section">
        <div class="xb-action-bar">
          <div>
            <strong>Backups</strong>
            <span>Database export, encrypted storage, safe config copy, and restore notes.</span>
          </div>
          <button class="xb-primary-button" type="button" :disabled="loading" @click="createBackup">
            <DatabaseBackup :size="16" />
            Manual backup
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

      <section v-if="activeTab === 'worker'" class="xb-panel xb-admin-section">
        <div class="xb-worker-grid">
          <article>
            <strong>Worker tasks</strong>
            <span v-for="(count, status) in bundle.worker?.worker_tasks || {}" :key="status">{{ status }}: {{ count }}</span>
          </article>
          <article>
            <strong>OCR tasks</strong>
            <span v-for="(count, status) in bundle.worker?.ocr_tasks || {}" :key="status">{{ status }}: {{ count }}</span>
          </article>
          <article>
            <strong>Document intelligence</strong>
            <span v-for="(count, status) in bundle.worker?.document_intelligence_tasks || {}" :key="status">{{ status }}: {{ count }}</span>
          </article>
          <article>
            <strong>Local AI</strong>
            <span>{{ bundle.worker?.ai?.enabled ? 'Enabled' : 'Disabled' }}</span>
            <span>{{ bundle.worker?.ai?.model || 'No model configured' }}</span>
            <span>{{ bundle.worker?.ai?.base_url || 'No endpoint' }}</span>
          </article>
          <article>
            <strong>Backups</strong>
            <span v-for="(count, status) in bundle.worker?.backups || {}" :key="status">{{ status }}: {{ count }}</span>
          </article>
        </div>
        <div class="xb-admin-list">
          <article v-for="failure in bundle.worker?.recent_failures || []" :key="failure.id" class="xb-admin-row">
            <div>
              <strong>{{ failure.task_type }}</strong>
              <span>{{ failure.target_type || 'task' }} · attempts {{ failure.attempts }} · {{ failure.finished_at ? formatDate(failure.finished_at) : 'unfinished' }}</span>
              <small>{{ failure.error_message }}</small>
            </div>
          </article>
          <p v-if="!(bundle.worker?.recent_failures || []).length" class="xb-muted">No recent worker failures.</p>
        </div>
      </section>
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
          Plan
          <select v-model="editingUser.plan">
            <option value="free">Free</option>
            <option value="pro">Pro</option>
          </select>
        </label>
        <label>
          Status
          <select v-model="editingUser.status">
            <option value="active">Active</option>
            <option value="disabled">Disabled</option>
          </select>
        </label>
        <label>Storage limit (MB) <input v-model="editingUser.storage_limit_mb" type="number" min="0" step="1" placeholder="empty for unlimited" /></label>
        <div class="xb-row-actions">
          <button class="xb-primary-button" type="submit">
            <Save :size="16" />
            Save
          </button>
          <button class="xb-secondary-button" type="button" @click="editingUser = null">Cancel</button>
        </div>
      </form>
    </section>
  </main>
</template>
