<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import AdminFilterBar from '../../components/admin/AdminFilterBar.vue'
import AdminTableCard from '../../components/admin/AdminTableCard.vue'
import AdminPagination from '../../components/admin/AdminPagination.vue'
import AdminIconAction from '../../components/admin/AdminIconAction.vue'
import AdminOpBtnGroup from '../../components/admin/AdminOpBtnGroup.vue'
import { deleteAuditLog, deleteAuditLogs, listAuditLogs, type AuditLogItem } from '../../api/admin'
import { get } from '../../utils/request'

const logs = ref<AuditLogItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const keyword = ref('')
const actionFilter = ref('')
const resourceFilter = ref('')
const loading = ref(false)
const deleting = ref(false)
const selected = ref<AuditLogItem[]>([])
const adminRole = ref('')
const isSuperAdmin = computed(() => adminRole.value === 'super_admin')

const RESOURCE_OPTIONS = [
  { value: 'user', label: '用户' },
  { value: 'order', label: '订单' },
  { value: 'content', label: '内容' },
  { value: 'membership_plan', label: '会员套餐' },
  { value: 'system_settings', label: '系统配置' },
  { value: 'enterprise', label: '企业' },
  { value: 'open_api_key', label: '开放 API' },
  { value: 'banner', label: '历史轮播' },
  { value: 'launch_splash', label: '启动引导' },
]

async function load() {
  loading.value = true
  try {
    const res = await listAuditLogs({
      page: page.value,
      size: pageSize.value,
      keyword: keyword.value || undefined,
      action: actionFilter.value || undefined,
      resource: resourceFilter.value || undefined,
    })
    logs.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

function formatTime(t: string) {
  return t?.slice(0, 19).replace('T', ' ')
}

function onSelectionChange(rows: AuditLogItem[]) {
  selected.value = rows
}

async function removeOne(row: AuditLogItem) {
  await ElMessageBox.confirm('确定删除这条操作日志？删除后不能恢复。', '删除日志', { type: 'warning' })
  await deleteAuditLog(row.id)
  ElMessage.success('已删除')
  await load()
}

async function removeSelected() {
  if (!selected.value.length) return
  await ElMessageBox.confirm(
    `确定删除选中的 ${selected.value.length} 条操作日志？删除后不能恢复。`,
    '批量删除',
    { type: 'warning', confirmButtonText: '删除' },
  )
  deleting.value = true
  try {
    await deleteAuditLogs(selected.value.map((row) => row.id))
    ElMessage.success('已删除')
    selected.value = []
    await load()
  } finally {
    deleting.value = false
  }
}

onMounted(async () => {
  try {
    const me = await get<{ admin_role?: string }>('/api/v1/admin/me')
    adminRole.value = me.admin_role || ''
  } catch {
    adminRole.value = ''
  }
  await load()
})
</script>

<template>
  <div class="admin-page">
    <div class="admin-page-header">
      <div>
        <h2>操作日志</h2>
        <p class="admin-page-desc">追溯管理员在后台的关键操作记录。删除日志仅超级管理员可用。</p>
      </div>
    </div>

    <AdminFilterBar
      :selected-count="isSuperAdmin ? selected.length : 0"
      :batch-deletable="isSuperAdmin"
      :batch-loading="deleting"
      @batch-delete="removeSelected"
    >
      <el-input v-model="keyword" placeholder="搜索操作/资源/ID" style="width: 220px" clearable @keyup.enter="load" />
      <el-input v-model="actionFilter" placeholder="操作类型" style="width: 160px" clearable @change="load" />
      <el-select v-model="resourceFilter" placeholder="资源类型" clearable style="width: 160px" @change="load">
        <el-option v-for="r in RESOURCE_OPTIONS" :key="r.value" :label="r.label" :value="r.value" />
      </el-select>
      <el-button type="primary" @click="load">搜索</el-button>
    </AdminFilterBar>

    <AdminTableCard :loading="loading">
    <el-table :data="logs" class="admin-table" stripe @selection-change="onSelectionChange">
      <el-table-column v-if="isSuperAdmin" type="selection" width="48" align="center" />
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column label="操作说明" min-width="280">
        <template #default="{ row }">{{ row.summary || row.action_label || row.action }}</template>
      </el-table-column>
      <el-table-column prop="operator_name" label="操作人" width="120" />
      <el-table-column label="对象" width="140">
        <template #default="{ row }">{{ row.resource_label || row.resource }}</template>
      </el-table-column>
      <el-table-column label="详情" min-width="180">
        <template #default="{ row }">
          <span class="detail-text">{{ row.detail ? JSON.stringify(row.detail) : '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="ip" label="IP" width="120" />
      <el-table-column label="时间" width="170">
        <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column v-if="isSuperAdmin" label="操作" width="88" fixed="right" align="center">
        <template #default="{ row }">
          <AdminOpBtnGroup>
            <AdminIconAction action="delete" @click="removeOne(row)" />
          </AdminOpBtnGroup>
        </template>
      </el-table-column>
    </el-table>
      <template #footer>
        <AdminPagination v-model:page="page" v-model:page-size="pageSize" :total="total" @change="load" />
      </template>
    </AdminTableCard>
  </div>
</template>

<style scoped>
.detail-text {
  font-size: 12px;
  color: #64748b;
  word-break: break-all;
}
</style>
