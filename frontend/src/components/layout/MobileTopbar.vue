<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Menu } from 'lucide-vue-next'
import XbAssetIcon from '../common/XbAssetIcon.vue'

defineProps({
  title: {
    type: String,
    required: true
  }
})

const links = [
  { to: '/inbox', label: 'Inbox' },
  { to: '/receipts', label: 'Receipts' },
  { to: '/shared', label: 'Shared' },
  { to: '/messages', label: 'Messages' },
  { to: '/settings', label: 'Settings' }
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
</script>

<template>
  <header class="xb-mobile-topbar">
    <div class="xb-mobile-topbar-main">
      <router-link to="/" class="xb-mobile-brand" title="Home">
        <XbAssetIcon name="logo" :size="30" />
        <strong>{{ title }}</strong>
      </router-link>
      <div class="xb-mobile-actions">
        <button class="xb-icon-button" type="button" title="Search" @click="toggleSearch">
          <XbAssetIcon name="search" :size="18" />
        </button>
        <router-link to="/messages" class="xb-icon-button" title="Notifications">
          <XbAssetIcon name="notifications" :size="20" />
        </router-link>
        <details class="xb-mobile-menu">
          <summary class="xb-icon-button" title="More">
            <Menu :size="18" />
          </summary>
          <nav>
            <router-link v-for="link in links" :key="link.to" :to="link.to">{{ link.label }}</router-link>
          </nav>
        </details>
      </div>
    </div>
    <form v-if="shouldShowSearch" class="xb-mobile-search" @submit.prevent="submitSearch">
      <XbAssetIcon name="search" :size="17" />
      <input v-model="query" placeholder="Search files, OCR text..." enterkeyhint="search" />
      <button type="submit">Search</button>
    </form>
  </header>
</template>
