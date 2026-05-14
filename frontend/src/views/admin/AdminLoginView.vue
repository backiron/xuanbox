<script setup>
import { computed, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ShieldCheck } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'

import { authApi } from '../../api/authApi'
import XbAssetIcon from '../../components/common/XbAssetIcon.vue'
import { setLocale } from '../../i18n'
import { useAuthStore } from '../../stores/authStore'

const router = useRouter()
const authStore = useAuthStore()
const { t, locale } = useI18n()
const form = reactive({ username_or_email: '', password: '' })
const loading = ref(false)
const error = ref('')
const currentLocaleLabel = computed(() => locale.value === 'zh-CN' ? '中' : 'EN')
const localeTitle = computed(() => locale.value === 'zh-CN' ? '切换到英文' : 'Switch to Chinese')

async function submit() {
  loading.value = true
  error.value = ''
  try {
    const response = await authApi.adminLogin({ ...form, device_name: 'Admin Console' })
    authStore.setTokens(response.data.data)
    await authStore.loadMe()
    await router.push('/admin-console')
  } catch (err) {
    error.value = err.response?.data?.error?.message || t('pages.adminAuth.failed')
  } finally {
    loading.value = false
  }
}

function toggleLocale() {
  setLocale(locale.value === 'zh-CN' ? 'en' : 'zh-CN')
}
</script>

<template>
  <main class="xb-auth-page xb-admin-auth-page">
    <button class="xb-language-toggle xb-auth-language-toggle" type="button" :title="localeTitle" @click="toggleLocale">
      {{ currentLocaleLabel }}
    </button>
    <section class="xb-auth-brand">
      <div class="xb-auth-logo">
        <XbAssetIcon name="logo" :size="42" />
        <span>XuanBox</span>
      </div>
      <h1>{{ t('pages.adminAuth.title') }}</h1>
      <p>{{ t('pages.adminAuth.subtitle') }}</p>
    </section>

    <form class="xb-login-panel xb-auth-form" @submit.prevent="submit">
      <h2>{{ t('pages.adminAuth.signInTitle') }}</h2>
      <label>{{ t('pages.auth.account') }} <input v-model="form.username_or_email" autocomplete="username" required /></label>
      <label>{{ t('pages.auth.password') }} <input v-model="form.password" type="password" autocomplete="current-password" required /></label>
      <p v-if="error" class="xb-form-error">{{ error }}</p>
      <button class="xb-primary-button" type="submit" :disabled="loading">
        <ShieldCheck :size="16" />
        {{ loading ? t('pages.adminAuth.checking') : t('common.actions.openAdminConsole') }}
      </button>
      <router-link class="xb-text-button" to="/login">{{ t('pages.adminAuth.userSignIn') }}</router-link>
    </form>
  </main>
</template>
