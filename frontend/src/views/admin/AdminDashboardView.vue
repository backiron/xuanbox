<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
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
import { setLocale } from '../../i18n'
import { useAuthStore } from '../../stores/authStore'

const router = useRouter()
const { t, locale } = useI18n()
const authStore = useAuthStore()
const activeTab = ref('overview')
const loading = ref(false)
const error = ref('')
const notice = ref('')
const bundle = ref({ overview: null, users: [], invites: [], audit_logs: [], backups: [], plans: [], worker: null, system_settings: {} })
const editingUser = ref(null)
const selectedAuditLog = ref(null)
const inviteDraft = ref({ role_to_assign: 'user', max_uses: 1, expires_at: '', note: '' })
const messageDraft = reactive({ title: '', body: '', level: 'info', recipient_username: '' })
const systemDraft = reactive({ registration_mode: 'invite_only', default_free_storage_mb: 500, auto_backup_enabled: false })
const passwordDraft = reactive({ old_password: '', new_password: '', confirm_password: '' })
const currentLocaleLabel = computed(() => locale.value === 'zh-CN' ? '中' : 'EN')
const localeTitle = computed(() => locale.value === 'zh-CN' ? '切换到英文' : 'Switch to Chinese')
const ADMIN_PAGE_SIZE = 10
const auditPage = ref(1)
const backupPage = ref(1)
const workerPage = ref(1)

const tabs = [
  { key: 'overview', labelKey: 'pages.admin.tab.overview', icon: Gauge },
  { key: 'users', labelKey: 'pages.admin.tab.users', icon: Users },
  { key: 'plans', labelKey: 'pages.admin.tab.plans', icon: CreditCard },
  { key: 'invites', labelKey: 'pages.admin.tab.invites', icon: Ticket },
  { key: 'messages', labelKey: 'pages.admin.tab.messages', icon: Bell },
  { key: 'system', labelKey: 'pages.admin.tab.system', icon: Settings },
  { key: 'audit', labelKey: 'pages.admin.tab.audit', icon: ClipboardList },
  { key: 'backups', labelKey: 'pages.admin.tab.backups', icon: DatabaseBackup },
  { key: 'worker', labelKey: 'pages.admin.tab.worker', icon: ServerCog }
]

const activeTabLabel = computed(() => {
  const tab = tabs.find((item) => item.key === activeTab.value)
  return tab ? t(tab.labelKey) : t('pages.admin.title')
})

const auditLogs = computed(() => bundle.value.audit_logs || [])
const backupRows = computed(() => bundle.value.backups || [])
const workerFailures = computed(() => bundle.value.worker?.recent_failures || [])
const auditPageCount = computed(() => pageCount(auditLogs.value))
const backupPageCount = computed(() => pageCount(backupRows.value))
const workerPageCount = computed(() => pageCount(workerFailures.value))
const pagedAuditLogs = computed(() => pagedItems(auditLogs.value, auditPage.value))
const pagedBackups = computed(() => pagedItems(backupRows.value, backupPage.value))
const pagedWorkerFailures = computed(() => pagedItems(workerFailures.value, workerPage.value))

function pageCount(items) {
  return Math.max(1, Math.ceil((items?.length || 0) / ADMIN_PAGE_SIZE))
}

function pagedItems(items, page) {
  const list = Array.isArray(items) ? items : []
  const start = (page - 1) * ADMIN_PAGE_SIZE
  return list.slice(start, start + ADMIN_PAGE_SIZE)
}

function clampPage(pageRef, items) {
  pageRef.value = Math.min(Math.max(1, pageRef.value), pageCount(items))
}

function setPage(pageRef, items, direction) {
  pageRef.value = Math.min(Math.max(1, pageRef.value + direction), pageCount(items))
}

function changeAuditPage(direction) {
  setPage(auditPage, auditLogs.value, direction)
}

function changeBackupPage(direction) {
  setPage(backupPage, backupRows.value, direction)
}

