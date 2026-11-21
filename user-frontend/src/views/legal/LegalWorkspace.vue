<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useBrandLabels } from '../../composables/useBrandLabels'
import { useUserStore } from '../../store/user'
import { resolveWorkspaceKey } from '../../constants/workspaceNav'
import WorkspaceAnnouncement from '../../components/layout/WorkspaceAnnouncement.vue'
import WorkspaceUserBar from '../../components/layout/WorkspaceUserBar.vue'
import ChatPanel from './panels/ChatPanel.vue'

import SiteBottomBar from '../../components/layout/SiteBottomBar.vue'
import FaIcon from '../../components/FaIcon.vue'
import { ensureLoggedIn } from '../../composables/useLoginDialog'


const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const { workspaceNav, workspaceMeta, load } = useBrandLabels()

onMounted(() => {
  load()
  
})

const activeFunc = computed(() => resolveWorkspaceKey(route.path))
const meta = computed(() => workspaceMeta(activeFunc.value))
const activeTone = computed(
  () => workspaceNav.value.find((item) => item.key === activeFunc.value)?.tone || 'blue',
)

function switchFunc(item: typeof workspaceNav.value[0]) {
  if (activeFunc.value === 'enterprise' && item.key === 'enterprise') {
    router.push('/chat/enterprise')
    return
  }
  if (item.key === 'enterprise' && !userStore.isLoggedIn) {
    ensureLoggedIn('/chat/enterprise')
    return
  }
  if (route.path !== item.route) router.push(item.route)
}

const toolsTab = computed(() => {
  if (activeFunc.value === 'contract') {
    return route.query.tab === 'extract' ? 'extract' : 'contracts'
  }
  if (activeFunc.value === 'analysis') return 'analysis'
  return 'documents'
})

const commercialPanels: Record<string, object> = {

}
</script>

<template>
  <div class="workspace-layout">
    <nav class="func-nav">
      <div class="func-nav-items">
        <div
          v-for="item in workspaceNav"
          :key="item.key"
          class="func-nav-item"
          :class="{ active: activeFunc === item.key }"
          :title="item.label"
          @click="switchFunc(item)"
        >
          <FaIcon class="func-nav-icon" :name="item.icon" />
          <span class="func-nav-label">{{ item.label }}</span>
        </div>
      </div>
      <WorkspaceUserBar />
    </nav>

    <div class="workspace-panel">
      <WorkspaceAnnouncement />
      <div class="workspace-panel-content">
        <KeepAlive>
          <ChatPanel v-if="activeFunc === 'ai'" :key="'ai'" class="workspace-panel-fill" />
        </KeepAlive>
        <main
          v-if="activeFunc !== 'ai'"
          :key="activeFunc"
          class="workspace-main workspace-panel-fill"
          :class="{
            'workspace-main--enterprise': activeFunc === 'enterprise',
            'workspace-main--multimodal': activeFunc === 'multimodal',
            'workspace-main--lawyer': activeFunc === 'lawyer',
          }"
        >
        <div v-if="activeFunc !== 'enterprise' && activeFunc !== 'contract' && activeFunc !== 'search' && activeFunc !== 'read' && activeFunc !== 'document'" class="workspace-topbar">
          <div class="topbar-title">
            <FaIcon class="topbar-icon fa-grad" :class="`tone-${activeTone}`" :name="meta.icon" />
            <div>
              <span class="topbar-name">{{ meta.title }}</span>
              <span v-if="meta.desc" class="topbar-desc">{{ meta.desc }}</span>
            </div>
          </div>
        </div>
        <div
          class="workspace-body"
          :class="{
            'workspace-body--enterprise': activeFunc === 'enterprise',
            'workspace-body--contract': activeFunc === 'contract',
            'workspace-body--search': activeFunc === 'search',
            'workspace-body--read': activeFunc === 'read',
            'workspace-body--document': activeFunc === 'document',
            'workspace-body--analysis': activeFunc === 'analysis',
            'workspace-body--lawyer': activeFunc === 'lawyer',
          }"
        >
          <component :is="commercialPanels.search" v-if="activeFunc === 'search' && commercialPanels.search" />
          <component :is="commercialPanels.read" v-else-if="activeFunc === 'read' && commercialPanels.read" />
          <component
            :is="commercialPanels.tools"
            v-else-if="commercialPanels.tools && ['document', 'contract', 'analysis'].includes(activeFunc)"
            embedded
            :initial-tab="toolsTab"
            :show-contract-tabs="activeFunc === 'contract'"
            :show-document-panel="activeFunc === 'document'"
          />
          <component :is="commercialPanels.lawyer" v-else-if="activeFunc === 'lawyer' && commercialPanels.lawyer" embedded />
          <component :is="commercialPanels.multimodal" v-else-if="activeFunc === 'multimodal' && commercialPanels.multimodal" embedded />
          <component :is="commercialPanels.enterprise" v-else-if="activeFunc === 'enterprise' && commercialPanels.enterprise" />
        </div>
        </main>
      </div>
      <SiteBottomBar />
    </div>
  </div>
