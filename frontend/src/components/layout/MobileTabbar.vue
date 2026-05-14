<script setup>
import XbAssetIcon from '../common/XbAssetIcon.vue'

const tabs = [
  { to: '/', label: 'Home', icon: 'dashboard' },
  { to: '/inbox', label: 'Inbox', icon: 'upload' },
  { to: '/photos', label: 'Photos', icon: 'photos' },
  { to: '/files', label: 'Files', icon: 'files' },
  { to: '/receipts', label: 'Receipts', icon: 'receipts' },
  { to: '/drop', label: 'Drop', icon: 'xuandrop' },
  { to: '/settings', label: 'Me', icon: 'users' }
]
</script>

<template>
  <nav class="xb-mobile-tabbar">
    <router-link v-for="tab in tabs" :key="`${tab.to}-${tab.label}`" :to="tab.to" class="xb-mobile-tab">
      <XbAssetIcon :name="tab.icon" :size="22" />
      <span>{{ tab.label }}</span>
    </router-link>
  </nav>
</template>
