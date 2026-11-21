<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getSharedMessage } from '../api/chat'
import { legalChatHtml, splitLegalAnswer } from '../utils/legalChatContent'
import { useBrandLabels } from '../composables/useBrandLabels'
import FaIcon from '../components/FaIcon.vue'

const route = useRoute()
const router = useRouter()
const { platformName, config, load } = useBrandLabels()

const loading = ref(true)
const missing = ref(false)
const question = ref('')
const answer = ref('')
const createdAt = ref('')
const detailOpen = ref(false)
const detailHtml = ref('')
let detailTimer = 0

const navItems = [
  { label: '首页', path: '/', icon: 'house' },
  { label: '法律咨询', path: '/chat/ai', icon: 'comments' },
  { label: '法律检索', path: '/chat/search', icon: 'magnifying-glass' },
  { label: '合同服务', path: '/chat/contract', icon: 'clipboard' },
  { label: '文书生成', path: '/chat/document', icon: 'file-lines' },
]

onMounted(async () => {
  load()
  try {
    const data = await getSharedMessage(String(route.params.token || ''))
    question.value = data.question || ''
    answer.value = data.answer || ''
    createdAt.value = data.created_at
      ? new Date(data.created_at).toLocaleString('zh-CN')
      : ''
  } catch {
    missing.value = true
  } finally {
    loading.value = false
  }
})

function go(path: string) {
  router.push(path)
}

function toggleShareDetail() {
  if (detailOpen.value) {
    detailOpen.value = false
    if (detailTimer) window.clearInterval(detailTimer)
    detailTimer = 0
    return
  }
  const full = splitLegalAnswer(answer.value).detail
  detailOpen.value = true
  detailHtml.value = ''
  if (!full) return
  let shown = ''
  if (detailTimer) window.clearInterval(detailTimer)
  detailTimer = window.setInterval(() => {
    if (shown.length >= full.length) {
      detailHtml.value = legalChatHtml(full)
      window.clearInterval(detailTimer)
      detailTimer = 0
      return
    }
    shown = full.slice(0, shown.length + 40)
    detailHtml.value = legalChatHtml(shown, true)
  }, 36)
}

onBeforeUnmount(() => {
  if (detailTimer) window.clearInterval(detailTimer)
})
</script>

<template>
  <div v-loading="loading" class="share-page">
    <header class="share-top">
      <button type="button" class="share-brand" @click="go('/')">
        <img v-if="config.logo_url" :src="config.logo_url" alt="" class="share-logo" />
        <FaIcon v-else name="scale-balanced" />
        <span>{{ platformName || '首页' }}</span>
      </button>
      <nav class="share-nav" aria-label="页面导航">
        <button
          v-for="item in navItems"
          :key="item.path"
          type="button"
          class="share-nav-link"
          @click="go(item.path)"
        >
          <FaIcon :name="item.icon" />
          <span>{{ item.label }}</span>
        </button>
      </nav>
    </header>

    <main class="share-main">
      <article v-if="!missing" class="share-card">
        <p class="share-kicker">分享的法律咨询回复</p>
        <h1>咨询内容</h1>
        <p v-if="createdAt" class="share-time">分享于 {{ createdAt }}</p>

        <section v-if="question" class="share-block">
          <h2>提问</h2>
          <p class="share-question">{{ question }}</p>
        </section>

        <section class="share-block">
          <h2>回复</h2>
          <div class="msg-markdown" v-html="legalChatHtml(splitLegalAnswer(answer).summary)" />
          <button
            v-if="splitLegalAnswer(answer).detail"
            type="button"
            class="share-detail-btn"
            @click="toggleShareDetail"
          >
            {{ detailOpen ? '收起详细内容' : '查看详细内容' }}
          </button>
          <p v-if="splitLegalAnswer(answer).detail && !detailOpen" class="share-detail-hint">
            上面是根据现行规定整理的结论。需要地方补充和法条原文时，再查看详细内容。
          </p>
          <div v-if="detailOpen && detailHtml" class="msg-markdown share-detail" v-html="detailHtml" />
        </section>
      </article>

      <article v-else class="share-card">
        <h1>分享不存在或已失效</h1>
        <p class="share-empty">这条链接已被删除，或地址不正确。</p>
      </article>

      <div class="share-actions">
        <button type="button" class="share-btn share-btn--ghost" @click="go('/')">返回首页</button>
        <button type="button" class="share-btn share-btn--primary" @click="go('/chat/ai')">开始咨询</button>
      </div>
    </main>
  </div>
</template>

<style scoped>
.share-page {
  flex: 1 1 auto;
  min-height: 0;
  height: 100%;
  overflow-x: hidden;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
  background: #f4f7fb;
  color: #0f172a;
}