function changeWorkerPage(direction) {
  setPage(workerPage, workerFailures.value, direction)
}

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
  if (!value) return t('common.states.never')
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))
}

function quotaLabel(user) {
  return user.storage_limit_bytes == null ? t('common.states.unlimited') : formatBytes(user.storage_limit_bytes)
}

function usagePercent(user) {
  if (!user.storage_limit_bytes) return 0
  return Math.min(100, Math.round((user.storage_used_bytes / user.storage_limit_bytes) * 100))
}

function auditActionLabel(action) {
  const labels = {
    'admin.system_settings.update': t('pages.admin.auditAction.systemSettingsUpdate'),
    'admin.user.update': t('pages.admin.auditAction.userUpdate'),
    'backup.create': t('pages.admin.auditAction.backupCreate'),
    'backup.delete': t('pages.admin.auditAction.backupDelete'),
    'auth.login': t('pages.admin.auditAction.login'),
    'auth.refresh': t('pages.admin.auditAction.sessionRefresh'),
    'auth.logout': t('pages.admin.auditAction.logout')
  }
  return labels[action] || action
}

function auditTargetLabel(log) {
  if (!log.target_type && !log.target_id) return t('pages.admin.auditTargetSystem')
  return `${log.target_type || t('pages.admin.auditTargetUnknown')} · ${log.target_id || t('pages.admin.auditTargetNone')}`
}

function auditMetadata(log) {
  if (!log?.metadata_json || !Object.keys(log.metadata_json).length) return t('pages.admin.auditNoMetadata')
  return JSON.stringify(log.metadata_json, null, 2)
}

async function loadAdmin() {
  loading.value = true
  error.value = ''
  try {
    const response = await adminApi.bundle()
    bundle.value = response.data.data
    systemDraft.registration_mode = bundle.value.system_settings?.registration_mode || 'invite_only'
    systemDraft.default_free_storage_mb = bundle.value.system_settings?.default_free_storage_mb ?? 500
    systemDraft.auto_backup_enabled = Boolean(bundle.value.system_settings?.auto_backup_enabled)
    clampPage(auditPage, bundle.value.audit_logs || [])
    clampPage(backupPage, bundle.value.backups || [])
    clampPage(workerPage, bundle.value.worker?.recent_failures || [])
  } catch (err) {
    error.value = err.response?.data?.error?.message || t('pages.admin.loadFailed')
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
    error.value = err.response?.data?.error?.message || t('pages.admin.userUpdateFailed')
  }
}

async function saveSystemSettings() {
  error.value = ''
  notice.value = ''
  try {
    const response = await adminApi.updateSystemSettings({
      registration_mode: systemDraft.registration_mode,
      default_free_storage_mb: Number(systemDraft.default_free_storage_mb),
      auto_backup_enabled: systemDraft.auto_backup_enabled
    })
    bundle.value.system_settings = response.data.data
    systemDraft.auto_backup_enabled = Boolean(response.data.data?.auto_backup_enabled)
    notice.value = t('pages.admin.systemSaved')
  } catch (err) {
    error.value = err.response?.data?.error?.message || t('pages.admin.systemUpdateFailed')
  }
}

async function changeAdminPassword() {
  error.value = ''
  notice.value = ''
  if (passwordDraft.new_password !== passwordDraft.confirm_password) {
    error.value = t('pages.admin.passwordMismatch')
    return
  }
  try {
    await authApi.changePassword({
      old_password: passwordDraft.old_password,
      new_password: passwordDraft.new_password
    })
    passwordDraft.old_password = ''
    passwordDraft.new_password = ''
    passwordDraft.confirm_password = ''
    window.alert(t('pages.admin.passwordChangedRelogin'))
    authStore.logoutLocal()
    await router.push('/admin/login')
  } catch (err) {
    error.value = err.response?.data?.error?.message || t('pages.admin.passwordChangeFailed')
  }
}

