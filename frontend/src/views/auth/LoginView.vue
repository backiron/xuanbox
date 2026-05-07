<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { Archive } from 'lucide-vue-next'
import { useAuthStore } from '../../stores/authStore'

const router = useRouter()
const authStore = useAuthStore()
const usernameOrEmail = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function submit() {
  loading.value = true
  error.value = ''
  try {
    await authStore.login({
      username_or_email: usernameOrEmail.value,
      password: password.value,
      device_name: 'Local Browser'
    })
    router.push('/')
  } catch (err) {
    error.value = err.response?.data?.message || 'Login failed'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <main class="xb-auth-page">
    <section class="xb-auth-brand">
      <div class="xb-auth-logo">
        <Archive :size="34" />
        <span>XuanBox 玄匣</span>
      </div>
      <h1>Your Private Digital Vault</h1>
      <p>Photos, files, receipts and documents. Securely stored in your own cloud.</p>
    </section>
    <form class="xb-login-panel" @submit.prevent="submit">
      <h2>Sign in</h2>
      <label>
        Account
        <input v-model="usernameOrEmail" autocomplete="username" />
      </label>
      <label>
        Password
        <input v-model="password" type="password" autocomplete="current-password" />
      </label>
      <p v-if="error" class="xb-form-error">{{ error }}</p>
      <button class="xb-primary-button" type="submit" :disabled="loading">
        {{ loading ? 'Signing in' : 'Sign in' }}
      </button>
    </form>
  </main>
</template>
