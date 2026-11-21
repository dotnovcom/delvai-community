<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowLeft, ArrowRight, Close } from '@element-plus/icons-vue'
import { getNewsDetail, listAnnouncements, type NewsArticle, type NewsDetail } from '../../api/cms'
import { sanitizeHtml } from '../../utils/sanitizeHtml'

const STORAGE_KEY = 'ft-workspace-announcement-closed'
const router = useRouter()

const items = ref<NewsArticle[]>([])
const visible = ref(true)
const drawerVisible = ref(false)
const listMode = ref(true)
const currentIndex = ref(0)
const detail = ref<NewsDetail | null>(null)
const detailLoading = ref(false)

const currentItem = computed(() => items.value[currentIndex.value] ?? null)
const hasPrev = computed(() => currentIndex.value > 0)
const hasNext = computed(() => currentIndex.value < items.value.length - 1)
const navHint = computed(() =>
  items.value.length ? `${currentIndex.value + 1} / ${items.value.length}` : '',
)

async function load() {
  if (sessionStorage.getItem(STORAGE_KEY) === '1') {
    visible.value = false
    return
  }
  try {
    const res = await listAnnouncements(20)
    items.value = res.items
    visible.value = res.items.length > 0
  } catch {
    items.value = []
    visible.value = false
  }
}

async function loadDetail() {
  const item = currentItem.value
  if (!item) {
    detail.value = null
    return
  }
  detailLoading.value = true
  try {
    detail.value = await getNewsDetail(item.id)
  } catch {
    detail.value = null
  } finally {
    detailLoading.value = false
  }
}

async function openDrawerAt(index: number) {
  if (!items.value.length) return
  currentIndex.value = Math.min(Math.max(index, 0), items.value.length - 1)
  listMode.value = false
  drawerVisible.value = true
  await loadDetail()
}

function openItem(id: number) {
  const idx = items.value.findIndex((i) => i.id === id)
  if (idx >= 0) void openDrawerAt(idx)
}

async function goPrev() {
  if (!hasPrev.value) return
  currentIndex.value -= 1
  await loadDetail()
}

async function goNext() {
  if (!hasNext.value) return
  currentIndex.value += 1
  await loadDetail()
}

function goList() {
  listMode.value = true
  drawerVisible.value = true
}

function openAllAnnouncements() {
  drawerVisible.value = false
  router.push({ path: '/news', query: { category: 'announcement' } })
}

function dismiss() {
  sessionStorage.setItem(STORAGE_KEY, '1')
  visible.value = false
  drawerVisible.value = false
}

function displayText(item: NewsArticle) {
  return item.summary || item.title
}

function formatDate(iso?: string) {
  return iso?.slice(0, 10) || ''
}

onMounted(load)
</script>

