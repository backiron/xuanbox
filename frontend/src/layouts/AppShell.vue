<script setup>
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '../stores/authStore'
import { useThemeStore } from '../stores/themeStore'
import DesktopSidebar from '../components/layout/DesktopSidebar.vue'
import DesktopTopbar from '../components/layout/DesktopTopbar.vue'
import MobileTabbar from '../components/layout/MobileTabbar.vue'
import MobileTopbar from '../components/layout/MobileTopbar.vue'

const route = useRoute()
const { t } = useI18n()
const authStore = useAuthStore()
const themeStore = useThemeStore()
const title = computed(() => route.meta.titleKey ? t(route.meta.titleKey) : (route.meta.title || t('app.title')))

onMounted(async () => {
  themeStore.hydrate()
  await authStore.loadMe()
})
</script>

<template>
  <div class="xb-shell">
    <DesktopSidebar class="desktop-only" />
    <main class="xb-main">
      <DesktopTopbar class="desktop-only" :title="title" />
      <MobileTopbar class="mobile-only" :title="title" />
      <section class="xb-content">
        <router-view />
      </section>
    </main>
    <MobileTabbar class="mobile-only" />
  </div>
</template>
