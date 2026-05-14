<script setup>
import { computed } from 'vue'
import { AlertTriangle, MessageSquareText } from 'lucide-vue-next'
import { useDialogStore } from '../../stores/dialogStore'

const dialog = useDialogStore()
const icon = computed(() => (dialog.danger ? AlertTriangle : MessageSquareText))
</script>

<template>
  <section v-if="dialog.visible" class="xb-modal-backdrop xb-global-dialog-backdrop" @click.self="dialog.cancel">
    <form class="xb-modal xb-global-dialog" @submit.prevent="dialog.submit">
      <component :is="icon" :size="24" />
      <h3>{{ dialog.title }}</h3>
      <p v-if="dialog.message">{{ dialog.message }}</p>
      <label v-if="dialog.mode === 'prompt'">
        {{ dialog.label || dialog.title }}
        <input v-model="dialog.value" :type="dialog.inputType" :placeholder="dialog.placeholder" autofocus />
      </label>
      <div class="xb-row-actions">
        <button class="xb-primary-button" :class="{ 'xb-danger-fill': dialog.danger }" type="submit">
          {{ dialog.confirmText }}
        </button>
        <button class="xb-secondary-button" type="button" @click="dialog.cancel">{{ dialog.cancelText }}</button>
      </div>
    </form>
  </section>
</template>
