<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getNewsDetail, type NewsDetail } from '../api/cms'
import { usePublicConfig } from '../composables/usePublicConfig'
import { applySeo, buildArticleSeo } from '../utils/seo'
import { sanitizeHtml } from '../utils/sanitizeHtml'

const route = useRoute()
const router = useRouter()
const { config, load } = usePublicConfig()
const loading = ref(false)
const article = ref<NewsDetail | null>(null)

function syncArticleSeo() {
  if (!article.value) return
  applySeo(buildArticleSeo(article.value, config.value, route.fullPath))
}

async function fetchArticle() {
  loading.value = true
  try {
    await load()
    article.value = await getNewsDetail(Number(route.params.id))
    syncArticleSeo()
  } finally {
    loading.value = false
  }
}

onMounted(fetchArticle)

watch(
  () => route.params.id,
  (id, prev) => {
    if (id && id !== prev) fetchArticle()
  },
)
</script>

<template>
  <div v-loading="loading" class="ft-article-page">
    <template v-if="article">
      <header class="ft-article-hero">
        <div class="ft-article-hero__inner">
          <el-button text class="ft-article-back" @click="router.push('/news?category=announcement')">
            ← 返回公告列表
          </el-button>
          <h1>{{ article.title }}</h1>
          <p class="ft-article-meta">
            {{ article.published_at?.slice(0, 10) }} · {{ article.category === 'announcement' ? '平台公告' : article.category }}
          </p>
        </div>
      </header>
      <div class="ft-article-body-wrap">
        <article class="ft-article-content-card">
          <img v-if="article.cover_url" :src="article.cover_url" class="ft-article-cover" alt="" />
          <div class="ft-article-content" v-html="sanitizeHtml(article.content)" />
        </article>
      </div>
    </template>
  </div>
</template>
