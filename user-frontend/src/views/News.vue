<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { listNews, type NewsArticle } from '../api/cms'
import { useBrandLabels } from '../composables/useBrandLabels'

const route = useRoute()
const router = useRouter()
const { platformName, load: loadBrand } = useBrandLabels()

const loading = ref(false)
const articles = ref<NewsArticle[]>([])
const total = ref(0)
const page = ref(1)

const newsHeroBadge = computed(() => {
  const name = platformName.value
  return name ? `${name} · 平台公告` : '平台公告'
})

async function load() {
  loading.value = true
  try {
    const res = await listNews({ page: page.value, size: 12, category: 'announcement' })
    articles.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

function openArticle(id: number) {
  router.push(`/news/${id}`)
}

onMounted(async () => {
  await loadBrand()
  if (route.query.category && route.query.category !== 'announcement') {
    router.replace({ path: '/news', query: { category: 'announcement' } })
  }
  load()
})
</script>

<template>
  <div class="news-page">
    <section class="ft-hero ft-hero--compact">
      <div class="ft-hero__inner">
        <span class="ft-hero__badge">{{ newsHeroBadge }}</span>
        <h1 class="ft-hero__title">平台公告</h1>
        <p class="ft-hero__desc">平台动态、功能更新与重要通知</p>
      </div>
    </section>

    <div class="ft-page-body">
      <div v-loading="loading" class="ft-news-grid">
        <article
          v-for="item in articles"
          :key="item.id"
          class="ft-news-card"
          @click="openArticle(item.id)"
        >
          <div
            class="ft-news-card__cover ft-news-card__cover--placeholder"
            :style="item.cover_url ? { backgroundImage: `url(${item.cover_url})` } : undefined"
          >
            <span v-if="!item.cover_url">平台公告</span>
          </div>
          <div class="ft-news-card__body">
            <h3>{{ item.title }}</h3>
            <p>{{ item.summary }}</p>
            <span class="ft-news-card__date">{{ item.published_at?.slice(0, 10) }}</span>
          </div>
        </article>
        <el-empty v-if="!loading && !articles.length" description="暂无公告" class="news-empty" />
      </div>

      <el-pagination
        v-if="total > 12"
        v-model:current-page="page"
        :page-size="12"
        :total="total"
        layout="prev, pager, next"
        @current-change="load"
      />
    </div>
  </div>
</template>

<style scoped>
.news-page {
  min-height: 100%;
  background: var(--ft-bg);
}
.news-empty {
  grid-column: 1 / -1;
}
</style>
