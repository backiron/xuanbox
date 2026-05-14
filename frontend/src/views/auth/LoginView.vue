<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { KeyRound, UserPlus } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'

import { authApi } from '../../api/authApi'
import XbAssetIcon from '../../components/common/XbAssetIcon.vue'
import { useAuthStore } from '../../stores/authStore'

const router = useRouter()
const authStore = useAuthStore()
const { t } = useI18n()
const mode = ref('login')
const error = ref('')
const loading = ref(false)

const loginForm = reactive({ username_or_email: '', password: '' })
const registerForm = reactive({ username: '', email: '', password: '', display_name: '' })
const inviteForm = reactive({ invite_code: '', username: '', email: '', password: '', display_name: '' })
const ownerForm = reactive({ username: '', email: '', password: '', display_name: '' })
const authSettings = ref({ open_registration_enabled: false, invite_registration_enabled: false, bootstrap_available: false })

const modeTitle = computed(() => ({
  login: t('pages.auth.loginTitle'),
  register: t('pages.auth.registerTitle'),
  invite: t('pages.auth.inviteTitle'),
  owner: t('pages.auth.ownerTitle')
})[mode.value])

function applyTokens(response) {
  authStore.setTokens(response.data.data)
  return authStore.loadMe()
}

async function submit() {
  loading.value = true
  error.value = ''
  try {
    if (mode.value === 'login') {
      await authStore.login({ ...loginForm, device_name: 'Local Browser' })
    } else if (mode.value === 'register') {
      const response = await authApi.register({ ...registerForm, device_name: 'Local Browser' })
      await applyTokens(response)
    } else if (mode.value === 'invite') {
      const response = await authApi.registerByInvite({ ...inviteForm, device_name: 'Local Browser' })
      await applyTokens(response)
    } else {
      const response = await authApi.bootstrapOwner({ ...ownerForm, device_name: 'Local Browser' })
      await applyTokens(response)
    }
    router.push('/')
  } catch (err) {
    error.value = err.response?.data?.error?.message || err.response?.data?.message || t('pages.auth.authFailed')
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  try {
    const response = await authApi.registrationSettings()
    authSettings.value = response.data.data
    if (mode.value === 'owner' && !authSettings.value.bootstrap_available) {
      mode.value = 'login'
    }
    if (mode.value === 'register' && !authSettings.value.open_registration_enabled) {
      mode.value = 'login'
    }
    if (mode.value === 'invite' && !authSettings.value.invite_registration_enabled) {
      mode.value = 'login'
    }
  } catch {
    authSettings.value = { open_registration_enabled: false, invite_registration_enabled: false, bootstrap_available: false }
  }
})
</script>

<template>
  <main class="xb-auth-page">
    <section class="xb-auth-brand">
      <div class="xb-auth-logo">
        <XbAssetIcon name="logo" :size="42" />
        <span>XuanBox</span>
      </div>
      <h1>{{ t('pages.auth.heroTitle') }}</h1>
      <p>{{ t('pages.auth.heroDesc') }}</p>
    </section>
    <form class="xb-login-panel xb-auth-form" @submit.prevent="submit">
      <div class="xb-tabs">
        <button type="button" :class="{ 'is-active': mode === 'login' }" @click="mode = 'login'">{{ t('pages.auth.signInTab') }}</button>
        <button v-if="authSettings.open_registration_enabled" type="button" :class="{ 'is-active': mode === 'register' }" @click="mode = 'register'">
          {{ t('pages.auth.registerTab') }}
        </button>
        <button v-if="authSettings.invite_registration_enabled" type="button" :class="{ 'is-active': mode === 'invite' }" @click="mode = 'invite'">
          {{ t('pages.auth.inviteTab') }}
        </button>
        <button v-if="authSettings.bootstrap_available" type="button" :class="{ 'is-active': mode === 'owner' }" @click="mode = 'owner'">
          {{ t('pages.auth.bootstrapTab') }}
        </button>
      </div>

      <h2>{{ modeTitle }}</h2>

      <template v-if="mode === 'login'">
        <label>{{ t('pages.auth.account') }} <input v-model="loginForm.username_or_email" autocomplete="username" required /></label>
        <label>{{ t('pages.auth.password') }} <input v-model="loginForm.password" type="password" autocomplete="current-password" required /></label>
      </template>

      <template v-else-if="mode === 'register'">
        <label>{{ t('pages.auth.username') }} <input v-model="registerForm.username" minlength="3" required /></label>
        <label>{{ t('pages.auth.email') }} <input v-model="registerForm.email" type="email" required /></label>
        <label>{{ t('pages.auth.displayName') }} <input v-model="registerForm.display_name" /></label>
        <label>{{ t('pages.auth.password') }} <input v-model="registerForm.password" type="password" minlength="10" required /></label>
      </template>

      <template v-else-if="mode === 'invite'">
        <label>{{ t('pages.auth.inviteTab') }} <input v-model="inviteForm.invite_code" required /></label>
        <label>{{ t('pages.auth.username') }} <input v-model="inviteForm.username" minlength="3" required /></label>
        <label>{{ t('pages.auth.email') }} <input v-model="inviteForm.email" type="email" required /></label>
        <label>{{ t('pages.auth.displayName') }} <input v-model="inviteForm.display_name" /></label>
        <label>{{ t('pages.auth.password') }} <input v-model="inviteForm.password" type="password" minlength="10" required /></label>
      </template>

      <template v-else>
        <label>{{ t('pages.auth.username') }} <input v-model="ownerForm.username" minlength="3" required /></label>
        <label>{{ t('pages.auth.email') }} <input v-model="ownerForm.email" type="email" required /></label>
        <label>{{ t('pages.auth.displayName') }} <input v-model="ownerForm.display_name" /></label>
        <label>{{ t('pages.auth.password') }} <input v-model="ownerForm.password" type="password" minlength="10" required /></label>
      </template>

      <p v-if="error" class="xb-form-error">{{ error }}</p>
      <button class="xb-primary-button" type="submit" :disabled="loading">
        <component :is="mode === 'login' ? KeyRound : UserPlus" :size="16" />
        {{ loading ? t('pages.auth.working') : (mode === 'login' ? t('pages.auth.loginTitle') : t('common.actions.continue')) }}
      </button>
    </form>
  </main>
</template>
