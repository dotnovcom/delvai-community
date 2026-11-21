<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
export interface HubTab {
  name: string
  label: string
  path: string
}

const props = defineProps<{
  title: string
  subtitle?: string
  tabs: HubTab[]
}>()

const route = useRoute()
const router = useRouter()

const activeTab = computed({
  get() {
    const hit = props.tabs.find((t) => route.path === t.path || route.path.startsWith(t.path + '/'))
    return hit?.name ?? props.tabs[0]?.name ?? ''
  },
  set(name: string) {
    const tab = props.tabs.find((t) => t.name === name)
    if (tab && route.path !== tab.path) router.push(tab.path)
  },
})
</script>

<template>
  <div class="admin-hub admin-fade-in">
    <div class="admin-hub-hero">
      <h1 class="admin-hub-title">{{ title }}</h1>
      <p v-if="subtitle" class="admin-hub-subtitle">{{ subtitle }}</p>
    </div>

    <div class="admin-panel-card admin-panel-card--hub">
      <el-tabs v-model="activeTab" class="admin-segment-tabs">
        <el-tab-pane v-for="tab in tabs" :key="tab.name" :name="tab.name">
          <template #label>
            <span class="segment-tab-label">{{ tab.label }}</span>
          </template>
        </el-tab-pane>
      </el-tabs>
      <div class="admin-panel-body admin-hub-body">
        <router-view />
      </div>
    </div>
  </div>
</template>
