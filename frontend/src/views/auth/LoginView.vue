<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { KeyRound, UserPlus } from 'lucide-vue-next'
import { authApi } from '../../api/authApi'
import XbAssetIcon from '../../components/common/XbAssetIcon.vue'
import { useAuthStore } from '../../stores/authStore'

const router = useRouter()
const authStore = useAuthStore()
const mode = ref('login')
const error = ref('')
const loading = ref(false)

const loginForm = reactive({ username_or_email: '', password: '' })
const registerForm = reactive({ username: '', email: '', password: '', display_name: '' })
const inviteForm = reactive({ invite_code: '', username: '', email: '', password: '', display_name: '' })
const ownerForm = reactive({ username: '', email: '', password: '', display_name: '' })
const authSettings = ref({ open_registration_enabled: false, invite_registration_enabled: true })

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
    error.value = err.response?.data?.error?.message || err.response?.data?.message || 'Authentication failed'
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  try {
    const response = await authApi.registrationSettings()
    authSettings.value = response.data.data
  } catch {
    authSettings.value = { open_registration_enabled: false, invite_registration_enabled: true }
  }
})
</script>

<template>
  <main class="xb-auth-page">
    <section class="xb-auth-brand">
      <div class="xb-auth-logo">
        <XbAssetIcon name="logo" :size="42" />
        <span>XuanBox 玄匣</span>
      </div>
      <h1>Your Private Digital Vault</h1>
      <p>Photos, files, receipts and documents. Securely stored in your own encrypted workspace.</p>
    </section>
    <form class="xb-login-panel xb-auth-form" @submit.prevent="submit">
      <div class="xb-tabs">
        <button type="button" :class="{ 'is-active': mode === 'login' }" @click="mode = 'login'">Sign in</button>
        <button v-if="authSettings.open_registration_enabled" type="button" :class="{ 'is-active': mode === 'register' }" @click="mode = 'register'">Register</button>
        <button v-if="authSettings.invite_registration_enabled" type="button" :class="{ 'is-active': mode === 'invite' }" @click="mode = 'invite'">Invite</button>
        <button type="button" :class="{ 'is-active': mode === 'owner' }" @click="mode = 'owner'">Bootstrap</button>
      </div>

      <h2>{{ mode === 'login' ? 'Sign in' : mode === 'register' ? 'Create account' : mode === 'invite' ? 'Register by invite' : 'Create owner' }}</h2>

      <template v-if="mode === 'login'">
        <label>Account <input v-model="loginForm.username_or_email" autocomplete="username" required /></label>
        <label>Password <input v-model="loginForm.password" type="password" autocomplete="current-password" required /></label>
      </template>

      <template v-else-if="mode === 'register'">
        <label>Username <input v-model="registerForm.username" minlength="3" required /></label>
        <label>Email <input v-model="registerForm.email" type="email" required /></label>
        <label>Display name <input v-model="registerForm.display_name" /></label>
        <label>Password <input v-model="registerForm.password" type="password" minlength="10" required /></label>
      </template>

      <template v-else-if="mode === 'invite'">
        <label>Invite code <input v-model="inviteForm.invite_code" required /></label>
        <label>Username <input v-model="inviteForm.username" minlength="3" required /></label>
        <label>Email <input v-model="inviteForm.email" type="email" required /></label>
        <label>Display name <input v-model="inviteForm.display_name" /></label>
        <label>Password <input v-model="inviteForm.password" type="password" minlength="10" required /></label>
      </template>

      <template v-else>
        <label>Username <input v-model="ownerForm.username" minlength="3" required /></label>
        <label>Email <input v-model="ownerForm.email" type="email" required /></label>
        <label>Display name <input v-model="ownerForm.display_name" /></label>
        <label>Password <input v-model="ownerForm.password" type="password" minlength="10" required /></label>
      </template>

      <p v-if="error" class="xb-form-error">{{ error }}</p>
      <button class="xb-primary-button" type="submit" :disabled="loading">
        <component :is="mode === 'login' ? KeyRound : UserPlus" :size="16" />
        {{ loading ? 'Working...' : mode === 'login' ? 'Sign in' : 'Continue' }}
      </button>
    </form>
  </main>
</template>
