import { defineStore } from 'pinia'

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
      return new Promise((resolve) => {
        this.$patch({
          visible: true,
          mode: 'prompt',
          title: options.title || 'Input required',
          message: options.message || '',
          label: options.label || '',
          value: options.defaultValue || '',
          placeholder: options.placeholder || '',
          inputType: options.inputType || 'text',
          confirmText: options.confirmText || 'Confirm',
          cancelText: options.cancelText || 'Cancel',
          danger: Boolean(options.danger),
          resolver: resolve
        })
      })
    },
    confirm(options = {}) {
      return new Promise((resolve) => {
        this.$patch({
          visible: true,
          mode: 'confirm',
          title: options.title || 'Confirm action',
          message: options.message || '',
          label: '',
          value: '',
          placeholder: '',
          inputType: 'text',
          confirmText: options.confirmText || 'Confirm',
          cancelText: options.cancelText || 'Cancel',
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
