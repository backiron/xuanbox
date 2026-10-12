<script setup>
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { UserPlus, X } from 'lucide-vue-next'
import { dropChatApi } from '../../api/dropChatApi'
import { useDialogStore } from '../../stores/dialogStore'

const props = defineProps({
  contacts: { type: Array, default: () => [] }
})
const emit = defineEmits(['changed', 'open'])
const { t } = useI18n()
const dialog = useDialogStore()

const identifier = ref('')
const busy = ref(false)
const notice = ref('')
const error = ref('')

const incoming = computed(() => props.contacts.filter((contact) => contact.status === 'pending' && contact.direction === 'incoming'))
const outgoing = computed(() => props.contacts.filter((contact) => contact.status === 'pending' && contact.direction === 'outgoing'))

function errorMessage(err) {
  return err.response?.data?.message || t('pages.xuandrop.loadFailed')
}

async function addContact() {
  const value = identifier.value.trim()
  if (!value || busy.value) return
  busy.value = true
  error.value = ''
  notice.value = ''
  try {
    const response = await dropChatApi.requestContact(value)
    identifier.value = ''
    notice.value = response.data.data.status === 'accepted' ? '' : t('pages.xuandrop.requestSent')
    emit('changed')
  } catch (err) {
    error.value = errorMessage(err)
  } finally {
    busy.value = false
  }
}

async function respond(contact, accept) {
  try {
    await (accept ? dropChatApi.acceptContact(contact.id) : dropChatApi.declineContact(contact.id))
    emit('changed')
  } catch (err) {
    error.value = errorMessage(err)
  }
}

async function remove(contact) {
  const confirmed = await dialog.confirm({
    title: t('pages.xuandrop.removeContact'),
    message: t('pages.xuandrop.removeContactConfirm'),
    danger: true
  })
  if (!confirmed) return
  await dropChatApi.removeContact(contact.id)
  emit('changed')
}
</script>

<template>
  <section class="xd-contacts">
    <form class="xd-add-contact" @submit.prevent="addContact">
      <input v-model="identifier" :placeholder="t('pages.xuandrop.addContactLabel')" autocomplete="off" autocapitalize="off" />
      <button type="submit" class="xd-round-button is-primary" :disabled="busy || !identifier.trim()" :aria-label="t('pages.xuandrop.addContact')">
        <UserPlus :size="18" />
      </button>
    </form>
    <p class="xd-hint">{{ notice || t('pages.xuandrop.addContactHint') }}</p>
    <p v-if="error" class="xd-error">{{ error }}</p>

    <div v-if="incoming.length" class="xd-requests">
      <strong>{{ t('pages.xuandrop.incomingRequests') }}</strong>
      <div v-for="contact in incoming" :key="contact.id" class="xd-request">
        <span>{{ contact.peer?.display_name }} <small>@{{ contact.peer?.username }}</small></span>
        <button type="button" class="xb-primary-button" @click="respond(contact, true)">{{ t('pages.xuandrop.accept') }}</button>
        <button type="button" class="xb-text-button" @click="respond(contact, false)">{{ t('pages.xuandrop.decline') }}</button>
      </div>
    </div>

    <div v-for="contact in outgoing" :key="contact.id" class="xd-request is-muted">
      <span>{{ contact.peer?.display_name }} <small>@{{ contact.peer?.username }}</small></span>
      <small>{{ t('pages.xuandrop.waiting') }}</small>
      <button type="button" class="xd-icon-only" :aria-label="t('pages.xuandrop.removeContact')" @click="remove(contact)"><X :size="16" /></button>
    </div>
  </section>
</template>
