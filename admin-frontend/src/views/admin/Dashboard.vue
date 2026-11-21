<script setup lang="ts">
import { defineAsyncComponent, onMounted, ref } from 'vue'
import {
  UserFilled,
  WalletFilled,
  ShoppingCartFull,
  ChatDotRound,
  OfficeBuilding,
  Medal,
  TrendCharts,
  Search,
} from '@element-plus/icons-vue'
import AdminStatCard from '../../components/admin/AdminStatCard.vue'
import type { StatAccent } from '../../components/admin/AdminStatCard.vue'
import { getAdminStats, getAdminCharts, type DashboardStats, type DashboardCharts } from '../../api/admin'
import { labelOf, orderStatusLabel } from '../../utils/adminLabels'

const DashboardChartsPanel = defineAsyncComponent(() => import('./DashboardCharts.vue'))

const stats = ref<DashboardStats | null>(null)
const charts = ref<DashboardCharts | null>(null)
const loading = ref(false)

const primaryCards: {
  key: string
  label: string
  sub: string
  accent: StatAccent
  icon: typeof UserFilled
  format?: (v: number) => string
}[] = [
  { key: 'user_total', label: '用户总数', sub: '平台累计注册用户', accent: 'indigo', icon: UserFilled },
  { key: 'revenue_total', label: '总收入', sub: '累计已支付金额', accent: 'amber', icon: WalletFilled, format: (v) => `¥${v.toFixed(2)}` },
  { key: 'order_paid', label: '已支付订单', sub: '成功完成支付', accent: 'emerald', icon: ShoppingCartFull },
  { key: 'user_active', label: '活跃用户', sub: '近 7 日有行为', accent: 'violet', icon: UserFilled },
]

const secondaryCards: {
  key: string
  label: string
  sub: string
  accent: StatAccent
  icon: typeof UserFilled
}[] = [
  { key: 'user_new_week', label: '本周新增', sub: '近 7 日注册', accent: 'ocean', icon: TrendCharts },
  { key: 'conversation_total', label: '对话总数', sub: 'AI 会话累计', accent: 'magenta', icon: ChatDotRound },
  { key: 'enterprise_total', label: '企业数', sub: '企业客户', accent: 'coral', icon: OfficeBuilding },
  { key: 'membership_active', label: '活跃会员', sub: '有效订阅', accent: 'ruby', icon: Medal },
]

const searchCards: {
  key: string
  label: string
  sub: string
  accent: StatAccent
  format?: (v: number) => string
}[] = [
  { key: 'search_total_7d', label: '7日检索', sub: '法规/案例检索', accent: 'indigo', format: (v) => String(v) },
  { key: 'search_es_hit_rate_7d', label: 'ES 命中率', sub: '近7日命中占比', accent: 'emerald', format: (v) => `${v.toFixed(1)}%` },
  { key: 'search_farui_calls_7d', label: '法睿调用', sub: '近7日回填', accent: 'amber', format: (v) => String(v) },
  { key: 'search_indexed_7d', label: '入库条数', sub: '写入 ES', accent: 'ocean', format: (v) => String(v) },
]

function val(key: string, format?: (v: number) => string) {
  if (!stats.value) return '—'
  const v = stats.value[key as keyof DashboardStats]
  if (typeof v !== 'number') return '—'
  return format ? format(v) : String(v)
}

onMounted(async () => {
  loading.value = true
  try {
    const [s, c] = await Promise.all([getAdminStats(), getAdminCharts()])
    stats.value = s
    charts.value = c
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div v-loading="loading" class="admin-page admin-dashboard admin-fade-in">
    <div class="admin-page-header">
      <div>
        <h2>数据概览</h2>
        <p class="admin-page-desc">实时掌握用户、订单、会员与检索运营健康度</p>
      </div>
    </div>

    <section class="admin-stat-grid">
      <AdminStatCard
        v-for="c in primaryCards"
        :key="c.key"
        :icon="c.icon"
        :accent="c.accent"
        :label="c.label"
        :value="val(c.key, c.format)"
        :sub="c.sub"
      />
    </section>

    <section class="admin-stat-grid">
      <AdminStatCard
        v-for="c in secondaryCards"
        :key="c.key"
        :icon="c.icon"
        :accent="c.accent"
        :label="c.label"
        :value="val(c.key)"
        :sub="c.sub"
      />
    </section>

    <section class="admin-panel">
      <div class="admin-panel-head">
        <h3>检索服务（近 7 日）</h3>
        <el-icon :size="18" color="#6366f1"><Search /></el-icon>
      </div>
      <div class="admin-panel-body">
        <div class="admin-stat-grid" style="margin-bottom: 0">
          <AdminStatCard
            v-for="c in searchCards"
            :key="c.key"
            :accent="c.accent"
            :label="c.label"
            :value="val(c.key, c.format)"
            :sub="c.sub"
          />
        </div>
      </div>
    </section>

    <section v-if="stats?.ai_usage_7d?.length" class="admin-panel">
      <div class="admin-panel-head">
        <h3>AI 模型用量（近 7 日）</h3>
        <span class="text-muted">按助手回复消息聚合 · 详见业务中心「AI 用量」</span>
      </div>
      <div class="admin-panel-body">
        <el-table :data="stats.ai_usage_7d" class="admin-table" stripe>
          <el-table-column prop="label" label="模型" width="140" />
          <el-table-column prop="engine" label="引擎 ID" width="120" />
          <el-table-column prop="messages" label="回复条数" width="120" align="right" />
          <el-table-column prop="tokens" label="Token 合计" min-width="120" align="right" />
        </el-table>
      </div>
    </section>

    <DashboardChartsPanel v-if="charts" :data="charts" />

    <section class="admin-panel admin-panel-body--flush">
      <div class="admin-panel-head">
        <h3>最近订单</h3>
        <span class="text-muted">最新 10 条支付记录</span>
      </div>
      <el-table :data="charts?.recent_orders || []" class="admin-table" stripe empty-text="暂无订单">
        <el-table-column prop="order_no" label="订单号" min-width="180" show-overflow-tooltip />
        <el-table-column prop="plan_name" label="套餐" width="120" />
        <el-table-column prop="user_phone" label="用户手机" width="130" />
        <el-table-column label="金额" width="100" align="right">
          <template #default="{ row }">¥{{ Number(row.amount).toFixed(2) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="96" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="row.status === 'paid' ? 'success' : 'info'">
              {{ labelOf(orderStatusLabel, row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="170">
          <template #default="{ row }">{{ row.created_at?.slice(0, 19).replace('T', ' ') }}</template>
        </el-table-column>
      </el-table>
    </section>
  </div>
</template>
