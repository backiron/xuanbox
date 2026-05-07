<script setup>
import PageHeader from '../../components/common/PageHeader.vue'
</script>

<template>
  <PageHeader title="Admin" subtitle="System management without direct access to private user content." />
  <section class="xb-panel-grid">
    <article class="xb-panel">
      <h3>Users</h3>
      <p>Manage status, roles, quota, and invitations.</p>
    </article>
    <article class="xb-panel">
      <h3>Storage</h3>
      <p>View aggregate usage, not private file contents.</p>
    </article>
    <article class="xb-panel">
      <h3>Audit</h3>
      <p>Security-relevant operations are recorded by the backend.</p>
    </article>
  </section>
</template>
