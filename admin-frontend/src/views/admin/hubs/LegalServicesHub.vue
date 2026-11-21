<script setup lang="ts">
import AdminTabHub from '../components/AdminTabHub.vue'

const tabs = [
  { name: 'consult', label: '法律咨询', path: '/admin/hub/legal/consult' },
  { name: 'chat-actions', label: '回复互动', path: '/admin/hub/legal/chat-actions' },
]
</script>

<template>
  <AdminTabHub
    title="法律服务"
    subtitle="法律咨询、检索、合同、文书、律师与音视频 — 请使用上方 Tab 切换"
    :tabs="tabs"
  />
</template>
