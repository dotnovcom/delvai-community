<script setup lang="ts">
import AdminTabHub from '../components/AdminTabHub.vue'
import { BASIC_CONFIG_TABS } from '../config/basicConfigTabs'

const tabs = BASIC_CONFIG_TABS.map((t) => ({
  name: t.name,
  label: t.label,
  path: t.path,
}))
</script>

<template>
  <AdminTabHub title="基础配置" subtitle="站点常规、上传、缓存与安全等运维参数" :tabs="tabs" />
</template>
