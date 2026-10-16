<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { LockKeyhole } from 'lucide-vue-next'

import { vaultApi } from '../../api/vaultApi'
import { useVaultStore } from '../../stores/vaultStore'

const { t } = useI18n()
const vault = useVaultStore()

const pin = ref('')
const confirmPin = ref('')
const currentPin = ref('')
const password = ref('')
const error = ref('')
const busy = ref(false)

const mode = computed(() => vault.dialog?.mode || '')
const title = computed(() => mode.value ? t(`pages.vault.dialog.${mode.value}Title`) : '')
const hint = computed(() => mode.value ? t(`pages.vault.dialog.${mode.value}Hint`) : '')
const needsConfirm = computed(() => ['setup', 'reset', 'change'].includes(mode.value))

watch(mode, async (value) => {
  pin.value = ''
  confirmPin.value = ''
  currentPin.value = ''
  password.value = ''
  error.value = ''
  if (value) {
    await nextTick()
    document.querySelector('.xb-vault-pin-dialog input')?.focus()
  }
})

function digitsOnly(value) {
  return String(value || '').replace(/\D/g, '').slice(0, 6)
}

function errorMessage(err) {
  const code = err.response?.data?.error_code
  const known = {
    invalid_vault_pin: 'wrongPin',
    vault_pin_locked: 'pinLocked',
    invalid_password: 'wrongPassword',
    rate_limited: 'tooManyTries'
  }
  if (known[code]) return t(`pages.vault.errors.${known[code]}`)
  if (err.response?.status === 429) return t('pages.vault.errors.tooManyTries')
  return t('pages.vault.errors.generic')
}

async function submit() {
  error.value = ''
  if (!/^\d{6}$/.test(pin.value) || (mode.value === 'change' && !/^\d{6}$/.test(currentPin.value))) {
    error.value = t('pages.vault.errors.sixDigits')
    return
  }
  if (needsConfirm.value && pin.value !== confirmPin.value) {
    error.value = t('pages.vault.errors.mismatch')
    return
  }
  if (mode.value === 'reset' && !password.value) {
    error.value = t('pages.vault.errors.passwordRequired')
    return
  }
  busy.value = true
  try {
    const request = {
      setup: () => vaultApi.setup(pin.value),
      unlock: () => vaultApi.unlock(pin.value),
      reset: () => vaultApi.resetPin(password.value, pin.value),
      change: () => vaultApi.changePin(currentPin.value, pin.value)
    }[mode.value]
    const response = await request()
    const data = response.data.data
    vault.remember(data.unlock_token, data.expires_in_seconds)
    vault.pinSet = true
    vault.closeDialog(data.unlock_token)
  } catch (err) {
    error.value = errorMessage(err)
  } finally {
    busy.value = false
  }
}

function forgotPin() {
  const resolve = vault.dialog?.resolve
  vault.dialog = { mode: 'reset', resolve }
}
</script>

<template>
  <section v-if="mode" class="xb-modal-backdrop" @click.self="vault.closeDialog()">
    <form class="xb-modal xb-vault-pin-dialog" autocomplete="off" @submit.prevent="submit">
      <LockKeyhole :size="28" />
      <h3>{{ title }}</h3>
      <p>{{ hint }}</p>
      <label v-if="mode === 'reset'">
        {{ t('pages.vault.dialog.accountPassword') }}
        <input v-model="password" type="password" autocomplete="current-password" />
      </label>
      <label v-if="mode === 'change'">
        {{ t('pages.vault.dialog.currentPin') }}
        <input :value="currentPin" type="password" inputmode="numeric" maxlength="6" @input="currentPin = digitsOnly($event.target.value); $event.target.value = currentPin" />
      </label>
      <label>
        {{ ['setup', 'unlock'].includes(mode) ? t('pages.vault.dialog.pin') : t('pages.vault.dialog.newPin') }}
        <input
          :value="pin"
          type="password"
          inputmode="numeric"
          maxlength="6"
          :placeholder="t('pages.vault.dialog.sixDigits')"
          @input="pin = digitsOnly($event.target.value); $event.target.value = pin"
        />
      </label>
      <label v-if="needsConfirm">
        {{ t('pages.vault.dialog.confirmPin') }}
        <input :value="confirmPin" type="password" inputmode="numeric" maxlength="6" @input="confirmPin = digitsOnly($event.target.value); $event.target.value = confirmPin" />
      </label>
      <p v-if="error" class="xb-form-error">{{ error }}</p>
      <div class="xb-vault-pin-actions">
        <button class="xb-primary-button" type="submit" :disabled="busy">{{ t(`pages.vault.dialog.${mode}Submit`) }}</button>
        <button class="xb-secondary-button" type="button" @click="vault.closeDialog()">{{ t('common.actions.cancel') }}</button>
      </div>
      <button v-if="mode === 'unlock'" class="xb-text-button" type="button" @click="forgotPin">{{ t('pages.vault.dialog.forgot') }}</button>
    </form>
  </section>
</template>
