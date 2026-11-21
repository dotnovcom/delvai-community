<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { InfoFilled, QuestionFilled } from '@element-plus/icons-vue'
import { getAdminRoles, updateAdminRoles, type RolePermissions } from '../../api/admin'

const loading = ref(false)
const saving = ref(false)
const data = ref<RolePermissions | null>(null)
const editMatrix = ref<Record<string, Record<string, string[]>>>({})

const roleLabels: Record<string, string> = {
  super_admin: '超级管理员',
  operator: '运营主管',
  content_editor: '内容编辑',
  viewer: '只读查看',
}

const roleDesc: Record<string, string> = {
  super_admin: '拥有全部权限，不可编辑',
  operator: '用户、订单、业务与数据统计',
  content_editor: '资讯、Banner、推送与套餐',
  viewer: '各模块仅读，不可修改',
}

const moduleLabels: Record<string, string> = {
  stats: '数据统计',
  users: '用户管理',
  content: '内容管理',
  push: '消息推送',
  plans: '会员套餐',
  settings: '系统配置',
  ai: 'AI 接口',
  orders: '订单管理',
  enterprise: '企业服务',
  conversations: '对话管理',
  audit_logs: '操作日志',
  banners: '启动引导',
  feedbacks: '用户反馈',
  document_templates: '文书模板',
  open_api: '开放 API',
  legal_search: '搜索服务',
  legal_contract: '合同服务',
  legal_documents: '文书生成记录',
  lawyers: '律师服务',
}

const MODULE_GROUPS: { label: string; modules: string[] }[] = [
  {
    label: '运营与数据',
    modules: ['stats', 'users', 'orders', 'enterprise', 'conversations', 'feedbacks', 'audit_logs'],
  },
  {
    label: '内容与会员',
    modules: ['content', 'banners', 'push', 'plans', 'document_templates'],
  },
  {
    label: '系统与集成',
    modules: ['settings', 'ai', 'open_api'],
  },
  {
    label: '法律服务',
    modules: ['legal_search', 'legal_contract', 'legal_documents', 'lawyers'],
  },
]

const editableRoles = ['operator', 'content_editor', 'viewer']

const INTRO_TEXT =
  '横向为角色、纵向为功能模块，便于一览某角色的整体权限；列头「全读 / 全写 / 清空」可批量设置该角色。'

type TableRow = { type: 'group'; label: string } | { type: 'module'; module: string }

const tableRows = computed((): TableRow[] => {
  if (!data.value) return []
  const allowed = new Set(data.value.modules)
  const rows: TableRow[] = []
  const grouped = new Set<string>()

  for (const g of MODULE_GROUPS) {
    const mods = g.modules.filter((m) => allowed.has(m))
    if (!mods.length) continue
    rows.push({ type: 'group', label: g.label })
    for (const m of mods) {
      rows.push({ type: 'module', module: m })
      grouped.add(m)
    }
  }

  const orphans = data.value.modules.filter((m) => !grouped.has(m))
  if (orphans.length) {
    rows.push({ type: 'group', label: '其他' })
    for (const m of orphans) rows.push({ type: 'module', module: m })
  }
  return rows
})

const roleColumnCount = computed(() => (data.value?.roles.length ?? 0) + 1)

function moduleLabelText(mod: string) {
  const name = moduleLabels[mod] || mod
  return `${name}（${mod}）`
}

async function load() {
  loading.value = true
  try {
    data.value = await getAdminRoles()
    editMatrix.value = JSON.parse(JSON.stringify(data.value.matrix))
  } finally {
    loading.value = false
  }
}

function hasPerm(role: string, mod: string, act: string) {
  return editMatrix.value[role]?.[mod]?.includes(act) ?? false
}

function togglePerm(role: string, mod: string, act: string) {
  if (!editableRoles.includes(role)) return
  if (!editMatrix.value[role]) editMatrix.value[role] = {}
  const perms = editMatrix.value[role][mod] ? [...editMatrix.value[role][mod]] : []
  const idx = perms.indexOf(act)
  if (idx >= 0) perms.splice(idx, 1)
  else perms.push(act)
  if (perms.length) editMatrix.value[role][mod] = perms
  else delete editMatrix.value[role][mod]
}

function bulkRole(role: string, acts: string[]) {
  if (!editableRoles.includes(role) || !data.value) return
  if (!editMatrix.value[role]) editMatrix.value[role] = {}
  for (const mod of data.value.modules) {
    if (acts.length) editMatrix.value[role][mod] = [...acts]
    else delete editMatrix.value[role][mod]
  }
}

function spanMethod({
  row,
  columnIndex,
}: {
  row: TableRow
  columnIndex: number
}): [number, number] | { rowspan: number; colspan: number } {
  if (row.type !== 'group') return [1, 1]
  if (columnIndex === 0) return { rowspan: 1, colspan: roleColumnCount.value }
  return { rowspan: 0, colspan: 0 }
}

function rowClassName({ row }: { row: TableRow }) {
  return row.type === 'group' ? 'roles-group-row' : ''
}

