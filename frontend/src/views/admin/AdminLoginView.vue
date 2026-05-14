<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ShieldCheck } from 'lucide-vue-next'

import { authApi } from '../../api/authApi'
import XbAssetIcon from '../../components/common/XbAssetIcon.vue'
import { useAuthStore } from '../../stores/authStore'

const router = useRouter()
const authStore = useAuthStore()
const form = reactive({ username_or_email: '', password: '' })
const loading = ref(false)
const error = ref('')

async function submit() {
  loading.value = true
  error.value = ''
  try {
    const response = await authApi.adminLogin({ ...form, device_name: 'Admin Console' })
    authStore.setTokens(response.data.data)
    await authStore.loadMe()
    await router.push('/admin-console')
  } catch (err) {
    error.value = err.response?.data?.error?.message || 'Admin sign in failed'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <main class="xb-auth-page xb-admin-auth-page">
    <section class="xb-auth-brand">
      <div class="xb-auth-logo">
        <XbAssetIcon name="logo" :size="42" />
        <span>XuanBox</span>
      </div>
      <h1>Admin Console</h1>
      <p>System management for users, quotas, invites, backups, audits, and worker health.</p>
    </section>

    <form class="xb-login-panel xb-auth-form" @submit.prevent="submit">
      <h2>Admin sign in</h2>
      <label>Admin account <input v-model="form.username_or_email" autocomplete="username" required /></label>
      <label>Password <input v-model="form.password" type="password" autocomplete="current-password" required /></label>
      <p v-if="error" class="xb-form-error">{{ error }}</p>
      <button class="xb-primary-button" type="submit" :disabled="loading">
        <ShieldCheck :size="16" />
        {{ loading ? 'Checking...' : 'Open admin console' }}
      </button>
      <router-link class="xb-text-button" to="/login">User sign in</router-link>
    </form>
  </main>
</template>
