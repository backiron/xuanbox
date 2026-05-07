<script setup>
import {
  Archive,
  FileText,
  Gauge,
  HardDrive,
  Image,
  ReceiptText,
  Send,
  Share2,
  Settings,
  ShieldCheck
} from 'lucide-vue-next'

const navItems = [
  { to: '/', label: 'Dashboard', icon: Gauge },
  { to: '/photos', label: 'Photos', icon: Image },
  { to: '/files', label: 'Files', icon: HardDrive },
  { to: '/receipts', label: 'Receipts', icon: ReceiptText },
  { to: '/drop', label: 'XuanDrop', icon: Send },
  { to: '/shared', label: 'Shared', icon: Share2 },
  { to: '/settings', label: 'Settings', icon: Settings },
  { to: '/admin', label: 'Admin', icon: ShieldCheck }
]
</script>

<template>
  <aside class="xb-sidebar">
    <div class="xb-logo">
      <Archive :size="26" />
      <div>
        <strong>XuanBox</strong>
        <span>玄匣</span>
      </div>
    </div>
    <nav class="xb-sidebar-nav">
      <router-link v-for="item in navItems" :key="item.to" :to="item.to" class="xb-nav-link">
        <component :is="item.icon" :size="18" />
        <span>{{ item.label }}</span>
      </router-link>
    </nav>
    <div class="xb-storage-mini">
      <FileText :size="18" />
      <div>
        <strong>Private Vault</strong>
        <span>Encrypted local storage</span>
      </div>
    </div>
  </aside>
</template>