<template>
  <div v-if="visible && items.length" class="ws-announcement">
    <span class="ws-announcement-label">公告</span>
    <div class="ws-announcement-track-wrap">
      <div class="ws-announcement-track" :class="{ 'ws-announcement-track--scroll': items.length > 1 }">
        <button
          v-for="item in items"
          :key="item.id"
          type="button"
          class="ws-announcement-item"
          @click="openItem(item.id)"
        >
          {{ displayText(item) }}
        </button>
        <template v-if="items.length > 1">
          <button
            v-for="item in items"
            :key="`dup-${item.id}`"
            type="button"
            class="ws-announcement-item"
            @click="openItem(item.id)"
          >
            {{ displayText(item) }}
          </button>
        </template>
      </div>
    </div>
    <button type="button" class="ws-announcement-more" @click="goList">查看更多</button>
    <button type="button" class="ws-announcement-close" aria-label="关闭公告栏" @click="dismiss">
      <el-icon><Close /></el-icon>
    </button>
  </div>

  <el-drawer
    v-model="drawerVisible"
    :title="detail?.title || currentItem?.title || '平台公告'"
    direction="rtl"
    size="min(520px, 92vw)"
    append-to-body
    destroy-on-close
    class="ws-announcement-drawer"
  >
    <template #header>
      <div class="ws-drawer-head">
        <div class="ws-drawer-head__main">
          <span class="ws-drawer-badge">平台公告</span>
          <template v-if="listMode">
            <h2 class="ws-drawer-title">全部公告</h2>
            <p class="ws-drawer-meta">共 {{ items.length }} 条</p>
          </template>
          <template v-else>
            <h2 class="ws-drawer-title">{{ detail?.title || currentItem?.title }}</h2>
            <p v-if="detail?.published_at || currentItem?.published_at" class="ws-drawer-meta">
              {{ formatDate(detail?.published_at || currentItem?.published_at) }}
            </p>
          </template>
        </div>
      </div>
    </template>

    <div v-loading="detailLoading" class="ws-drawer-body">
      <ul v-if="listMode" class="ws-announcement-list">
        <li v-for="(item, index) in items" :key="item.id">
          <button type="button" class="ws-announcement-list__item" @click="openDrawerAt(index)">
            <span class="ws-announcement-list__index">{{ index + 1 }}</span>
            <span class="ws-announcement-list__body">
              <strong>{{ item.title }}</strong>
              <em v-if="item.summary && item.summary !== item.title">{{ item.summary }}</em>
            </span>
            <time>{{ formatDate(item.published_at) }}</time>
          </button>
        </li>
      </ul>
      <template v-else>
      <p v-if="detail?.summary" class="ws-drawer-summary">{{ detail.summary }}</p>
      <div
        v-if="detail?.content"
        class="ws-drawer-content ft-article-content"
        v-html="sanitizeHtml(detail.content)"
      />
      <el-empty v-else-if="!detailLoading" description="暂无公告正文" />
      </template>
    </div>

    <template #footer>
      <div class="ws-drawer-footer">
        <div v-if="!listMode" class="ws-drawer-nav">
          <el-button :disabled="!hasPrev || detailLoading" @click="goPrev">
            <el-icon class="ws-drawer-nav__icon"><ArrowLeft /></el-icon>
            上一条
          </el-button>
          <span class="ws-drawer-nav__hint">{{ navHint }}</span>
          <el-button :disabled="!hasNext || detailLoading" @click="goNext">
            下一条
            <el-icon class="ws-drawer-nav__icon"><ArrowRight /></el-icon>
          </el-button>
        </div>
        <button type="button" class="ws-drawer-all" @click="openAllAnnouncements">查看全部公告</button>
      </div>
    </template>
  </el-drawer>
</template>

