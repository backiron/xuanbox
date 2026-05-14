<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  Camera,
  Database,
  Moon,
  KeyRound,
  Laptop,
  Lock,
  LogOut,
  RefreshCw,
  ShieldCheck,
  Smartphone,
  Sun,
  UserRound,
  XCircle
} from 'lucide-vue-next'

import PageHeader from '../../components/common/PageHeader.vue'
import { authApi } from '../../api/authApi'
import { deviceApi } from '../../api/deviceApi'
import { importantDocApi } from '../../api/fileApi'
import { settingsApi } from '../../api/settingsApi'
import { http } from '../../api/http'
import { useAuthStore } from '../../stores/authStore'
import { useDialogStore } from '../../stores/dialogStore'
import { useThemeStore } from '../../stores/themeStore'

const router = useRouter()
const authStore = useAuthStore()
const dialog = useDialogStore()
const themeStore = useThemeStore()
const activeSection = ref('profile')
const devices = ref([])
const storage = ref(null)
const vaultStatus = ref({ pin_set: false, locked_until: null })
const avatarObjectUrl = ref('')
const loading = ref(false)
const message = ref('')
const error = ref('')
const profileForm = reactive({ display_name: '', email: '' })
const passwordForm = reactive({ old_password: '', new_password: '' })
const vaultForm = reactive({ pin: '' })

const sections = [
  { key: 'profile', label: 'Profile', icon: UserRound },
  { key: 'security', label: 'Security', icon: ShieldCheck },
  { key: 'devices', label: 'Devices', icon: Laptop },
  { key: 'storage', label: 'Storage', icon: Database },
  { key: 'appearance', label: 'Appearance', icon: Moon },
  { key: 'privacy', label: 'Notes', icon: Lock }
]

const initials = computed(() => {
  const name = authStore.user?.display_name || authStore.user?.username || 'XB'
  return name.slice(0, 2).toUpperCase()
})

function formatBytes(value) {
  if (value == null) return 'Unlimited'
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

function formatDate(value) {
  if (!value) return 'Never seen'
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))
}

function syncProfileForm() {
  profileForm.display_name = authStore.user?.display_name || ''
  profileForm.email = authStore.user?.email || ''
}

async function loadDevices() {
  const response = await deviceApi.list()
  devices.value = response.data.data
}

async function loadStorage() {
  const response = await settingsApi.storage()
  storage.value = response.data.data
}

async function loadVaultStatus() {
  const response = await importantDocApi.status()
  vaultStatus.value = response.data.data
}

async function loadAvatar() {
  if (!authStore.user?.avatar_file_id) {
    avatarObjectUrl.value = ''
    return
  }
  try {
    const response = await http.get('/settings/avatar', { responseType: 'blob' })
    if (avatarObjectUrl.value) URL.revokeObjectURL(avatarObjectUrl.value)
    avatarObjectUrl.value = URL.createObjectURL(response.data)
  } catch {
    avatarObjectUrl.value = ''
  }
}

async function loadAll() {
  loading.value = true
  error.value = ''
  try {
    await authStore.loadMe()
    syncProfileForm()
    await Promise.all([loadDevices(), loadStorage(), loadVaultStatus(), loadAvatar()])
  } catch (err) {
    error.value = err.response?.data?.error?.message || 'Unable to load settings'
  } finally {
    loading.value = false
  }
}

async function saveProfile() {
  message.value = ''
  error.value = ''
  try {
    const response = await settingsApi.updateProfile({ ...profileForm })
    authStore.user = response.data.data
    syncProfileForm()
    message.value = 'Profile updated'
  } catch (err) {
    error.value = err.response?.data?.error?.message || 'Unable to update profile'
  }
}

async function uploadAvatar(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return
  message.value = ''
  error.value = ''
  try {
    const response = await settingsApi.uploadAvatar(file)
    authStore.user = response.data.data
    await loadAvatar()
    await loadStorage()
    message.value = 'Avatar updated'
  } catch (err) {
    error.value = err.response?.data?.error?.message || 'Unable to upload avatar'
  }
}

async function changePassword() {
  message.value = ''
  error.value = ''
  try {
    await authApi.changePassword({ ...passwordForm })
    passwordForm.old_password = ''
    passwordForm.new_password = ''
    authStore.logoutLocal()
    await router.push('/login')
  } catch (err) {
    error.value = err.response?.data?.error?.message || 'Unable to change password'
  }
}

