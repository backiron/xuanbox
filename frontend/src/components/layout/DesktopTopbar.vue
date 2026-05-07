<script setup>
import { Moon, Search, Sun } from 'lucide-vue-next'
import { useThemeStore } from '../../stores/themeStore'

defineProps({
  title: {
    type: String,
    required: true
  }
})

const themeStore = useThemeStore()
</script>

<template>
  <header class="xb-topbar">
    <div>
      <h1>{{ title }}</h1>
      <p>Private, encrypted, owner-isolated workspace</p>
    </div>
    <div class="xb-topbar-actions">
      <label class="xb-search">
        <Search :size="18" />
        <input placeholder="Search files, photos, receipts" />
      </label>
      <button class="xb-icon-button" type="button" @click="themeStore.toggle">
        <Moon v-if="themeStore.mode === 'light'" :size="18" />
        <Sun v-else :size="18" />
      </button>
    </div>
  </header>
</template>
