<script setup>
import PageHeader from '../../components/common/PageHeader.vue'

const cards = [
  { label: 'Storage', value: '0 MB', hint: 'Local test vault' },
  { label: 'Photos', value: '0', hint: 'Timeline ready' },
  { label: 'Files', value: '0', hint: 'Encrypted storage' },
  { label: 'Receipts', value: '0', hint: 'OCR worker reserved' }
]
</script>

<template>
  <PageHeader title="Dashboard" subtitle="Your private space is isolated, encrypted, and ready for local testing." />
  <section class="xb-metric-grid">
    <article v-for="card in cards" :key="card.label" class="xb-metric-card">
      <span>{{ card.label }}</span>
      <strong>{{ card.value }}</strong>
      <p>{{ card.hint }}</p>
    </article>
  </section>
  <section class="xb-panel-grid">
    <article class="xb-panel">
      <h3>Recent Uploads</h3>
      <p>No local test files uploaded yet.</p>
    </article>
    <article class="xb-panel">
      <h3>XuanDrop</h3>
      <p>Device transfer entry is in place for the next backend module.</p>
    </article>
    <article class="xb-panel">
      <h3>Security</h3>
      <p>All file access routes through authenticated APIs.</p>
    </article>
  </section>
</template>
