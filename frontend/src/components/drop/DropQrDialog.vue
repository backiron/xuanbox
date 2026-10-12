<script setup>
import { ref } from 'vue'
import QRCode from 'qrcode'
import { useI18n } from 'vue-i18n'
import { Copy, QrCode, X } from 'lucide-vue-next'
import { dropApi } from '../../api/dropApi'

const emit = defineEmits(['close'])
const { t } = useI18n()
const MINUTES = 30

const link = ref('')
const qr = ref('')
const busy = ref(false)
const copied = ref(false)
const error = ref('')
const configuredPublicOrigin = (import.meta.env.VITE_DROP_PUBLIC_ORIGIN || '').replace(/\/$/, '')

async function create() {
  busy.value = true
  error.value = ''
  try {
    const response = await dropApi.createSession({ title: 'XuanDrop', expires_in_minutes: MINUTES })
    const token = response.data.data.public_token || response.data.data.token
    link.value = `${configuredPublicOrigin || window.location.origin}/drop/public/${token}`
    qr.value = await QRCode.toDataURL(link.value, { width: 220, margin: 2, errorCorrectionLevel: 'M' })
  } catch (err) {
    error.value = err.response?.data?.message || t('pages.xuandrop.loadFailed')
  } finally {
    busy.value = false
  }
}

async function copyLink() {
  await navigator.clipboard.writeText(link.value)
  copied.value = true
  window.setTimeout(() => { copied.value = false }, 1500)
}
</script>

<template>
  <div class="xd-overlay" @click.self="emit('close')">
    <div class="xd-dialog">
      <header>
        <strong>{{ t('pages.xuandrop.qrTitle') }}</strong>
        <button type="button" class="xd-icon-only" :aria-label="t('common.actions.close')" @click="emit('close')"><X :size="18" /></button>
      </header>
      <p class="xd-hint">{{ t('pages.xuandrop.qrHint', { minutes: MINUTES }) }}</p>
      <div v-if="qr" class="xd-qr">
        <img :src="qr" alt="QR" />
        <button type="button" class="xb-secondary-button" @click="copyLink">
          <Copy :size="16" />{{ copied ? t('pages.xuandrop.copied') : t('pages.xuandrop.copyLink') }}
        </button>
      </div>
      <button v-else type="button" class="xb-primary-button" :disabled="busy" @click="create">
        <QrCode :size="16" />{{ t('pages.xuandrop.qrCreate') }}
      </button>
      <p v-if="error" class="xd-error">{{ error }}</p>
    </div>
  </div>
</template>
