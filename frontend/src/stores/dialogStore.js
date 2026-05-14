import { defineStore } from 'pinia'
import { i18n } from '../i18n'

export const useDialogStore = defineStore('dialog', {
  state: () => ({
    visible: false,
    mode: 'prompt',
    title: '',
    message: '',
    label: '',
    value: '',
    placeholder: '',
    inputType: 'text',
    confirmText: 'Confirm',
    cancelText: 'Cancel',
    danger: false,
    resolver: null
  }),
  actions: {
    prompt(options = {}) {
      const t = (key, fallback) => (i18n.global.te(key) ? i18n.global.t(key) : fallback)
      return new Promise((resolve) => {
        this.$patch({
          visible: true,
          mode: 'prompt',
          title: options.title || t('pages.dialog.inputRequired', 'Input required'),
          message: options.message || '',
          label: options.label || '',
          value: options.defaultValue || '',
          placeholder: options.placeholder || '',
          inputType: options.inputType || 'text',
          confirmText: options.confirmText || t('common.actions.confirm'),
          cancelText: options.cancelText || t('common.actions.cancel'),
          danger: Boolean(options.danger),
          resolver: resolve
        })
      })
    },
    confirm(options = {}) {
      const t = (key, fallback) => (i18n.global.te(key) ? i18n.global.t(key) : fallback)
      return new Promise((resolve) => {
        this.$patch({
          visible: true,
          mode: 'confirm',
          title: options.title || t('common.actions.confirm', 'Confirm'),
          message: options.message || '',
          label: '',
          value: '',
          placeholder: '',
          inputType: 'text',
          confirmText: options.confirmText || t('common.actions.confirm'),
          cancelText: options.cancelText || t('common.actions.cancel'),
          danger: Boolean(options.danger),
          resolver: resolve
        })
      })
    },
    submit() {
      const result = this.mode === 'confirm' ? true : this.value
      this.resolver?.(result)
      this.close()
    },
    cancel() {
      this.resolver?.(null)
      this.close()
    },
    close() {
      this.visible = false
      this.resolver = null
    }
  }
})