.share-top {
  position: sticky;
  top: 0;
  z-index: 5;
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: calc(12px + env(safe-area-inset-top)) 16px 12px;
  background: #0f172a;
  color: #fff;
}

.share-brand {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  border: none;
  background: transparent;
  color: #fff;
  font-size: 16px;
  font-weight: 700;
  padding: 0;
  cursor: pointer;
  max-width: 100%;
}

.share-brand span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.share-logo {
  height: 28px;
  width: auto;
  max-width: 120px;
  object-fit: contain;
}

.share-nav {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding-bottom: 2px;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: none;
}

.share-nav::-webkit-scrollbar {
  display: none;
}

.share-nav-link {
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 36px;
  padding: 0 12px;
  border: 1px solid rgba(255, 255, 255, 0.16);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  color: #fff;
  font-size: 13px;
  cursor: pointer;
}

.share-nav-link:hover {
  background: rgba(16, 185, 129, 0.28);
}

.share-main {
  width: min(860px, calc(100% - 24px));
  margin: 0 auto;
  padding: 16px 0 calc(28px + env(safe-area-inset-bottom));
}

.share-card {
  background: #fff;
  border-radius: 16px;
  padding: 22px 18px 24px;
  box-shadow: 0 8px 28px rgba(15, 23, 42, 0.06);
}

.share-kicker {
  margin: 0;
  color: #059669;
  font-size: 13px;
  font-weight: 600;
}

h1 {
  margin: 8px 0 0;
  font-size: 22px;
  line-height: 1.35;
}

.share-time {
  margin: 8px 0 0;
  color: #94a3b8;
  font-size: 12px;
}

.share-block {
  margin-top: 22px;
}

h2 {
  margin: 0 0 10px;
  font-size: 15px;
  color: #334155;
}

.share-detail-btn {
  margin-top: 12px;
  min-height: 40px;
  padding: 0 14px;
  border: 1px solid #d1fae5;
  border-radius: 999px;
  background: #f0fdf4;
  color: #047857;
  font-size: 14px;
  cursor: pointer;
}

.share-detail-hint {
  margin: 8px 0 0;
  color: #64748b;
  font-size: 13px;
}

.share-detail {
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid #e2e8f0;
}

.share-question,
.share-empty {
  margin: 0;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  word-break: break-word;
  color: #334155;
  line-height: 1.75;
  font-size: 15px;
}

.share-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 16px;
}

.share-btn {
  flex: 1 1 140px;
  min-height: 44px;
  border-radius: 12px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
}

.share-btn--ghost {
  border: 1px solid #cbd5e1;
  background: #fff;
  color: #0f172a;
}

.share-btn--primary {
  border: none;
  background: #10b981;
  color: #fff;
}

.msg-markdown {
  font-size: 15px;
  line-height: 1.75;
  overflow-wrap: anywhere;
  word-break: break-word;
}

.msg-markdown :deep(h1),
.msg-markdown :deep(h2),
.msg-markdown :deep(h3) {
  margin: 0.8em 0 0.4em;
  font-weight: 650;
  line-height: 1.4;
  color: #0f172a;
}

.msg-markdown :deep(h1) { font-size: 1.2em; }
.msg-markdown :deep(h2) { font-size: 1.08em; }
.msg-markdown :deep(h3) { font-size: 1em; }

.msg-markdown :deep(p) {
  margin: 0.45em 0;
}

.msg-markdown :deep(ul),
.msg-markdown :deep(ol) {
  margin: 0.4em 0;
  padding-left: 1.25em;
}

.msg-markdown :deep(img) {
  max-width: 100%;
  height: auto;
}

.msg-markdown :deep(pre) {
  margin: 0.6em 0;
  padding: 10px 12px;
  background: #f1f5f9;
  border-radius: 8px;
  overflow-x: auto;
}

.msg-markdown :deep(table) {
  display: block;
  width: 100%;
  overflow-x: auto;
  border-collapse: collapse;
  font-size: 13px;
}

.msg-markdown :deep(th),
.msg-markdown :deep(td) {
  border: 1px solid #e2e8f0;
  padding: 8px 10px;
  text-align: left;
  vertical-align: top;
  min-width: 88px;
}

@media (min-width: 768px) {
  .share-top {
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
    padding-left: 24px;
    padding-right: 24px;
  }

  .share-nav {
    justify-content: flex-end;
  }

  .share-main {
    width: min(860px, calc(100% - 48px));
    padding-top: 28px;
  }

  .share-card {
    padding: 28px 32px 32px;
  }
}
</style>
