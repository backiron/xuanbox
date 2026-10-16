import { defineStore } from 'pinia'
import { vaultApi } from '../api/vaultApi'

// The unlock lives only in this browser tab (sessionStorage) and only until the server-side expiry.
const STORAGE_KEY = 'xb_vault_unlock'
let expiryTimer = null

function readSaved() {
  try {
    const saved = JSON.parse(sessionStorage.getItem(STORAGE_KEY) || 'null')
    if (saved?.token && saved.expiresAt > Date.now()) return saved
  } catch {
    // sessionStorage unavailable or corrupted: start locked
  }
  return { token: '', expiresAt: 0 }
}

export function forgetVaultUnlock() {
  try {
    sessionStorage.removeItem(STORAGE_KEY)
  } catch {
    // ignore
  }
}

export const useVaultStore = defineStore('vault', {
  state: () => ({
    ...readSaved(),
    pinSet: null,
    lockedUntil: null,
    now: Date.now(),
    dialog: null // { mode: 'setup' | 'unlock' | 'reset' | 'change', resolve }
  }),
  getters: {
    unlocked: (state) => Boolean(state.token) && state.expiresAt > state.now,
    secondsLeft: (state) => Math.max(0, Math.round((state.expiresAt - state.now) / 1000))
  },
  actions: {
    tick() {
      this.now = Date.now()
      if (this.token && this.expiresAt <= this.now) this.clear()
    },
    remember(token, seconds) {
      this.token = token
      this.expiresAt = Date.now() + (seconds - 5) * 1000
      this.now = Date.now()
      try {
        sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ token: this.token, expiresAt: this.expiresAt }))
      } catch {
        // still unlocked for this page
      }
      clearTimeout(expiryTimer)
      expiryTimer = setTimeout(() => this.tick(), this.expiresAt - Date.now() + 50)
    },
    clear() {
      this.token = ''
      this.expiresAt = 0
      clearTimeout(expiryTimer)
      forgetVaultUnlock()
    },
    async refreshStatus() {
      const response = await vaultApi.status()
      this.pinSet = response.data.data.pin_set
      this.lockedUntil = response.data.data.locked_until
      return response.data.data
    },
    openDialog(mode) {
      return new Promise((resolve) => {
        this.dialog?.resolve?.(null)
        this.dialog = { mode, resolve }
      })
    },
    closeDialog(token = null) {
      const dialog = this.dialog
      this.dialog = null
      dialog?.resolve?.(token)
    },
    /** The unlock token, asking for the PIN (or to create one) when needed. Null if the person cancels. */
    async ensureUnlocked() {
      this.tick()
      if (this.unlocked) return this.token
      await this.refreshStatus()
      return this.openDialog(this.pinSet ? 'unlock' : 'setup')
    },
    /** Run a vault request; if the unlock was revoked meanwhile, ask once more and retry. */
    async run(request) {
      let token = await this.ensureUnlocked()
      if (!token) return null
      try {
        return await request(token)
      } catch (err) {
        if (err.response?.status !== 401) throw err
        this.clear()
        token = await this.ensureUnlocked()
        if (!token) return null
        return request(token)
      }
    },
    async lock() {
      this.clear()
      try {
        await vaultApi.lock()
      } catch {
        // locked locally either way
      }
    }
  }
})