async function save() {
  saving.value = true
  try {
    const payload: Record<string, Record<string, string[]>> = {}
    for (const role of editableRoles) {
      payload[role] = editMatrix.value[role] || {}
    }
    data.value = await updateAdminRoles(payload)
    editMatrix.value = JSON.parse(JSON.stringify(data.value.matrix))
    ElMessage.success('权限已保存并生效')
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<template>
  <div v-loading="loading" class="admin-page roles-page">
    <div class="admin-page-header">
      <div>
        <h2>角色权限管理</h2>
        <p class="admin-page-desc">
          按功能模块配置各角色读写权限；保存后写入 Casbin 策略并立即生效。超级管理员固定为全部权限。
        </p>
      </div>
    </div>

    <div class="roles-toolbar">
      <div class="roles-toolbar__hint">
        <el-icon class="roles-toolbar__icon" :size="16"><InfoFilled /></el-icon>
        <span>{{ INTRO_TEXT }}</span>
      </div>
      <el-button type="primary" :loading="saving" :disabled="!data" @click="save">保存权限</el-button>
    </div>

    <div v-if="data" class="admin-panel-card roles-panel">
      <el-table
        :data="tableRows"
        class="admin-table roles-matrix"
        border
        stripe
        :span-method="spanMethod"
        :row-class-name="rowClassName"
      >
        <el-table-column label="功能模块" min-width="180" fixed>
          <template #default="{ row }">
            <template v-if="row.type === 'group'">
              <span class="roles-group-label">{{ row.label }}</span>
            </template>
            <template v-else>
              <span class="roles-module-label">{{ moduleLabelText(row.module) }}</span>
            </template>
          </template>
        </el-table-column>

        <el-table-column
          v-for="role in data.roles"
          :key="role"
          align="center"
          min-width="128"
        >
          <template #header>
            <div class="roles-col-head" :class="{ 'roles-col-head--editable': editableRoles.includes(role) }">
              <div class="roles-col-title-row">
                <span class="roles-col-title">{{ roleLabels[role] || role }}</span>
                <el-tooltip
                  :content="roleDesc[role]"
                  placement="top"
                  :show-after="200"
                >
                  <el-icon class="roles-col-info" :size="14"><QuestionFilled /></el-icon>
                </el-tooltip>
              </div>
              <div v-if="editableRoles.includes(role)" class="roles-col-actions">
                <el-button link type="primary" size="small" @click="bulkRole(role, ['read'])">全读</el-button>
                <el-button link type="primary" size="small" @click="bulkRole(role, ['read', 'write'])">全写</el-button>
                <el-button link type="info" size="small" @click="bulkRole(role, [])">清空</el-button>
              </div>
            </div>
          </template>
          <template #default="{ row }">
            <template v-if="row.type === 'group'" />
            <template v-else-if="role === 'super_admin'">
              <el-tag size="small" type="success" effect="plain">全部</el-tag>
            </template>
            <template v-else>
              <div class="perm-toggles">
                <label class="perm-toggle">
                  <el-checkbox
                    :model-value="hasPerm(role, row.module, 'read')"
                    @change="togglePerm(role, row.module, 'read')"
                  />
                  <span>读</span>
                </label>
                <label class="perm-toggle">
                  <el-checkbox
                    :model-value="hasPerm(role, row.module, 'write')"
                    @change="togglePerm(role, row.module, 'write')"
                  />
                  <span>写</span>
                </label>
              </div>
            </template>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<style scoped>
.roles-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
  padding: 12px 16px;
  background: var(--el-color-info-light-9, #f0f9ff);
  border: 1px solid var(--el-color-info-light-7, #bae6fd);
  border-radius: var(--adm-radius, 10px);
}

.roles-toolbar__hint {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  flex: 1;
  min-width: 0;
  font-size: 13px;
  line-height: 1.5;
  color: var(--adm-text-secondary, #64748b);
}

.roles-toolbar__icon {
  flex-shrink: 0;
  margin-top: 2px;
  color: var(--el-color-info, #0ea5e9);
}

.roles-panel {
  overflow: auto;
}

.roles-matrix :deep(.roles-group-row) {
  background: var(--adm-bg-subtle, #f8fafc);
}

.roles-matrix :deep(.roles-group-row td) {
  padding: 10px 16px;
}

.roles-group-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--adm-primary, #4f46e5);
  letter-spacing: 0.02em;
}

.roles-module-label {
  font-size: 14px;
  font-weight: 500;
  color: var(--adm-text, #0f172a);
  line-height: 1.4;
  white-space: nowrap;
}

.roles-col-head {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 4px 0;
}

.roles-col-title-row {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
}

.roles-col-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--adm-text, #0f172a);
}

.roles-col-info {
  color: var(--adm-text-muted, #94a3b8);
  cursor: help;
  flex-shrink: 0;
}

.roles-col-info:hover {
  color: var(--adm-primary, #4f46e5);
}

.roles-col-actions {
  display: flex;
  flex-wrap: nowrap;
  justify-content: center;
  gap: 4px 8px;
}

.roles-col-head--editable .roles-col-title {
  color: var(--adm-primary, #4f46e5);
}

.roles-matrix :deep(td .cell) {
  padding-left: 8px;
  padding-right: 8px;
}

.perm-toggles {
  display: flex;
  flex-direction: row;
  align-items: stretch;
  width: 100%;
  max-width: 120px;
  margin: 0 auto;
  gap: 0;
  padding: 2px 0;
}

.perm-toggle {
  flex: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  cursor: pointer;
  font-size: 13px;
  color: var(--adm-text-secondary, #64748b);
  user-select: none;
  min-width: 0;
}

.perm-toggle :deep(.el-checkbox) {
  margin-right: 0;
  height: auto;
}

.perm-toggle span {
  flex-shrink: 0;
}
</style>
