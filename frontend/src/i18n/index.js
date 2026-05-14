import { createI18n } from 'vue-i18n'
import en from './locales/en'
import zhCN from './locales/zh-CN'

export const SUPPORTED_LOCALES = ['en', 'zh-CN']

function normalizeLocale(rawLocale) {
  if (!rawLocale) return 'en'
  if (rawLocale === 'zh' || rawLocale === 'zh-CN' || rawLocale === 'zh-cn') return 'zh-CN'
  return rawLocale
}

const safeGetSaved = () => {
  try {
    return normalizeLocale(localStorage.getItem('xb_locale'))
  } catch {
    return 'en'
  }
}

const i18n = createI18n({
  legacy: false,
  globalInjection: false,
  fallbackLocale: 'en',
  locale: safeGetSaved() || 'en',
  messages: {
    en,
    'zh-CN': zhCN
  }
})

export const getSavedLocale = () => safeGetSaved()

export const setLocale = (locale) => {
  const next = normalizeLocale(locale)
  i18n.global.locale.value = next
  try {
    localStorage.setItem('xb_locale', next)
  } catch {
    // localStorage may be unavailable in restricted environments
  }
  return next
}

export { i18n }
