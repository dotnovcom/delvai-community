<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { Coin, DataAnalysis, Document, User } from '@element-plus/icons-vue'
import AdminFilterBar from '../../components/admin/AdminFilterBar.vue'
import AdminTableCard from '../../components/admin/AdminTableCard.vue'
import AdminPagination from '../../components/admin/AdminPagination.vue'
import AdminStatCard from '../../components/admin/AdminStatCard.vue'
import {
  listAdminAiUsage,
  listAdminAiUsageByUser,
  listAdminAiUsageServiceOptions,
  type AdminAiUsageItem,
  type AdminAiUsageByUserItem,
  type AiUsageSummary,
} from '../../api/admin'

const tab = ref<'detail' | 'by_user'>('by_user')
const items = ref<(AdminAiUsageItem | AdminAiUsageByUserItem)[]>([])
const total = ref(0)
const summary = ref<AiUsageSummary>({
  total_tokens: 0,
  total_cost: 0,
  record_count: 0,
  user_count: 0,
})
const page = ref(1)
const pageSize = ref(20)
const keyword = ref('')
const serviceKey = ref('')
const aiEngine = ref('')
const dateRange = ref<[string, string] | null>(null)
const loading = ref(false)
const serviceOptions = ref<{ service_key: string; label: string }[]>([])

const ENGINE_OPTIONS = [
  { value: '', label: '全部模型' },
  { value: 'deepseek', label: 'DeepSeek' },
  { value: 'farui', label: '通义法睿' },
  { value: 'qwen_vl', label: 'Qwen-VL' },
]

const queryParams = computed(() => ({
  page: page.value,
  size: pageSize.value,
  keyword: keyword.value || undefined,
  service_key: serviceKey.value || undefined,
  ai_engine: aiEngine.value || undefined,
  date_from: dateRange.value?.[0],
  date_to: dateRange.value?.[1],
}))

function formatTime(t?: string | null) {
  return t?.slice(0, 19).replace('T', ' ') || '—'
}

function formatUser(row: { user_nickname?: string | null; user_phone?: string | null; user_id: number }) {
  return row.user_nickname || row.user_phone || `用户 #${row.user_id}`
}

function formatTokens(n: number) {
  return n.toLocaleString('zh-CN')
}

function formatCost(n: number) {
  return `¥${n.toFixed(4)}`
}

async function loadServiceOptions() {
  serviceOptions.value = await listAdminAiUsageServiceOptions()
}

async function load() {
  loading.value = true
  try {
    if (tab.value === 'detail') {
      const res = await listAdminAiUsage(queryParams.value)
      items.value = res.items
      total.value = res.total
      summary.value = res.summary
    } else {
      const res = await listAdminAiUsageByUser(queryParams.value)
      items.value = res.items
      total.value = res.total
      summary.value = res.summary
    }
  } finally {
    loading.value = false
  }
}

function onSearch() {
  page.value = 1
  load()
}

function onTabChange() {
  page.value = 1
  load()
}

watch(page, load)
watch(pageSize, () => {
  page.value = 1
  load()
})

onMounted(async () => {
  await loadServiceOptions()
  await load()
})
</script>

<template>
  <div class="admin-page admin-page--fill">
    <div class="admin-page-header">
      <div>
        <h2>AI 用量统计</h2>
        <p class="admin-page-desc">
          按用户与功能追踪 Token 消耗与预估 API 成本，便于控制模型支出。成本单价可在「系统设置 → 服务集成 → AI」中配置。
        </p>
      </div>
    </div>

    <section class="admin-stat-grid">
      <AdminStatCard
        label="预估总成本"
        :value="formatCost(summary.total_cost)"
        sub="当前筛选条件下"
        accent="amber"
        :icon="Coin"
      />
      <AdminStatCard
        label="Token 合计"
        :value="formatTokens(summary.total_tokens)"
        sub="输入+输出总量"
        accent="indigo"
        :icon="DataAnalysis"
      />
      <AdminStatCard
        label="调用次数"
        :value="String(summary.record_count)"
        sub="AI 请求记录"
        accent="violet"
        :icon="Document"
      />
      <AdminStatCard
        label="涉及用户"
        :value="String(summary.user_count)"
        sub="去重用户数"
        accent="emerald"
        :icon="User"
      />
    </section>

    <AdminFilterBar>
      <el-date-picker
        v-model="dateRange"
        type="daterange"
        range-separator="至"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
        value-format="YYYY-MM-DD"
        style="width: 280px"
        clearable
      />
      <el-select v-model="serviceKey" placeholder="功能" clearable style="width: 160px">
        <el-option label="全部功能" value="" />
        <el-option
          v-for="opt in serviceOptions"
          :key="opt.service_key"
          :label="opt.label"
          :value="opt.service_key"
        />
      </el-select>
      <el-select v-model="aiEngine" placeholder="模型" clearable style="width: 140px">
        <el-option v-for="opt in ENGINE_OPTIONS" :key="opt.value" :label="opt.label" :value="opt.value" />
      </el-select>
      <el-input v-model="keyword" placeholder="手机号 / 昵称" style="width: 200px" clearable @keyup.enter="onSearch" />
      <el-button type="primary" @click="onSearch">查询</el-button>
    </AdminFilterBar>

    <el-tabs v-model="tab" class="admin-tabs" @tab-change="onTabChange">
      <el-tab-pane label="按用户汇总" name="by_user" />
      <el-tab-pane label="调用明细" name="detail" />
    </el-tabs>

    <AdminTableCard :loading="loading" fill>
      <el-table
        v-if="tab === 'by_user'"
        :data="items as AdminAiUsageByUserItem[]"
        class="admin-table"
        stripe
        height="100%"
        empty-text="暂无用量数据"
      >
        <el-table-column label="用户" min-width="160">
          <template #default="{ row }">{{ formatUser(row) }}</template>
        </el-table-column>
        <el-table-column prop="user_id" label="用户 ID" width="90" align="center" />
        <el-table-column label="Token 合计" min-width="120" align="right">
          <template #default="{ row }">{{ formatTokens(row.total_tokens) }}</template>
        </el-table-column>
        <el-table-column label="预估成本" min-width="120" align="right">
          <template #default="{ row }">{{ formatCost(row.total_cost) }}</template>
        </el-table-column>
        <el-table-column prop="call_count" label="调用次数" width="100" align="center" />
      </el-table>

      <el-table
        v-else
        :data="items as AdminAiUsageItem[]"
        class="admin-table"
        stripe
        height="100%"
        empty-text="暂无用量数据"
      >
        <el-table-column label="时间" width="170">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="用户" min-width="140">
          <template #default="{ row }">{{ formatUser(row) }}</template>
        </el-table-column>
        <el-table-column prop="service_label" label="功能" min-width="130" show-overflow-tooltip />
        <el-table-column prop="ai_engine_label" label="模型" width="110" />
        <el-table-column label="Token" width="100" align="right">
          <template #default="{ row }">{{ formatTokens(row.total_tokens) }}</template>
        </el-table-column>
        <el-table-column label="预估成本" width="110" align="right">
          <template #default="{ row }">{{ formatCost(row.estimated_cost) }}</template>
        </el-table-column>
        <el-table-column label="关联" width="120" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.ref_type">{{ row.ref_type }}#{{ row.ref_id }}</span>
            <span v-else class="text-muted">—</span>
          </template>
        </el-table-column>
      </el-table>

      <AdminPagination v-model:page="page" v-model:page-size="pageSize" :total="total" />
    </AdminTableCard>
  </div>
</template>
