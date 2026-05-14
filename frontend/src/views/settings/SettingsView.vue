<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import {
  Camera,
  Database,
  ExternalLink,
  Info,
  Lock,
  LogOut,
  Moon,
  KeyRound,
  Laptop,
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
import { setLocale } from '../../i18n'

const router = useRouter()
const authStore = useAuthStore()
const dialog = useDialogStore()
const themeStore = useThemeStore()
const { t, locale } = useI18n()
const appVersion = '0.1.0'

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

const sections = computed(() => ([
  { key: 'profile', label: t('pages.settings.sectionLabel.profile'), icon: UserRound },
  { key: 'security', label: t('pages.settings.sectionLabel.security'), icon: ShieldCheck },
  { key: 'devices', label: t('pages.settings.sectionLabel.devices'), icon: Laptop },
  { key: 'storage', label: t('pages.settings.sectionLabel.storage'), icon: Database },
  { key: 'appearance', label: t('pages.settings.sectionLabel.appearance'), icon: Moon },
  { key: 'privacy', label: t('pages.settings.sectionLabel.notes'), icon: Lock },
  { key: 'about', label: t('pages.settings.sectionLabel.about'), icon: Info }
]))

const localeOptions = [
  { value: 'en', label: t('common.language.en') },
  { value: 'zh-CN', label: t('common.language.zhCN') }
]

const initials = computed(() => {
  const name = authStore.user?.display_name || authStore.user?.username || 'XB'
  return name.slice(0, 2).toUpperCase()
})

const privacyNotes = computed(() => [
  t('pages.settings.privacyText.0'),
  t('pages.settings.privacyText.1'),
  t('pages.settings.privacyText.2'),
  t('pages.settings.privacyText.3')
])

function formatBytes(value) {
  if (value == null) return t('pages.settings.unlimited')
  if (!value) return t('common.file.noSize')
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
  if (!value) return t('pages.settings.neverSeen')
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
    error.value = err.response?.data?.error?.message || t('pages.settings.loadFailed')
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
    message.value = t('pages.settings.profileUpdated')
  } catch (err) {
    error.value = err.response?.data?.error?.message || t('pages.settings.profileError')
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
    message.value = t('pages.settings.avatarUpdated')
  } catch (err) {
    error.value = err.response?.data?.error?.message || t('pages.settings.avatarError')
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
    error.value = err.response?.data?.error?.message || t('pages.settings.passwordError')
  }
}

async function setupVaultPin() {
  message.value = ''
  error.value = ''
  try {
    await importantDocApi.setup(vaultForm.pin)
    vaultForm.pin = ''
    await loadVaultStatus()
    message.value = t('pages.settings.pinEnabled')
  } catch (err) {
    error.value = err.response?.data?.error?.message || t('pages.settings.pinError')
  }
}

