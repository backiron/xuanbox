<script setup>
import { useI18n } from 'vue-i18n'
import XbAssetIcon from '../common/XbAssetIcon.vue'

const { t } = useI18n()

const tabs = [
  { to: '/', label: () => t('routes.dashboard'), icon: 'dashboard' },
  { to: '/inbox', label: () => t('routes.inbox'), icon: 'upload' },
  { to: '/photos', label: () => t('routes.photos'), icon: 'photos' },
  { to: '/files', label: () => t('routes.files'), icon: 'files' },
  { to: '/receipts', label: () => t('routes.receipts'), icon: 'receipts' },
  { to: '/drop', label: () => t('routes.drop'), icon: 'xuandrop' },
  { to: '/settings', label: () => t('routes.settings'), icon: 'users' }
]
</script>

<template>
  <nav class="xb-mobile-tabbar">
    <router-link v-for="tab in tabs" :key="`${tab.to}-${tab.label}`" :to="tab.to" class="xb-mobile-tab">
      <XbAssetIcon :name="tab.icon" :size="22" />
      <span>{{ tab.label() }}</span>
    </router-link>
  </nav>
</template>
