<script setup lang="ts">
import AdminTabHub from '../components/AdminTabHub.vue'

const tabs = [
  { name: 'announcements', label: '平台公告', path: '/admin/hub/content/announcements' },
  { name: 'legal', label: '协议政策', path: '/admin/hub/content/legal' },
]
</script>

<template>
  <AdminTabHub title="内容运营" subtitle="平台公告、启动引导、模板库与用户通知" :tabs="tabs" />
</template>