async function revokeDevice(device) {
  const confirmed = await dialog.confirm({
    title: t('pages.settings.revokeDeviceTitle'),
    message: t('pages.settings.revokeDeviceMessage', { name: device.device_name }),
    confirmText: t('pages.settings.revoke'),
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
    title: t('pages.settings.logoutAllTitle'),
    message: t('pages.settings.logoutAllMessage'),
    confirmText: t('pages.settings.logoutAllButton'),
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

function setAppLocale(next) {
  if (!next || next === locale.value) return
  setLocale(next)
}

onMounted(loadAll)
</script>

<template>
  <PageHeader :title="t('pages.settings.title')" :subtitle="t('pages.settings.subtitle')">
    <button class="xb-secondary-button" type="button" :disabled="loading" @click="loadAll">
      <RefreshCw :size="16" />
      {{ t('common.actions.refresh') }}
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
            <h3>{{ t('pages.settings.profile') }}</h3>
            <p>{{ t('pages.settings.profileIntro') }}</p>
          </div>
          <label class="xb-secondary-button xb-avatar-upload">
            <Camera :size="16" />
            {{ t('pages.settings.avatar') }}
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
              {{ t('pages.settings.displayName') }}
              <input v-model="profileForm.display_name" maxlength="120" />
            </label>
            <label>
              {{ t('pages.settings.email') }}
              <input v-model="profileForm.email" type="email" required />
            </label>
            <div class="xb-row-actions">
              <button class="xb-primary-button" type="submit">{{ t('pages.settings.saveProfile') }}</button>
            </div>
          </form>
        </div>
      </section>

      <section v-if="activeSection === 'security'" class="xb-settings-stack">
        <form class="xb-panel xb-settings-card xb-settings-form" @submit.prevent="changePassword">
          <div class="xb-settings-card-header">
            <div>
              <h3>{{ t('pages.settings.password') }}</h3>
              <p>{{ t('pages.settings.passwordHint') }}</p>
            </div>
            <KeyRound :size="22" />
          </div>
          <label>
            {{ t('pages.settings.currentPassword') }}
            <input v-model="passwordForm.old_password" type="password" autocomplete="current-password" required />
          </label>
          <label>
            {{ t('pages.settings.newPassword') }}
            <input v-model="passwordForm.new_password" type="password" minlength="10" autocomplete="new-password" required />
          </label>
          <button class="xb-primary-button" type="submit">{{ t('pages.settings.changePassword') }}</button>
        </form>

        <form class="xb-panel xb-settings-card xb-settings-form" @submit.prevent="setupVaultPin">
          <div class="xb-settings-card-header">
            <div>
              <h3>{{ t('pages.settings.importantDocsPin') }}</h3>
              <p>{{ vaultStatus.pin_set ? t('pages.settings.pinEnabled') : t('pages.settings.pinSetupHint') }}</p>
            </div>
            <Lock :size="22" />
          </div>
          <label>
            {{ vaultStatus.pin_set ? t('pages.settings.pinLabelNew') : t('pages.settings.pinLabel') }}
            <input v-model="vaultForm.pin" type="password" minlength="4" maxlength="32" required />
          </label>
          <button class="xb-secondary-button" type="submit">{{ vaultStatus.pin_set ? t('common.buttons.resetPin') : t('common.buttons.setPin') }}</button>
        </form>

        <div class="xb-panel xb-settings-card">
          <h3>{{ t('pages.settings.sessions') }}</h3>
          <div class="xb-row-actions">
            <button class="xb-secondary-button" type="button" @click="logoutCurrent">
              <LogOut :size="16" />
              {{ t('pages.settings.logout') }}
            </button>
            <button class="xb-text-button xb-danger-button" type="button" @click="logoutEverywhere">{{ t('pages.settings.logoutAll') }}</button>
          </div>
        </div>

        <div class="xb-panel xb-settings-card">
          <h3>{{ t('pages.settings.languageTitle') }}</h3>
          <label>
            {{ t('common.language.label') }}
            <select :value="locale" @change="setAppLocale($event.target.value)">
              <option v-for="option in localeOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
            </select>
          </label>
        </div>
      </section>

      <section v-if="activeSection === 'devices'" class="xb-panel xb-settings-card">
        <div class="xb-settings-card-header">
          <div>
            <h3>{{ t('pages.settings.trustedDevices') }}</h3>
            <p>{{ t('pages.settings.trustedHint') }}</p>
          </div>
          <Laptop :size="22" />
        </div>
        <article v-for="device in devices" :key="device.id" class="xb-device-row">
          <component :is="device.device_type?.toLowerCase().includes('phone') ? Smartphone : Laptop" :size="22" />
          <div>
            <strong>{{ device.device_name }}</strong>
            <span>{{ device.os_name || device.device_type || t('pages.settings.noOS') }} / {{ device.browser_name || t('pages.settings.noBrowser') }}</span>
            <span>{{ device.last_ip || t('pages.settings.unknownIP') }} / {{ formatDate(device.last_seen_at || device.created_at) }}</span>
          </div>
          <button class="xb-icon-button" type="button" :disabled="device.revoked_at" :title="t('pages.settings.revoke')" @click="revokeDevice(device)">
            <XCircle :size="17" />
          </button>
        </article>
        <p v-if="devices.length === 0" class="xb-muted">{{ t('pages.settings.noDevices') }}</p>
      </section>

      <section v-if="activeSection === 'storage'" class="xb-panel xb-settings-card">
        <div class="xb-settings-card-header">
          <div>
            <h3>{{ t('pages.settings.storage') }}</h3>
            <p>{{ t('pages.settings.storageHint') }}</p>
          </div>
          <Database :size="22" />
        </div>
        <div class="xb-storage-summary">
          <strong>{{ formatBytes(storage?.used_bytes) }}</strong>
          <span>{{ t('pages.settings.usedOf', { total: formatBytes(storage?.limit_bytes) }) }}</span>
          <progress :value="storage?.percent_used || 0" max="100"></progress>
        </div>
        <dl class="xb-settings-facts">
          <div><dt>{{ t('pages.settings.planLabel') }}</dt><dd>{{ authStore.user?.plan || t('pages.files.importantSubtitle') }}</dd></div>
          <div><dt>{{ t('pages.settings.remainingLabel') }}</dt><dd>{{ formatBytes(storage?.remaining_bytes) }}</dd></div>
          <div><dt>{{ t('pages.settings.roleLabel') }}</dt><dd>{{ authStore.user?.role || t('pages.auth.account') }}</dd></div>
        </dl>
      </section>

      <section v-if="activeSection === 'appearance'" class="xb-panel xb-settings-card">
        <div class="xb-settings-card-header">
          <div>
            <h3>{{ t('pages.settings.appearance') }}</h3>
            <p>{{ t('pages.settings.appearanceHint') }}</p>
          </div>
          <Sun v-if="themeStore.mode === 'light'" :size="22" />
          <Moon v-else :size="22" />
        </div>
        <div class="xb-theme-options">
          <button type="button" :class="{ 'is-active': themeStore.mode === 'dark' }" @click="themeStore.setMode('dark')">
            <Moon :size="18" />
            <span>
              <strong>{{ t('pages.settings.themeDark') }}</strong>
              <small>{{ t('pages.settings.themeDarkHint') }}</small>
            </span>
          </button>
          <button type="button" :class="{ 'is-active': themeStore.mode === 'light' }" @click="themeStore.setMode('light')">
            <Sun :size="18" />
            <span>
              <strong>{{ t('pages.settings.themeLight') }}</strong>
              <small>{{ t('pages.settings.themeLightHint') }}</small>
            </span>
          </button>
        </div>
        <p class="xb-inline-help">{{ t('pages.settings.themeSavedHint') }}</p>
      </section>

      <section v-if="activeSection === 'privacy'" class="xb-panel xb-settings-card xb-privacy-notes">
        <h3>{{ t('pages.settings.privacyNotes') }}</h3>
        <p v-for="(line, index) in privacyNotes" :key="index">{{ line }}</p>
      </section>

      <section v-if="activeSection === 'about'" class="xb-settings-stack">
        <div class="xb-panel xb-settings-card">
          <div class="xb-settings-card-header">
            <div>
              <h3>{{ t('pages.settings.aboutTitle') }}</h3>
              <p>{{ t('pages.settings.aboutSubtitle') }}</p>
            </div>
            <Info :size="22" />
          </div>
          <dl class="xb-settings-facts xb-about-facts">
            <div><dt>{{ t('pages.settings.aboutProduct') }}</dt><dd>XuanBox</dd></div>
            <div><dt>{{ t('pages.settings.aboutVersion') }}</dt><dd>{{ appVersion }}</dd></div>
            <div><dt>{{ t('pages.settings.aboutMaintainer') }}</dt><dd>VIANBENI</dd></div>
            <div><dt>{{ t('pages.settings.aboutLicense') }}</dt><dd>AGPL-3.0</dd></div>
          </dl>
          <div class="xb-about-links">
            <a href="https://vianbeni.ca" target="_blank" rel="noreferrer">
              <ExternalLink :size="15" />
              {{ t('pages.settings.aboutWebsite') }}
            </a>
            <a href="https://github.com/keikozhang57/xuanbox" target="_blank" rel="noreferrer">
              <ExternalLink :size="15" />
              {{ t('pages.settings.aboutSource') }}
            </a>
            <a href="mailto:xuanbox@vianbeni.ca">
              <ExternalLink :size="15" />
              xuanbox@vianbeni.ca
            </a>
          </div>
        </div>

        <div class="xb-panel xb-settings-card xb-privacy-notes">
          <h3>{{ t('pages.settings.openSourceTitle') }}</h3>
          <p>{{ t('pages.settings.openSourceText') }}</p>
          <p>{{ t('pages.settings.commercialText') }}</p>
          <p>{{ t('pages.settings.trademarkText') }}</p>
          <p>{{ t('pages.settings.securityModelText') }}</p>
        </div>
      </section>
    </div>
  </section>
</template>
