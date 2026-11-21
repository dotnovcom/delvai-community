<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import SettingsForm from './components/SettingsForm.vue'
import { BASIC_CONFIG_TABS } from './config/basicConfigTabs'

const route = useRoute()

const tabDef = computed(() =>
  BASIC_CONFIG_TABS.find((t) => route.path === t.path || route.path.startsWith(t.path + '/')),
)

const title = computed(() => tabDef.value?.label ?? '基础配置')
const categories = computed(() => tabDef.value?.categories)
const keys = computed(() => tabDef.value?.keys)
const sections = computed(() => tabDef.value?.sections)
</script>

<template>
  <SettingsForm
    v-if="tabDef"
    :title="title"
    :categories="categories"
    :keys="keys"
    :sections="sections"
    hide-header
    embedded
    :save-label="`保存${title}`"
    show-footer-actions
  />
  <el-empty v-else description="未找到对应配置项" />
</template>
