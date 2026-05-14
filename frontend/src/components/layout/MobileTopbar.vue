<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Menu } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import XbAssetIcon from '../common/XbAssetIcon.vue'
import { setLocale } from '../../i18n'

defineProps({
  title: {
    type: String,
    required: true
  }
})

const { t, locale } = useI18n()
const currentLocaleLabel = computed(() => locale.value === 'zh-CN' ? '中' : 'EN')
const localeTitle = computed(() => locale.value === 'zh-CN' ? '切换到英文' : 'Switch to Chinese')

const links = [
  { to: '/inbox', label: () => t('routes.inbox'), icon: 'inbox' },
  { to: '/receipts', label: () => t('routes.receipts'), icon: 'receipts' },
  { to: '/shared', label: () => t('routes.shared'), icon: 'share' },
  { to: '/messages', label: () => t('routes.messages'), icon: 'notifications' },
  { to: '/settings', label: () => t('routes.settings'), icon: 'settings' }
]

const route = useRoute()
const router = useRouter()
const query = ref(String(route.query.q || ''))
const searchOpen = ref(route.path === '/search')
const shouldShowSearch = computed(() => searchOpen.value || route.path === '/search')

watch(() => route.query.q, (value) => {
  query.value = String(value || '')
})

watch(() => route.path, (path) => {
  searchOpen.value = path === '/search'
})

function toggleSearch() {
  searchOpen.value = !searchOpen.value
}

function submitSearch() {
  const q = query.value.trim()
  if (!q) {
    router.push('/search')
    return
  }
  router.push({ path: '/search', query: { q } })
}

function toggleLocale() {
  setLocale(locale.value === 'zh-CN' ? 'en' : 'zh-CN')
}
</script>

<template>
  <header class="xb-mobile-topbar">
    <div class="xb-mobile-topbar-main">
      <router-link to="/" class="xb-mobile-brand" :title="t('layout.topbar.home')">
        <XbAssetIcon name="logo" :size="30" />
        <strong>{{ title }}</strong>
      </router-link>
      <div class="xb-mobile-actions">
        <button class="xb-icon-button" type="button" :title="t('layout.topbar.searchButton')" @click="toggleSearch">
          <XbAssetIcon name="search" :size="18" />
        </button>
        <router-link to="/messages" class="xb-icon-button" :title="t('layout.topbar.notifications')">
          <XbAssetIcon name="notifications" :size="20" />
        </router-link>
        <button class="xb-language-toggle xb-mobile-language-toggle" type="button" :title="localeTitle" @click="toggleLocale">
          {{ currentLocaleLabel }}
        </button>
        <details class="xb-mobile-menu">
          <summary class="xb-icon-button" :title="t('common.actions.more')">
            <Menu :size="18" />
          </summary>
          <nav>
            <router-link v-for="link in links" :key="link.to" :to="link.to">{{ link.label() }}</router-link>
          </nav>
        </details>
      </div>
    </div>
    <form v-if="shouldShowSearch" class="xb-mobile-search" @submit.prevent="submitSearch">
      <XbAssetIcon name="search" :size="17" />
      <input v-model="query" :placeholder="t('layout.mobileSearchPlaceholder')" enterkeyhint="search" />
      <button type="submit">{{ t('layout.mobileSearchButton') }}</button>
    </form>
  </header>
</template>
