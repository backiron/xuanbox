<script setup>
import { onMounted, ref } from 'vue'
import { CheckCircle2, Mail, RefreshCw } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'

import PageHeader from '../../components/common/PageHeader.vue'
import { messageApi } from '../../api/messageApi'

const messages = ref([])
const loading = ref(false)
const error = ref('')
const { t } = useI18n()

function formatDate(value) {
  if (!value) return ''
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))
}

async function loadMessages() {
  loading.value = true
  error.value = ''
  try {
    const response = await messageApi.list()
    messages.value = response.data.data
  } catch (err) {
    error.value = err.response?.data?.error?.message || t('pages.messages.noMessages')
  } finally {
    loading.value = false
  }
}

async function markRead(message) {
  await messageApi.markRead(message.id)
  await loadMessages()
}

onMounted(loadMessages)
</script>

<template>
  <PageHeader :title="t('pages.messages.title')" :subtitle="t('pages.messages.subtitle')">
    <button class="xb-secondary-button" type="button" :disabled="loading" @click="loadMessages">
      <RefreshCw :size="16" />
      {{ t('common.actions.refresh') }}
    </button>
  </PageHeader>

  <p v-if="error" class="xb-form-error">{{ error }}</p>

  <section class="xb-panel xb-message-list">
    <article v-for="message in messages" :key="message.id" class="xb-message-card" :class="{ 'is-unread': !message.read_at }">
      <Mail :size="22" />
      <div>
        <strong>{{ message.title }}</strong>
        <span>{{ message.level }} / {{ formatDate(message.created_at) }}</span>
        <p>{{ message.body }}</p>
      </div>
      <button v-if="!message.read_at" class="xb-secondary-button" type="button" @click="markRead(message)">
        <CheckCircle2 :size="16" />
        {{ t('pages.messages.markRead') }}
      </button>
    </article>
    <div v-if="!loading && messages.length === 0" class="xb-empty-state">
      <h3>{{ t('pages.messages.noMessages') }}</h3>
      <p>{{ t('pages.messages.noMessagesDesc') }}</p>
    </div>
  </section>
</template>
