<script setup>
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Check, Copy, Download, ExternalLink, FileText, FolderInput, Share, Trash2 } from 'lucide-vue-next'
import { NATIVE_DOWNLOAD_FROM_BYTES, cachedFile, canShareFile, deliverFile, downloadNatively, fetchMessageFile, formatSize, isAppleMobile, splitLinks, thumbnailUrl } from '../../utils/dropMedia'

const props = defineProps({
  message: { type: Object, required: true },
  mine: { type: Boolean, default: false },
  senderLabel: { type: String, default: '' },
  targetLabel: { type: String, default: '' },
  read: { type: Boolean, default: false },
  canDelete: { type: Boolean, default: false },
  saving: { type: Boolean, default: false }
})
const emit = defineEmits(['preview', 'save', 'delete'])
const { t } = useI18n()

const thumb = ref('')
const copied = ref(false)
const fetching = ref(false)
const progress = ref(0)
const readyFile = ref(null)
const libraryMenu = ref(false)

const isImage = computed(() => props.message.kind === 'file' && props.message.has_thumbnail)
const parts = computed(() => splitLinks(props.message.body))
const firstLink = computed(() => parts.value.find((part) => part.isLink)?.text || '')
const time = computed(() => new Date(props.message.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }))
const expiryText = computed(() => {
  // Rounded so a few seconds of clock difference between devices does not show 8 days.
  const days = Math.round((new Date(props.message.expires_at) - Date.now()) / 86400000)
  return days > 1 ? t('pages.xuandrop.expiresIn', { days }) : t('pages.xuandrop.expiresToday')
})
const thumbStyle = computed(() => {
  const { image_width: width, image_height: height } = props.message
  return width && height ? { aspectRatio: `${width} / ${height}` } : {}
})

onMounted(async () => {
  if (isImage.value) {
    try {
      thumb.value = await thumbnailUrl(props.message.id)
    } catch {
      thumb.value = ''
    }
  }
  readyFile.value = cachedFile(props.message.id)
})

async function copyText() {
  try {
    await navigator.clipboard.writeText(props.message.body || '')
  } catch {
    const area = document.createElement('textarea')
    area.value = props.message.body || ''
    document.body.appendChild(area)
    area.select()
    document.execCommand('copy')
    area.remove()
  }
  copied.value = true
  window.setTimeout(() => { copied.value = false }, 1500)
}

const isLarge = computed(() => (props.message.file_size || 0) >= NATIVE_DOWNLOAD_FROM_BYTES)

async function saveToDevice() {
  if (isLarge.value) {
    fetching.value = true
    try {
      await downloadNatively(props.message)
    } finally {
      fetching.value = false
    }
    return
  }
  if (readyFile.value) {
    await deliverFile(readyFile.value)
    return
  }
  fetching.value = true
  progress.value = 0
  try {
    const file = await fetchMessageFile(props.message, (value) => { progress.value = value })
    readyFile.value = file
    // iOS only opens the share sheet from a fresh tap, so the second tap saves.
    if (!(isAppleMobile && canShareFile(file))) await deliverFile(file)
  } finally {
    fetching.value = false
  }
}

function chooseDestination(destination) {
  libraryMenu.value = false
  emit('save', destination)
}
</script>

<template>
  <div class="xd-msg" :class="{ 'is-mine': mine }">
    <div class="xd-msg-meta">
      <span v-if="senderLabel" class="xd-msg-sender">{{ senderLabel }}</span>
      <span>{{ time }}</span>
      <span v-if="targetLabel" class="xd-msg-target">→ {{ targetLabel }}</span>
    </div>

    <div class="xd-bubble" :class="{ 'is-media': isImage }">
      <p v-if="message.kind === 'text'" class="xd-text">
        <template v-for="(part, index) in parts" :key="index">
          <a v-if="part.isLink" :href="part.text" target="_blank" rel="noopener noreferrer">{{ part.text }}</a>
          <template v-else>{{ part.text }}</template>
        </template>
      </p>

      <template v-else>
        <button v-if="isImage" type="button" class="xd-thumb" :style="thumbStyle" @click="emit('preview', message)">
          <img v-if="thumb" :src="thumb" :alt="message.filename" loading="lazy" />
        </button>
        <div class="xd-file" :class="{ 'is-compact': isImage }">
          <FileText v-if="!isImage" :size="26" class="xd-file-icon" />
          <div class="xd-file-main">
            <strong :title="message.filename">{{ message.filename }}</strong>
            <span>{{ formatSize(message.file_size) }}</span>
          </div>
        </div>
        <div v-if="fetching" class="xd-progress"><span :style="{ width: `${Math.round(progress * 100)}%` }" /></div>
      </template>
    </div>

    <div class="xd-msg-actions">
      <template v-if="message.kind === 'text'">
        <button type="button" class="xd-action" @click="copyText">
          <Check v-if="copied" :size="14" /><Copy v-else :size="14" />
          {{ copied ? t('pages.xuandrop.copied') : t('pages.xuandrop.copyText') }}
        </button>
        <a v-if="firstLink" class="xd-action" :href="firstLink" target="_blank" rel="noopener noreferrer">
          <ExternalLink :size="14" />{{ t('pages.xuandrop.openLink') }}
        </a>
      </template>
      <template v-else>
        <button type="button" class="xd-action" :class="{ 'is-ready': readyFile && isAppleMobile }" :disabled="fetching" @click="saveToDevice">
          <Share v-if="readyFile && isAppleMobile" :size="14" /><Download v-else :size="14" />
          {{ isLarge ? t('pages.xuandrop.download') : readyFile && isAppleMobile ? t('pages.xuandrop.saveToDevice') : (isAppleMobile ? t('pages.xuandrop.prepareSave') : t('pages.xuandrop.download')) }}
        </button>
        <span v-if="message.can_save_to_library === false && !message.saved_to" class="xd-hint">{{ t('pages.xuandrop.tooLargeForLibrary') }}</span>
        <span v-else-if="message.saved_to" class="xd-saved"><Check :size="14" />{{ t('pages.xuandrop.savedTo', { destination: t(`pages.xuandrop.destinations.${message.saved_to}`) }) }}</span>
        <div v-else class="xd-library">
          <button type="button" class="xd-action" :disabled="saving" @click="libraryMenu = !libraryMenu">
            <FolderInput :size="14" />{{ t('pages.xuandrop.saveToLibrary') }}
          </button>
          <div v-if="libraryMenu" class="xd-library-menu">
            <button v-if="isImage || message.mime_type?.startsWith('image/')" type="button" @click="chooseDestination('photos')">{{ t('pages.xuandrop.destinations.photos') }}</button>
            <button type="button" @click="chooseDestination('files')">{{ t('pages.xuandrop.destinations.files') }}</button>
            <button type="button" @click="chooseDestination('receipts')">{{ t('pages.xuandrop.destinations.receipts') }}</button>
          </div>
        </div>
      </template>
      <button v-if="canDelete" type="button" class="xd-action is-danger" :aria-label="t('pages.xuandrop.deleteForAll')" @click="emit('delete', message)">
        <Trash2 :size="14" />
      </button>
    </div>

    <div class="xd-msg-foot">
      <span>{{ expiryText }}</span>
      <span v-if="read" class="xd-read">· {{ t('pages.xuandrop.read') }}</span>
    </div>
  </div>
</template>
