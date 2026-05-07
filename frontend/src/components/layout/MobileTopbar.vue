<script setup>
defineProps({
  title: {
    type: String,
    required: true
  }
})
</script>

<template>
  <header class="xb-mobile-topbar">
    <strong>{{ title }}</strong>
    <span>XuanBox</span>
  </header>
</template>
