<script setup>
import { onMounted, ref } from 'vue'
import { CheckCircle2, Mail, RefreshCw } from 'lucide-vue-next'

import PageHeader from '../../components/common/PageHeader.vue'
import { messageApi } from '../../api/messageApi'

const messages = ref([])
const loading = ref(false)
const error = ref('')

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
    error.value = err.response?.data?.error?.message || 'Unable to load messages'
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
  <PageHeader title="Messages" subtitle="System announcements and direct messages from your XuanBox administrator.">
    <button class="xb-secondary-button" type="button" :disabled="loading" @click="loadMessages">
      <RefreshCw :size="16" />
      Refresh
    </button>
  </PageHeader>

  <p v-if="error" class="xb-form-error">{{ error }}</p>

  <section class="xb-panel xb-message-list">
    <article v-for="message in messages" :key="message.id" class="xb-message-card" :class="{ 'is-unread': !message.read_at }">
      <Mail :size="22" />
      <div>
        <strong>{{ message.title }}</strong>
        <span>{{ message.level }} · {{ formatDate(message.created_at) }}</span>
        <p>{{ message.body }}</p>
      </div>
      <button v-if="!message.read_at" class="xb-secondary-button" type="button" @click="markRead(message)">
        <CheckCircle2 :size="16" />
        Mark read
      </button>
    </article>
    <div v-if="!loading && messages.length === 0" class="xb-empty-state">
      <h3>No messages yet</h3>
      <p>System notices and admin messages will appear here.</p>
    </div>
  </section>
</template>
