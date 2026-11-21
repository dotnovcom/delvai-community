<script setup lang="ts">
import SettingsForm from './components/SettingsForm.vue'
import { PLATFORM_CONFIG_KEYS, PLATFORM_CONFIG_SECTIONS } from './config/platformConfigSections'
</script>

<template>
  <SettingsForm
    title="平台配置"
    :keys="PLATFORM_CONFIG_KEYS"
    :sections="PLATFORM_CONFIG_SECTIONS"
  />
</template>
