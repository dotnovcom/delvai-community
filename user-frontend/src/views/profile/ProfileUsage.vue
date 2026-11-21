<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { getUsageSummary, type UsageQuotaItem } from '../../api/membership'

const router = useRouter()
const loading = ref(false)
const levelName = ref('free')
const planName = ref('')
const items = ref<UsageQuotaItem[]>([])

function periodLabel(period: string) {
  if (period === 'daily') return '每日'
  if (period === 'monthly') return '每月'
  return '累计'
}

function formatRemaining(row: UsageQuotaItem) {
  if (row.unlimited) return '不限'
  return String(row.remaining ?? 0)
}

function formatLimit(row: UsageQuotaItem) {
  if (row.unlimited) return '不限'
  return String(row.limit ?? 0)
}

function progressPercent(row: UsageQuotaItem) {
  if (row.unlimited || !row.limit) return 0
  return Math.min(100, Math.round((row.used / row.limit) * 100))
}

function progressStatus(row: UsageQuotaItem) {
  if (row.unlimited) return 'success'
  const pct = progressPercent(row)
  if (pct >= 90) return 'exception'
  if (pct >= 70) return 'warning'
  return ''
}

async function load() {
  loading.value = true
  try {
    const data = await getUsageSummary()
    levelName.value = data.level_name
    planName.value = data.plan_name || '免费版'
    items.value = data.items
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div v-loading="loading" class="profile-page">
    <div class="pc-card usage-card">
      <div class="header-row">
        <div>
          <h2>用量统计</h2>
          <p class="page-desc">
            当前套餐：<strong>{{ planName }}</strong>
            <span class="level-chip">{{ levelName.toUpperCase() }}</span>
          </p>
        </div>
        <div class="header-actions">
          <el-button type="primary" @click="router.push('/profile/membership')">升级会员</el-button>
          <el-button plain @click="router.push({ path: '/profile/membership', query: { tab: 'peruse' } })">
            购买按次包
          </el-button>
        </div>
      </div>

      <div v-if="items.length" class="usage-grid">
        <article v-for="row in items" :key="row.key" class="usage-item">
          <div class="usage-item__head">
            <h3>{{ row.label }}</h3>
            <span class="usage-period">{{ periodLabel(row.period) }}</span>
          </div>
          <p class="usage-numbers">
            <template v-if="row.unlimited">不限</template>
            <template v-else>
              <strong>{{ row.used }}</strong>
              <span> / {{ formatLimit(row) }}</span>
            </template>
          </p>
          <el-progress
            v-if="!row.unlimited && row.limit"
            :percentage="progressPercent(row)"
            :status="progressStatus(row)"
            :stroke-width="8"
            :show-text="false"
          />
          <p class="usage-remain">
            {{ row.unlimited ? '无限制使用' : `剩余 ${formatRemaining(row)}` }}
          </p>
        </article>
      </div>
      <el-empty v-else description="暂无用量数据" :image-size="72" />

      <p class="usage-tip">额度按 UTC 日/月重置。合同审查按次包额度永久有效，优先于月度配额扣减。</p>
    </div>
  </div>
</template>

<style scoped>
.pc-card {
  min-height: 360px;
  padding: 24px;
  background: #fff;
  border: 1px solid #e8e8e8;
  border-radius: 24px;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
}

h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
}

.page-desc {
  margin: 6px 0 0;
  font-size: 13px;
  color: #6b7280;
}

.page-desc strong {
  color: #10b981;
  font-weight: 600;
}

.level-chip {
  display: inline-block;
  margin-left: 8px;
  padding: 2px 10px;
  border-radius: 999px;
  background: #ecfdf5;
  color: #059669;
  font-size: 11px;
  vertical-align: middle;
}

.header-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 20px;
}

.header-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  flex-shrink: 0;
}

.usage-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 14px;
}

.usage-item {
  padding: 18px 16px 16px;
  border: 1px solid #e8e8e8;
  border-radius: 20px;
  background: linear-gradient(180deg, #ecfdf5 0%, #fff 56%);
}

.usage-item__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 10px;
}

.usage-item h3 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: #1f2937;
}

.usage-period {
  font-size: 11px;
  color: #059669;
  background: #d1fae5;
  padding: 2px 8px;
  border-radius: 999px;
}

.usage-numbers {
  margin: 0 0 10px;
  font-size: 13px;
  color: #6b7280;
}

.usage-numbers strong {
  font-size: 24px;
  font-weight: 600;
  color: #10b981;
}

.usage-remain {
  margin: 10px 0 0;
  font-size: 12px;
  color: #6b7280;
}

.usage-tip {
  margin: 18px 0 0;
  font-size: 12px;
  color: #6b7280;
  line-height: 1.6;
}

@media (max-width: 720px) {
  .header-row {
    flex-direction: column;
  }
}
</style>
