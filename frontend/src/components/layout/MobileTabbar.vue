<script setup>
import { Files, Home, Image, ReceiptText, Share2, User } from 'lucide-vue-next'

const tabs = [
  { to: '/', label: 'Home', icon: Home },
  { to: '/photos', label: 'Photos', icon: Image },
  { to: '/files', label: 'Files', icon: Files },
  { to: '/receipts', label: 'Receipts', icon: ReceiptText },
  { to: '/shared', label: 'Shared', icon: Share2 },
  { to: '/settings', label: 'Me', icon: User }
]
</script>

<template>
  <nav class="xb-mobile-tabbar">
    <router-link v-for="tab in tabs" :key="tab.to" :to="tab.to" class="xb-mobile-tab">
      <component :is="tab.icon" :size="20" />
      <span>{{ tab.label }}</span>
    </router-link>
  </nav>
</template>
