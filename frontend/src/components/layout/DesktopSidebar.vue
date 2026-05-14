<script setup>
import XbAssetIcon from '../common/XbAssetIcon.vue'

const navItems = [
  { to: '/', label: 'Dashboard', icon: 'dashboard' },
  { to: '/inbox', label: 'Inbox', icon: 'upload' },
  { to: '/photos', label: 'Photos', icon: 'photos' },
  { to: '/files', label: 'Files', icon: 'files' },
  { to: '/receipts', label: 'Receipts', icon: 'receipts' },
  { to: '/drop', label: 'XuanDrop', icon: 'xuandrop' },
  { to: '/shared', label: 'Shared', icon: 'share' },
  { to: '/messages', label: 'Messages', icon: 'notifications' },
  { to: '/settings', label: 'Settings', icon: 'settings' }
]
</script>

<template>
  <aside class="xb-sidebar">
    <div class="xb-logo">
      <XbAssetIcon name="logo" :size="34" />
      <div>
        <strong>XuanBox</strong>
        <span>玄匣</span>
      </div>
    </div>
    <nav class="xb-sidebar-nav">
      <router-link v-for="item in navItems" :key="item.to" :to="item.to" class="xb-nav-link">
        <XbAssetIcon :name="item.icon" :size="22" />
        <span>{{ item.label }}</span>
      </router-link>
    </nav>
    <div class="xb-storage-mini">
      <XbAssetIcon name="storage" :size="24" />
      <div>
        <strong>Private Vault</strong>
        <span>Encrypted personal archive</span>
      </div>
    </div>
  </aside>
</template>
