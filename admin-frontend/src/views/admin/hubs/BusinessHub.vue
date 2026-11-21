<script setup lang="ts">
import AdminTabHub from '../components/AdminTabHub.vue'

const tabs = [
  { name: 'ai-usage', label: 'AI 用量', path: '/admin/hub/business/ai-usage' },
  { name: 'conversations', label: '对话记录', path: '/admin/hub/business/conversations' },
]
</script>

<template>
  <AdminTabHub title="业务中心" subtitle="订单流水、全量对话审计与企业客户" :tabs="tabs" />
</template>
