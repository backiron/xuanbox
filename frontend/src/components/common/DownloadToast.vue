<script setup>
import { useI18n } from 'vue-i18n'
import { Download } from 'lucide-vue-next'

defineProps({ percent: { type: Number, default: 0 } })
const { t } = useI18n()
</script>

<template>
  <Teleport to="body">
    <div v-if="percent" class="xb-download-toast" role="status">
      <Download :size="16" />
      <span>{{ t('common.saveFile.downloading', { percent }) }}</span>
      <i><b :style="{ width: `${percent}%` }"></b></i>
    </div>
  </Teleport>
</template>
