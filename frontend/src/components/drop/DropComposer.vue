<script setup>
import { computed, nextTick, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Paperclip, SendHorizontal } from 'lucide-vue-next'

const props = defineProps({
  disabled: { type: Boolean, default: false },
  targets: { type: Array, default: () => [] },
  target: { type: String, default: '' }
})
const emit = defineEmits(['send-text', 'send-files', 'update:target'])
const { t } = useI18n()

const text = ref('')
const input = ref(null)
const fileInput = ref(null)
const isTouch = window.matchMedia('(pointer: coarse)').matches
const placeholder = computed(() => (isTouch ? t('pages.xuandrop.inputPlaceholderMobile') : t('pages.xuandrop.inputPlaceholder')))

function resize() {
  const element = input.value
  if (!element) return
  element.style.height = 'auto'
  element.style.height = `${Math.min(element.scrollHeight, 160)}px`
}

async function submit() {
  const body = text.value.trim()
  if (!body || props.disabled) return
  emit('send-text', body)
  text.value = ''
  await nextTick()
  resize()
}

function onKeydown(event) {
  // Desktop: Enter sends, Shift+Enter adds a line. Phones keep Enter for new lines.
  if (event.key === 'Enter' && !event.shiftKey && !isTouch && !event.isComposing) {
    event.preventDefault()
    submit()
  }
}

function onPaste(event) {
  const files = Array.from(event.clipboardData?.files || [])
  if (files.length) {
    event.preventDefault()
    emit('send-files', files)
  }
}

function onFiles(event) {
  const files = Array.from(event.target.files || [])
  if (files.length) emit('send-files', files)
  event.target.value = ''
}
</script>

<template>
  <div class="xd-composer">
    <label v-if="targets.length" class="xd-target">
      <span>{{ t('pages.xuandrop.sendTo') }}</span>
      <select :value="target" @change="emit('update:target', $event.target.value)">
        <option value="">{{ t('pages.xuandrop.allDevices') }}</option>
        <option v-for="device in targets" :key="device.id" :value="device.id">
          {{ device.device_name }}{{ device.online ? ` · ${t('pages.xuandrop.online')}` : '' }}
        </option>
      </select>
    </label>
    <div class="xd-composer-row">
      <button type="button" class="xd-round-button" :disabled="disabled" :aria-label="t('pages.xuandrop.attach')" @click="fileInput?.click()">
        <Paperclip :size="20" />
      </button>
      <input ref="fileInput" type="file" multiple hidden @change="onFiles" />
      <textarea
        ref="input"
        v-model="text"
        rows="1"
        :placeholder="placeholder"
        :disabled="disabled"
        @input="resize"
        @keydown="onKeydown"
        @paste="onPaste"
      />
      <button type="button" class="xd-round-button is-primary" :disabled="disabled || !text.trim()" :aria-label="t('pages.xuandrop.send')" @click="submit">
        <SendHorizontal :size="20" />
      </button>
    </div>
  </div>
</template>