async function setupVaultPin() {
  message.value = ''
  error.value = ''
  try {
    await importantDocApi.setup(vaultForm.pin)
    vaultForm.pin = ''
    await loadVaultStatus()
    message.value = 'Important docs PIN is ready'
  } catch (err) {
    error.value = err.response?.data?.error?.message || 'Unable to set PIN'
  }
}

async function revokeDevice(device) {
  const confirmed = await dialog.confirm({
    title: 'Revoke device?',
    message: `${device.device_name} will be signed out.`,
    confirmText: 'Revoke',
    danger: true
  })
  if (!confirmed) return
  await deviceApi.revoke(device.id)
  await loadDevices()
}

async function logoutCurrent() {
  try {
    await authApi.logout(authStore.refreshToken)
  } finally {
    authStore.logoutLocal()
    await router.push('/login')
  }
}

async function logoutEverywhere() {
  const confirmed = await dialog.confirm({
    title: 'Log out every device?',
    message: 'All active sessions will be revoked.',
    confirmText: 'Log out all',
    danger: true
  })
  if (!confirmed) return
  try {
    await authApi.logoutAllDevices()
  } finally {
    authStore.logoutLocal()
    await router.push('/login')
  }
}

onMounted(loadAll)
</script>

<template>
  <PageHeader title="Settings" subtitle="Manage your profile, security, devices, storage, and privacy notes.">
    <button class="xb-secondary-button" type="button" :disabled="loading" @click="loadAll">
      <RefreshCw :size="16" />
      Refresh
    </button>
  </PageHeader>

  <p v-if="message" class="xb-muted">{{ message }}</p>
  <p v-if="error" class="xb-form-error">{{ error }}</p>

  <section class="xb-settings-shell">
    <nav class="xb-settings-nav">
      <button
        v-for="section in sections"
        :key="section.key"
        type="button"
        :class="{ 'is-active': activeSection === section.key }"
        @click="activeSection = section.key"
      >
        <component :is="section.icon" :size="17" />
        <span>{{ section.label }}</span>
      </button>
    </nav>

    <div class="xb-settings-body">
      <section v-if="activeSection === 'profile'" class="xb-panel xb-settings-card">
        <div class="xb-settings-card-header">
          <div>
            <h3>Profile</h3>
            <p>Your personal identity inside XuanBox.</p>
          </div>
          <label class="xb-secondary-button xb-avatar-upload">
            <Camera :size="16" />
            Avatar
            <input type="file" accept="image/*" @change="uploadAvatar" />
          </label>
        </div>
        <div class="xb-profile-editor">
          <div class="xb-profile-avatar is-large">
            <img v-if="avatarObjectUrl" :src="avatarObjectUrl" alt="" />
            <span v-else>{{ initials }}</span>
          </div>
          <form class="xb-settings-form" @submit.prevent="saveProfile">
            <label>
              Display name
              <input v-model="profileForm.display_name" maxlength="120" />
            </label>
            <label>
              Email
              <input v-model="profileForm.email" type="email" required />
            </label>
            <div class="xb-row-actions">
              <button class="xb-primary-button" type="submit">Save profile</button>
            </div>
          </form>
        </div>
      </section>

      <section v-if="activeSection === 'security'" class="xb-settings-stack">
        <form class="xb-panel xb-settings-card xb-settings-form" @submit.prevent="changePassword">
          <div class="xb-settings-card-header">
            <div>
              <h3>Password</h3>
              <p>Changing password ends all active sessions.</p>
            </div>
            <KeyRound :size="22" />
          </div>
          <label>
            Current password
            <input v-model="passwordForm.old_password" type="password" autocomplete="current-password" required />
          </label>
          <label>
            New password
            <input v-model="passwordForm.new_password" type="password" minlength="10" autocomplete="new-password" required />
          </label>
          <button class="xb-primary-button" type="submit">Change password</button>
        </form>

        <form class="xb-panel xb-settings-card xb-settings-form" @submit.prevent="setupVaultPin">
          <div class="xb-settings-card-header">
            <div>
              <h3>Important docs PIN</h3>
              <p>{{ vaultStatus.pin_set ? 'PIN protection is enabled.' : 'Set a PIN before using important docs.' }}</p>
            </div>
            <Lock :size="22" />
          </div>
          <label>
            {{ vaultStatus.pin_set ? 'New PIN' : 'PIN' }}
            <input v-model="vaultForm.pin" type="password" minlength="4" maxlength="32" required />
          </label>
          <button class="xb-secondary-button" type="submit">{{ vaultStatus.pin_set ? 'Reset PIN' : 'Set PIN' }}</button>
        </form>

        <div class="xb-panel xb-settings-card">
          <h3>Sessions</h3>
          <div class="xb-row-actions">
            <button class="xb-secondary-button" type="button" @click="logoutCurrent">
              <LogOut :size="16" />
              Log out
            </button>
            <button class="xb-text-button xb-danger-button" type="button" @click="logoutEverywhere">Log out all devices</button>
          </div>
        </div>
      </section>

      <section v-if="activeSection === 'devices'" class="xb-panel xb-settings-card">
        <div class="xb-settings-card-header">
          <div>
            <h3>Trusted devices</h3>
            <p>Review browsers and devices that have signed in.</p>
          </div>
          <Laptop :size="22" />
        </div>
        <article v-for="device in devices" :key="device.id" class="xb-device-row">
          <component :is="device.device_type?.toLowerCase().includes('phone') ? Smartphone : Laptop" :size="22" />
          <div>
            <strong>{{ device.device_name }}</strong>
            <span>{{ device.os_name || device.device_type || 'Unknown OS' }} / {{ device.browser_name || 'Unknown browser' }}</span>
            <span>{{ device.last_ip || 'No IP' }} / {{ formatDate(device.last_seen_at || device.created_at) }}</span>
          </div>
          <button class="xb-icon-button" type="button" :disabled="device.revoked_at" title="Revoke" @click="revokeDevice(device)">
            <XCircle :size="17" />
          </button>
        </article>
        <p v-if="devices.length === 0" class="xb-muted">No devices have been registered yet.</p>
      </section>

      <section v-if="activeSection === 'storage'" class="xb-panel xb-settings-card">
        <div class="xb-settings-card-header">
          <div>
            <h3>Storage</h3>
            <p>Your plan and encrypted storage usage.</p>
          </div>
          <Database :size="22" />
        </div>
        <div class="xb-storage-summary">
          <strong>{{ formatBytes(storage?.used_bytes) }}</strong>
          <span>used of {{ formatBytes(storage?.limit_bytes) }}</span>
          <progress :value="storage?.percent_used || 0" max="100"></progress>
        </div>
        <dl class="xb-settings-facts">
          <div><dt>Plan</dt><dd>{{ authStore.user?.plan || 'internal' }}</dd></div>
          <div><dt>Remaining</dt><dd>{{ formatBytes(storage?.remaining_bytes) }}</dd></div>
          <div><dt>Role</dt><dd>{{ authStore.user?.role || 'user' }}</dd></div>
        </dl>
      </section>

      <section v-if="activeSection === 'appearance'" class="xb-panel xb-settings-card">
        <div class="xb-settings-card-header">
          <div>
            <h3>Appearance</h3>
            <p>Choose the interface theme for this browser.</p>
          </div>
          <Sun v-if="themeStore.mode === 'light'" :size="22" />
          <Moon v-else :size="22" />
        </div>
        <div class="xb-theme-options">
          <button
            type="button"
            :class="{ 'is-active': themeStore.mode === 'dark' }"
            @click="themeStore.setMode('dark')"
          >
            <Moon :size="18" />
            <span>
              <strong>Dark</strong>
              <small>Default XuanBox look</small>
            </span>
          </button>
          <button
            type="button"
            :class="{ 'is-active': themeStore.mode === 'light' }"
            @click="themeStore.setMode('light')"
          >
            <Sun :size="18" />
            <span>
              <strong>Light</strong>
              <small>Higher brightness for daytime use</small>
            </span>
          </button>
        </div>
        <p class="xb-inline-help">Theme preference is saved on this device only. Dark remains the default for new browsers.</p>
      </section>

      <section v-if="activeSection === 'privacy'" class="xb-panel xb-settings-card xb-privacy-notes">
        <h3>Security and privacy notes</h3>
        <p>XuanBox stores uploaded files encrypted at rest and keeps user resources separated by account ownership.</p>
        <p>Administrators manage accounts, quotas, invites, backups, and system health. The product UI does not give admins a way to browse your private file space.</p>
        <p>This deployment is not zero-knowledge yet: the server owns the master key, so the server operator controls the deployment, database, storage, and backups.</p>
        <p>Keep your password and important-docs PIN private. Public links should be treated like keys: anyone with the link and required password can access them until they expire or are cancelled.</p>
      </section>
    </div>
  </section>
</template>
