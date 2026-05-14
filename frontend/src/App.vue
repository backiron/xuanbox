<template>
  <n-config-provider>
    <n-message-provider>
      <router-view />
      <GlobalDialog />
    </n-message-provider>
  </n-config-provider>
</template>

<script setup>
import GlobalDialog from './components/common/GlobalDialog.vue'
</script>
