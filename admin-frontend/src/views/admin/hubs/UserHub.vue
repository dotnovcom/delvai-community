<script setup lang="ts">
import AdminTabHub from '../components/AdminTabHub.vue'

const tabs = [
  { name: 'users', label: '用户列表', path: '/admin/hub/users/list' },
  { name: 'feedbacks', label: '用户反馈', path: '/admin/hub/users/feedbacks' },
]
</script>

<template>
  <AdminTabHub title="用户中心" subtitle="注册用户、会员套餐与用户反馈的统一管理" :tabs="tabs" />
</template>