</template>

<style scoped>
.workspace-layout {
  height: 100%;
  min-height: 0;
  display: flex;
  background: var(--ft-bg);
}

.func-nav {
  width: 72px;
  background: var(--ft-portal-dark);
  border-right: 1px solid rgba(255, 255, 255, 0.06);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  z-index: 2;
  align-self: stretch;
  min-height: 100%;
}

.func-nav-items {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  align-items: stretch;
  padding: 12px 0;
  gap: 0;
}

.func-nav-item {
  width: 100%;
  min-height: 64px;
  margin: 0;
  padding: 8px 0 6px;
  border: none;
  border-radius: 0;
  box-shadow: none;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  color: rgba(255, 255, 255, 0.72);
  transition: background 0.28s cubic-bezier(0.22, 1, 0.36, 1), color 0.28s ease;
  box-sizing: border-box;
}

.func-nav-item:hover {
  background: rgba(255, 255, 255, 0.08);
  color: #fff;
}

.func-nav-item.active {
  background: rgba(16, 185, 129, 0.18);
  color: #fff;
  border: none;
  border-radius: 0;
  box-shadow: none;
}

.func-nav-icon {
  font-size: 20px;
  color: #fff;
  transition: transform 0.22s cubic-bezier(0.22, 1, 0.36, 1);
}

.func-nav-label {
  font-size: 10px;
  line-height: 1.2;
  text-align: center;
  max-width: 100%;
  word-break: break-all;
}

.workspace-panel {
  flex: 1;
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  background: #f3f4f6;
}

.workspace-panel-content {
  flex: 1;
  min-height: 0;
  min-width: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.workspace-panel-fill {
  flex: 1;
  min-height: 0;
  min-width: 0;
}

.workspace-main {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  flex: 1;
}

.workspace-main--enterprise {
  min-height: 0;
}

.workspace-main--multimodal {
  padding: 16px 20px 24px;
}

.workspace-main.workspace-panel-fill.workspace-main--lawyer {
  padding: 10px;
  box-sizing: border-box;
}

.workspace-body--lawyer {
  overflow: hidden;
  display: flex;
  flex-direction: column;
  min-height: 0;
  background: #eef2f6;
}

.workspace-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 28px;
  background: var(--ft-card-bg);
  border-bottom: 1px solid var(--ft-border);
  flex-shrink: 0;
  box-shadow: 0 1px 0 rgba(15, 23, 42, 0.04);
  border-radius: 15px;
  margin-bottom: 10px;
}

.topbar-title {
  display: flex;
  align-items: center;
  gap: 12px;
}

.topbar-icon { font-size: 20px; }

.topbar-name {
  display: block;
  font-size: 17px;
  font-weight: 500;
  color: var(--ft-text);
  letter-spacing: 0.02em;
}

.topbar-desc {
  display: block;
  font-size: 12px;
  color: var(--ft-text-secondary);
  margin-top: 4px;
  line-height: 1.4;
}

.workspace-body {
  flex: 1;
  overflow-y: auto;
  min-height: 0;
}

.workspace-body--enterprise {
  overflow: hidden;
  display: flex;
  flex-direction: column;
  background: #eef2f6;
}

.workspace-body--contract,
.workspace-body--search,
.workspace-body--read,
.workspace-body--document {
  background: #eef2f6;
  padding: 12px 16px 12px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.workspace-body--contract :deep(.tools-page--embedded),
.workspace-body--search :deep(.search-service),
.workspace-body--read :deep(.read-service),
.workspace-body--document :deep(.tools-page--embedded),
.workspace-body--analysis :deep(.tools-page--embedded) {
  flex: 1;
  height: 100%;
  min-height: 0;
}

.workspace-body--analysis {
  background: #eef2f6;
  padding: 12px 16px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.workspace-body--contract :deep(.contract-service),
.workspace-body--search :deep(.search-service),
.workspace-body--read :deep(.read-service),
.workspace-body--document :deep(.doc-service) {
  flex: 1;
  height: 100%;
  min-height: 0;
}

@media (max-width: 768px) {
  .func-nav { width: 56px; }
  .func-nav-item { width: 100%; }
  .func-nav-label { font-size: 9px; }
}
</style>