<style scoped>
.ws-announcement {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 16px;
  height: 40px;
  flex-shrink: 0;
  background: linear-gradient(90deg, #fef3c7 0%, #fde68a 100%);
  border-bottom: 1px solid #f59e0b;
  position: relative;
}

.ws-announcement-label {
  flex-shrink: 0;
  font-size: 13px;
  font-weight: 700;
  color: #92400e;
  padding: 2px 8px;
  background: rgba(255, 255, 255, 0.65);
  border-radius: 4px;
}

.ws-announcement-track-wrap {
  flex: 1;
  overflow: hidden;
  min-width: 0;
}

.ws-announcement-track {
  display: inline-flex;
  align-items: center;
  gap: 32px;
  white-space: nowrap;
}

.ws-announcement-track--scroll {
  animation: ws-announcement-scroll 36s linear infinite;
}

.ws-announcement-track--scroll:hover {
  animation-play-state: paused;
}

.ws-announcement-item {
  border: none;
  background: transparent;
  padding: 0;
  font-size: 13px;
  font-weight: 500;
  color: #78350f;
  cursor: pointer;
  transition: color 0.2s;
}

.ws-announcement-item:hover {
  color: #92400e;
  text-decoration: underline;
}

.ws-announcement-more {
  flex-shrink: 0;
  border: none;
  background: transparent;
  font-size: 12px;
  font-weight: 600;
  color: #b45309;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  transition: background 0.2s;
}

.ws-announcement-more:hover {
  background: rgba(255, 255, 255, 0.5);
}

.ws-announcement-close {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  background: rgba(255, 255, 255, 0.55);
  border-radius: 6px;
  color: #92400e;
  cursor: pointer;
  transition: all 0.2s;
}

.ws-announcement-close:hover {
  background: #fff;
  color: #78350f;
}

@keyframes ws-announcement-scroll {
  0% {
    transform: translateX(0);
  }
  100% {
    transform: translateX(-50%);
  }
}

.ws-drawer-head__main {
  min-width: 0;
  padding-right: 8px;
}

.ws-drawer-badge {
  display: inline-block;
  font-size: 11px;
  font-weight: 700;
  color: #92400e;
  background: #fef3c7;
  border: 1px solid #fcd34d;
  padding: 2px 8px;
  border-radius: 4px;
  margin-bottom: 8px;
}

.ws-drawer-title {
  margin: 0 0 6px;
  font-size: 18px;
  font-weight: 700;
  line-height: 1.4;
  color: #0f172a;
}

.ws-drawer-meta {
  margin: 0;
  font-size: 13px;
  color: #64748b;
}

.ws-drawer-body {
  min-height: 200px;
}

.ws-drawer-summary {
  margin: 0 0 16px;
  padding: 12px 14px;
  font-size: 14px;
  line-height: 1.65;
  color: #475569;
  background: #f8fafc;
  border-radius: 8px;
  border-left: 3px solid #f59e0b;
}

.ws-drawer-content {
  font-size: 15px;
  line-height: 1.75;
  color: #1e293b;
}

.ws-drawer-footer {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 12px;
  width: 100%;
}

.ws-drawer-nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.ws-drawer-nav__hint {
  font-size: 13px;
  font-weight: 600;
  color: #64748b;
  flex-shrink: 0;
}

.ws-drawer-nav__icon {
  margin: 0 2px;
}

.ws-announcement-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.ws-announcement-list__item {
  width: 100%;
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 14px;
  text-align: left;
  color: inherit;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  cursor: pointer;
  transition: border-color 0.15s ease, background 0.15s ease, box-shadow 0.15s ease;
}

.ws-announcement-list__item:hover {
  border-color: #fcd34d;
  background: #fffbeb;
  box-shadow: 0 8px 18px rgba(245, 158, 11, 0.12);
}

.ws-announcement-list__index {
  flex-shrink: 0;
  width: 28px;
  height: 28px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  background: #fef3c7;
  color: #92400e;
  font-size: 12px;
  font-weight: 700;
}

.ws-announcement-list__body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.ws-announcement-list__body strong {
  font-size: 15px;
  font-weight: 600;
  line-height: 1.45;
  color: #0f172a;
}

.ws-announcement-list__body em {
  font-style: normal;
  font-size: 13px;
  line-height: 1.5;
  color: #64748b;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.ws-announcement-list__item time {
  flex-shrink: 0;
  font-size: 12px;
  color: #94a3b8;
  line-height: 28px;
}

.ws-drawer-all {
  width: 100%;
  height: 40px;
  border: none;
  border-radius: 10px;
  background: #10b981;
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}

.ws-drawer-all:hover {
  background: #059669;
}
</style>

<style>
.ws-announcement-drawer .el-drawer__header {
  margin-bottom: 0;
  padding: 18px 20px 12px;
  border-bottom: 1px solid #e2e8f0;
}

.ws-announcement-drawer .el-drawer__body {
  padding: 16px 20px;
}

.ws-announcement-drawer .el-drawer__footer {
  padding: 12px 20px 16px;
  border-top: 1px solid #e2e8f0;
}

.ws-announcement-drawer .ws-drawer-content p {
  margin: 0 0 0.9em;
}

.ws-announcement-drawer .ws-drawer-content ul,
.ws-announcement-drawer .ws-drawer-content ol {
  margin: 0 0 1em;
  padding-left: 1.25em;
}

.ws-announcement-drawer .ws-drawer-content li {
  margin: 0.35em 0;
}
</style>
