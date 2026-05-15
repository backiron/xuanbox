<script setup>
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { LogOut } from 'lucide-vue-next'
import { authApi } from '../../api/authApi'
import { useAuthStore } from '../../stores/authStore'
import XbAssetIcon from '../common/XbAssetIcon.vue'

const { t } = useI18n()
const router = useRouter()
const authStore = useAuthStore()

const navItems = [
  { to: '/', label: () => t('routes.dashboard'), icon: 'dashboard' },
  { to: '/inbox', label: () => t('routes.inbox'), icon: 'upload' },
  { to: '/photos', label: () => t('routes.photos'), icon: 'photos' },
  { to: '/files', label: () => t('routes.files'), icon: 'files' },
  { to: '/receipts', label: () => t('routes.receipts'), icon: 'receipts' },
  { to: '/drop', label: () => t('routes.drop'), icon: 'xuandrop' },
  { to: '/shared', label: () => t('routes.shared'), icon: 'share' },
  { to: '/messages', label: () => t('routes.messages'), icon: 'notifications' },
  { to: '/settings', label: () => t('routes.settings'), icon: 'settings' }
]

async function logoutCurrent() {
  try {
    await authApi.logout(authStore.refreshToken)
  } finally {
    authStore.logoutLocal()
    await router.push('/login')
  }
}
</script>

<template>
  <aside class="xb-sidebar">
    <div class="xb-logo">
      <XbAssetIcon name="logo" :size="34" />
      <div>
        <strong>XuanBox</strong>
        <span>{{ t('layout.sidebar.privateVaultTitle') }}</span>
      </div>
    </div>
    <nav class="xb-sidebar-nav">
      <router-link v-for="item in navItems" :key="item.to" :to="item.to" class="xb-nav-link">
        <XbAssetIcon :name="item.icon" :size="22" />
        <span>{{ item.label() }}</span>
      </router-link>
    </nav>
    <div class="xb-sidebar-footer">
      <div class="xb-storage-mini">
        <XbAssetIcon name="storage" :size="24" />
        <div>
          <strong>{{ t('layout.sidebar.privateVaultTitle') }}</strong>
          <span>{{ t('layout.sidebar.privateVaultDescription') }}</span>
        </div>
      </div>
      <button class="xb-sidebar-logout" type="button" @click="logoutCurrent">
        <LogOut :size="16" />
        <span>{{ t('layout.sidebar.logout') }}</span>
      </button>
    </div>
  </aside>
</template>
