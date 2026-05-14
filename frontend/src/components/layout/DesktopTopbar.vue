<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Search } from 'lucide-vue-next'
import XbAssetIcon from '../common/XbAssetIcon.vue'
import { http } from '../../api/http'
import { useAuthStore } from '../../stores/authStore'

defineProps({
  title: {
    type: String,
    required: true
  }
})

const authStore = useAuthStore()
const router = useRouter()
const query = ref('')
const avatarObjectUrl = ref('')
const userInitial = computed(() => (authStore.user?.display_name || authStore.user?.username || 'M').slice(0, 1).toUpperCase())

function submitSearch() {
  const q = query.value.trim()
  if (!q) return
  router.push({ path: '/search', query: { q } })
}

function clearAvatarObjectUrl() {
  if (avatarObjectUrl.value) URL.revokeObjectURL(avatarObjectUrl.value)
  avatarObjectUrl.value = ''
}

async function loadAvatar() {
  clearAvatarObjectUrl()
  if (!authStore.user?.avatar_file_id) return
  try {
    const response = await http.get('/settings/avatar', { responseType: 'blob' })
    avatarObjectUrl.value = URL.createObjectURL(response.data)
  } catch {
    clearAvatarObjectUrl()
  }
}

watch(() => authStore.user?.avatar_file_id, loadAvatar, { immediate: true })
onBeforeUnmount(clearAvatarObjectUrl)
</script>

<template>
  <header class="xb-topbar" :aria-label="title">
    <div class="xb-topbar-spacer"></div>
    <div class="xb-topbar-actions">
      <form class="xb-search" @submit.prevent="submitSearch">
        <XbAssetIcon name="search" :size="18" />
        <input v-model="query" placeholder="Search files, photos, receipts" />
        <button type="submit" title="Search">
          <Search :size="16" />
          <span>Search</span>
        </button>
      </form>
      <router-link to="/messages" class="xb-icon-button" title="Notifications">
        <XbAssetIcon name="notifications" :size="18" />
      </router-link>
      <router-link class="xb-user-chip" to="/settings">
        <span class="xb-user-avatar">
          <img v-if="avatarObjectUrl" :src="avatarObjectUrl" alt="" />
          <span v-else>{{ userInitial }}</span>
        </span>
        {{ authStore.user?.display_name || authStore.user?.username || 'Morning' }}
      </router-link>
    </div>
  </header>
</template>
