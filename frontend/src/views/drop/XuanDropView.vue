<script setup>
import { QrCode, Send } from 'lucide-vue-next'
import PageHeader from '../../components/common/PageHeader.vue'
</script>

<template>
  <PageHeader title="XuanDrop" subtitle="Device transfer is a core module, not a side feature." />
  <section class="xb-drop-layout">
    <article class="xb-drop-zone">
      <Send :size="42" />
      <strong>Drop files here to send</strong>
      <p>Transfer sessions, QR tokens, and WebSocket updates are the next backend slice.</p>
    </article>
    <article class="xb-qr-panel">
      <QrCode :size="84" />
      <strong>Scan to send files to this PC</strong>
      <span>QR token will expire in 5 minutes.</span>
    </article>
  </section>
</template>