async function createBackup() {
  error.value = ''
  notice.value = ''
  try {
    await adminApi.createBackup()
    await loadAdmin()
    activeTab.value = 'backups'
    notice.value = t('pages.admin.backupCreated')
  } catch (err) {
    error.value = err.response?.data?.error?.message || t('pages.admin.backupCreateFailed')
  }
}

async function deleteBackup(backup) {
  if (!window.confirm(t('pages.admin.deleteBackupConfirm'))) return
  error.value = ''
  notice.value = ''
  try {
    await adminApi.deleteBackup(backup.id)
    await loadAdmin()
    activeTab.value = 'backups'
    notice.value = t('pages.admin.backupDeleted')
  } catch (err) {
    error.value = err.response?.data?.error?.message || t('pages.admin.backupDeleteFailed')
  }
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
    error.value = err.response?.data?.error?.message || t('pages.admin.messageFailed')
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

function toggleLocale() {
  setLocale(locale.value === 'zh-CN' ? 'en' : 'zh-CN')
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
          <span>{{ t('pages.admin.title') }}</span>
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
          <span>{{ t(tab.labelKey) }}</span>
        </button>
      </nav>

      <div class="xb-admin-rail-footer">
        <span>{{ authStore.user?.display_name || authStore.user?.username || t('pages.admin.title') }}</span>
        <button type="button" class="xb-secondary-button" @click="logoutAdmin">
          <LogOut :size="15" />
          {{ t('common.buttons.signOut') }}
        </button>
      </div>
    </aside>

    <section class="xb-admin-main">
      <header class="xb-admin-header">
        <div>
          <p>{{ t('pages.admin.systemManagement') }}</p>
          <h1>{{ activeTabLabel }}</h1>
        </div>
        <div class="xb-admin-header-actions">
          <span class="xb-admin-status"><span></span> {{ t('pages.admin.systemOnline') }}</span>
          <button class="xb-language-toggle" type="button" :title="localeTitle" @click="toggleLocale">
            {{ currentLocaleLabel }}
          </button>
          <button class="xb-secondary-button" type="button" :disabled="loading" @click="loadAdmin">
            <RefreshCw :size="16" />
            {{ t('common.actions.refresh') }}
          </button>
        </div>
      </header>

      <p v-if="error" class="xb-form-error">{{ error }}</p>
      <p v-if="notice" class="xb-admin-notice">{{ notice }}</p>

      <section v-if="activeTab === 'overview'" class="xb-panel-grid">
        <article class="xb-panel">
          <Users :size="22" />
          <h3>{{ t('pages.admin.usersCount', { count: bundle.overview?.users_count || 0 }) }}</h3>
          <p>{{ t('pages.admin.activeAccountsCount', { count: bundle.overview?.active_users_count || 0 }) }}</p>
        </article>
        <article class="xb-panel">
          <DatabaseBackup :size="22" />
          <h3>{{ formatBytes(bundle.overview?.storage_bytes) }}</h3>
          <p>{{ t('pages.admin.uploadsTodayCount', { count: bundle.overview?.today_uploads_count || 0 }) }}</p>
        </article>
        <article class="xb-panel">
          <Activity :size="22" />
          <h3>{{ t('pages.admin.errorsCount', { count: bundle.overview?.error_count || 0 }) }}</h3>
          <p>{{ t('pages.admin.statusLine', { status: bundle.overview?.service_status?.api || t('common.actions.loading') }) }}</p>
        </article>
        <article class="xb-panel">
          <ShieldCheck :size="22" />
          <h3>{{ bundle.overview?.latest_backup?.status || t('pages.admin.noBackup') }}</h3>
          <p>{{ bundle.overview?.latest_backup?.created_at ? formatDate(bundle.overview.latest_backup.created_at) : t('pages.admin.noBackupDesc') }}</p>
        </article>
      </section>

      <section v-if="activeTab === 'users'" class="xb-panel xb-admin-section">
        <div class="xb-action-bar">
          <div>
            <strong>{{ t('pages.admin.overview.users') }}</strong>
            <span>{{ t('pages.admin.overview.usersDesc') }}</span>
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
            <button class="xb-text-button" type="button" @click="startUserEdit(user)">{{ t('common.actions.edit') }}</button>
          </article>
        </div>
      </section>

      <section v-if="activeTab === 'plans'" class="xb-panel xb-admin-section">
        <div class="xb-action-bar">
          <div>
            <strong>{{ t('pages.admin.planPolicies') }}</strong>
            <span>{{ t('pages.admin.planPoliciesDesc') }}</span>
          </div>
        </div>
        <div class="xb-plan-grid">
          <article v-for="plan in bundle.plans" :key="plan.key" class="xb-plan-card">
            <strong>{{ plan.name }}</strong>
            <span>{{ formatBytes(plan.storage_limit_bytes) }} {{ t('pages.admin.planStorage') }}</span>
            <span>{{ plan.max_public_shares ?? t('common.states.unlimited') }} {{ t('pages.admin.publicShares') }}</span>
            <span>{{ plan.max_share_downloads ?? t('common.states.unlimited') }} {{ t('pages.admin.downloadsPerLink') }}</span>
            <div>
              <span class="xb-admin-pill">{{ plan.ocr_enabled ? t('pages.admin.ocrOn') : t('pages.admin.ocrOff') }}</span>
              <span class="xb-admin-pill">{{ plan.ai_enabled ? t('pages.admin.aiOn') : t('pages.admin.aiOff') }}</span>
            </div>
          </article>
        </div>
      </section>

      <section v-if="activeTab === 'system'" class="xb-panel xb-admin-section">
        <div class="xb-action-bar">
          <div>
            <strong>{{ t('pages.admin.systemSettings') }}</strong>
            <span>{{ t('pages.admin.systemSettingsDesc') }}</span>
          </div>
        </div>
        <form class="xb-admin-system-form" @submit.prevent="saveSystemSettings">
          <label>
            {{ t('pages.admin.registrationMode') }}
            <select v-model="systemDraft.registration_mode">
              <option value="invite_only">{{ t('pages.admin.registration.inviteOnly') }}</option>
              <option value="open">{{ t('pages.admin.registration.open') }}</option>
              <option value="closed">{{ t('pages.admin.registration.closed') }}</option>
            </select>
          </label>
          <label>
            {{ t('pages.admin.defaultFreeStorage') }}
            <input v-model="systemDraft.default_free_storage_mb" type="number" min="0" step="1" />
          </label>
          <div class="xb-system-summary">
            <span>{{ t('pages.admin.defaultStorageHint', { count: systemDraft.default_free_storage_mb || 0 }) }}</span>
            <span>{{ t('pages.admin.freeOcr') }}</span>
          </div>
          <label class="xb-admin-check">
            <input v-model="systemDraft.auto_backup_enabled" type="checkbox" />
            <span>
              <strong>{{ t('pages.admin.autoBackup') }}</strong>
              <small>{{ t('pages.admin.autoBackupHint') }}</small>
            </span>
          </label>
          <button class="xb-primary-button" type="submit">
            <Save :size="16" />
            {{ t('pages.admin.saveSettings') }}
          </button>
        </form>

        <form class="xb-admin-system-form xb-admin-password-form" @submit.prevent="changeAdminPassword">
          <div class="xb-system-summary">
            <span>{{ t('pages.admin.adminPasswordTitle') }}</span>
            <span>{{ t('pages.admin.adminPasswordHint') }}</span>
          </div>
          <label>
            {{ t('pages.admin.currentPassword') }}
            <input v-model="passwordDraft.old_password" type="password" autocomplete="current-password" required />
          </label>
          <label>
            {{ t('pages.admin.newPassword') }}
            <input v-model="passwordDraft.new_password" type="password" autocomplete="new-password" minlength="10" required />
          </label>
          <label>
            {{ t('pages.admin.confirmNewPassword') }}
            <input v-model="passwordDraft.confirm_password" type="password" autocomplete="new-password" minlength="10" required />
          </label>
          <button class="xb-primary-button" type="submit">
            <Save :size="16" />
            {{ t('pages.admin.changePassword') }}
          </button>
        </form>
      </section>

      <section v-if="activeTab === 'invites'" class="xb-panel xb-admin-section">
        <form class="xb-admin-invite-form" @submit.prevent="createInvite">
          <label>
            {{ t('pages.admin.role') }}
            <select v-model="inviteDraft.role_to_assign">
              <option v-if="authStore.user?.role === 'owner'" value="admin">{{ t('pages.admin.status.admin') }}</option>
              <option value="user">{{ t('pages.admin.status.user') }}</option>
              <option value="guest">{{ t('pages.admin.status.guest') }}</option>
            </select>
          </label>
          <label>{{ t('pages.admin.maxUses') }} <input v-model="inviteDraft.max_uses" type="number" min="1" max="100" /></label>
          <label>{{ t('pages.shared.expires') }} <input v-model="inviteDraft.expires_at" type="datetime-local" /></label>
          <label>{{ t('pages.documents.note') }} <input v-model="inviteDraft.note" /></label>
          <button class="xb-primary-button" type="submit">{{ t('pages.admin.createInvite') }}</button>
        </form>
        <div class="xb-admin-list">
          <article v-for="invite in bundle.invites" :key="invite.id" class="xb-admin-row">
            <div>
              <strong>{{ invite.invite_code }}</strong>
              <span>{{ invite.role_to_assign }} · {{ invite.used_count }}/{{ invite.max_uses }} · {{ invite.is_active ? t('common.states.active') : t('common.states.inactive') }}</span>
            </div>
            <span>{{ invite.expires_at ? formatDate(invite.expires_at) : t('common.file.noExpiry') }}</span>
          </article>
        </div>
      </section>

      <section v-if="activeTab === 'messages'" class="xb-admin-messages">
        <form class="xb-panel xb-admin-message-form" @submit.prevent="createMessage">
          <div>
            <strong>{{ t('pages.admin.sendMessage') }}</strong>
            <span>{{ t('pages.admin.sendHint') }}</span>
          </div>
          <label>{{ t('pages.admin.titleLabel') }} <input v-model="messageDraft.title" maxlength="160" required /></label>
          <label>{{ t('pages.admin.recipient') }} <input v-model="messageDraft.recipient_username" :placeholder="t('pages.admin.recipientOptional')" /></label>
          <label>
            {{ t('pages.admin.level') }}
            <select v-model="messageDraft.level">
              <option value="info">{{ t('pages.admin.levelInfo') }}</option>
              <option value="success">{{ t('pages.admin.levelSuccess') }}</option>
              <option value="warning">{{ t('pages.admin.levelWarning') }}</option>
              <option value="critical">{{ t('pages.admin.levelCritical') }}</option>
            </select>
          </label>
          <label>{{ t('pages.admin.body') }} <textarea v-model="messageDraft.body" rows="5" maxlength="4000" required></textarea></label>
          <button class="xb-primary-button" type="submit">{{ t('pages.admin.sendMessage') }}</button>
        </form>
        <section class="xb-panel xb-admin-section">
          <div class="xb-admin-list">
            <article v-for="message in bundle.messages || []" :key="message.id" class="xb-admin-row">
              <div>
                <strong>{{ message.title }}</strong>
                <span>{{ message.scope }} · {{ message.level }} · {{ formatDate(message.created_at) }}</span>
                <small>{{ message.body }}</small>
              </div>
              <button class="xb-text-button xb-danger-button" type="button" @click="archiveMessage(message)">{{ t('pages.shared.archive') }}</button>
            </article>
            <p v-if="!(bundle.messages || []).length" class="xb-muted">{{ t('pages.admin.noMessagesYet') }}</p>
          </div>
        </section>
      </section>

      <section v-if="activeTab === 'audit'" class="xb-panel xb-admin-section">
        <div class="xb-action-bar">
          <div>
            <strong>{{ t('pages.admin.auditTrail') }}</strong>
            <span>{{ t('pages.admin.auditTrailDesc') }}</span>
          </div>
        </div>
        <div class="xb-admin-list">
          <article v-for="log in pagedAuditLogs" :key="log.id" class="xb-admin-row xb-admin-click-row" @click="selectedAuditLog = log">
            <div>
              <strong>{{ auditActionLabel(log.action) }}</strong>
              <span>{{ auditTargetLabel(log) }}</span>
            </div>
            <span>{{ formatDate(log.created_at) }}</span>
          </article>
          <p v-if="!auditLogs.length" class="xb-muted">{{ t('pages.admin.noAuditLogs') }}</p>
        </div>
        <nav v-if="auditLogs.length > ADMIN_PAGE_SIZE" class="xb-pagination" aria-label="Audit pages">
          <button class="xb-secondary-button" type="button" :disabled="auditPage <= 1" @click="changeAuditPage(-1)">
            {{ t('pages.admin.pagePrev') }}
          </button>
          <span>{{ t('pages.admin.pageSummary', { page: auditPage, pages: auditPageCount, count: auditLogs.length }) }}</span>
          <button class="xb-secondary-button" type="button" :disabled="auditPage >= auditPageCount" @click="changeAuditPage(1)">
            {{ t('pages.admin.pageNext') }}
          </button>
        </nav>
      </section>

      <section v-if="activeTab === 'backups'" class="xb-panel xb-admin-section">
        <div class="xb-action-bar">
          <div>
            <strong>{{ t('pages.admin.backups') }}</strong>
            <span>{{ t('pages.admin.backupsDesc') }}</span>
          </div>
          <button class="xb-primary-button" type="button" :disabled="loading" @click="createBackup">
            <DatabaseBackup :size="16" />
            {{ t('pages.admin.createBackup') }}
          </button>
        </div>
        <div class="xb-admin-list">
          <article v-for="backup in pagedBackups" :key="backup.id" class="xb-admin-row">
            <div>
              <strong>{{ backup.status }}</strong>
              <span>{{ backup.backup_path || backup.error_message || 'pending' }}</span>
            </div>
            <span>{{ formatBytes(backup.file_size) }}</span>
            <button class="xb-text-button xb-danger-button" type="button" @click="deleteBackup(backup)">
              {{ t('common.actions.delete') }}
            </button>
          </article>
          <p v-if="!backupRows.length" class="xb-muted">{{ t('pages.admin.noBackupsYet') }}</p>
        </div>
        <nav v-if="backupRows.length > ADMIN_PAGE_SIZE" class="xb-pagination" aria-label="Backup pages">
          <button class="xb-secondary-button" type="button" :disabled="backupPage <= 1" @click="changeBackupPage(-1)">
            {{ t('pages.admin.pagePrev') }}
          </button>
          <span>{{ t('pages.admin.pageSummary', { page: backupPage, pages: backupPageCount, count: backupRows.length }) }}</span>
          <button class="xb-secondary-button" type="button" :disabled="backupPage >= backupPageCount" @click="changeBackupPage(1)">
            {{ t('pages.admin.pageNext') }}
          </button>
        </nav>
      </section>

      <section v-if="activeTab === 'worker'" class="xb-panel xb-admin-section">
        <div class="xb-worker-grid">
          <article>
            <strong>{{ t('pages.admin.backgroundJobs') }}</strong>
            <span v-for="(count, status) in bundle.worker?.worker_tasks || {}" :key="status">{{ status }}: {{ count }}</span>
          </article>
          <article>
            <strong>{{ t('pages.admin.receiptScans') }}</strong>
            <span v-for="(count, status) in bundle.worker?.ocr_tasks || {}" :key="status">{{ status }}: {{ count }}</span>
          </article>
          <article>
            <strong>{{ t('pages.admin.documentTextScans') }}</strong>
            <span v-for="(count, status) in bundle.worker?.document_intelligence_tasks || {}" :key="status">{{ status }}: {{ count }}</span>
          </article>
          <article>
            <strong>{{ t('pages.admin.localAI') }}</strong>
            <span>{{ bundle.worker?.ai?.enabled ? t('common.states.enabled') : t('common.states.disabled') }}</span>
            <span>{{ bundle.worker?.ai?.model || t('pages.admin.noModelSelected') }}</span>
            <span>{{ bundle.worker?.ai?.base_url || t('pages.admin.noConnectionConfigured') }}</span>
          </article>
          <article>
            <strong>{{ t('pages.admin.backups') }}</strong>
            <span v-for="(count, status) in bundle.worker?.backups || {}" :key="status">{{ status }}: {{ count }}</span>
          </article>
        </div>
        <div class="xb-admin-list">
          <article v-for="failure in pagedWorkerFailures" :key="failure.id" class="xb-admin-row">
            <div>
              <strong>{{ failure.task_type }}</strong>
              <span>{{ failure.target_type || 'task' }} · {{ t('pages.admin.attempts', { count: failure.attempts }) }} · {{ failure.finished_at ? formatDate(failure.finished_at) : t('pages.admin.unfinished') }}</span>
              <small>{{ failure.error_message }}</small>
            </div>
          </article>
          <p v-if="!workerFailures.length" class="xb-muted">{{ t('pages.admin.noWorkers') }}</p>
        </div>
        <nav v-if="workerFailures.length > ADMIN_PAGE_SIZE" class="xb-pagination" aria-label="Worker failure pages">
          <button class="xb-secondary-button" type="button" :disabled="workerPage <= 1" @click="changeWorkerPage(-1)">
            {{ t('pages.admin.pagePrev') }}
          </button>
          <span>{{ t('pages.admin.pageSummary', { page: workerPage, pages: workerPageCount, count: workerFailures.length }) }}</span>
          <button class="xb-secondary-button" type="button" :disabled="workerPage >= workerPageCount" @click="changeWorkerPage(1)">
            {{ t('pages.admin.pageNext') }}
          </button>
        </nav>
      </section>
    </section>

    <section v-if="editingUser" class="xb-modal-backdrop" @click.self="editingUser = null">
      <form class="xb-modal" @submit.prevent="saveUserEdit">
        <h3>{{ t('pages.admin.editUser') }}</h3>
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

    <section v-if="selectedAuditLog" class="xb-modal-backdrop" @click.self="selectedAuditLog = null">
      <article class="xb-modal xb-audit-modal">
        <h3>{{ t('pages.admin.auditDetails') }}</h3>
        <dl>
          <dt>{{ t('pages.admin.auditActionLabel') }}</dt>
          <dd>{{ auditActionLabel(selectedAuditLog.action) }}</dd>
          <dt>{{ t('pages.admin.auditTarget') }}</dt>
          <dd>{{ auditTargetLabel(selectedAuditLog) }}</dd>
          <dt>{{ t('pages.admin.auditTime') }}</dt>
          <dd>{{ formatDate(selectedAuditLog.created_at) }}</dd>
          <dt>{{ t('pages.admin.auditActor') }}</dt>
          <dd>{{ selectedAuditLog.actor_user_id || t('common.states.unknown') }}</dd>
          <dt>{{ t('pages.admin.auditIp') }}</dt>
          <dd>{{ selectedAuditLog.ip_address || t('common.states.unknown') }}</dd>
          <dt>{{ t('pages.admin.auditUserAgent') }}</dt>
          <dd>{{ selectedAuditLog.user_agent || t('common.states.unknown') }}</dd>
          <dt>{{ t('pages.admin.auditMetadata') }}</dt>
          <dd><pre>{{ auditMetadata(selectedAuditLog) }}</pre></dd>
        </dl>
        <div class="xb-row-actions">
          <button class="xb-secondary-button" type="button" @click="selectedAuditLog = null">{{ t('common.actions.close') }}</button>
        </div>
      </article>
    </section>
  </main>
</template>
