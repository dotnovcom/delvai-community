<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Edit, Lock, Switch, UserFilled } from '@element-plus/icons-vue'
import AdminFilterBar from '../../components/admin/AdminFilterBar.vue'
import AdminTableCard from '../../components/admin/AdminTableCard.vue'
import AdminPagination from '../../components/admin/AdminPagination.vue'
import AdminIconAction from '../../components/admin/AdminIconAction.vue'
import AdminOpBtn from '../../components/admin/AdminOpBtn.vue'
import AdminOpBtnGroup from '../../components/admin/AdminOpBtnGroup.vue'
import { usePointsLabel } from '../../composables/usePointsLabel'
import {
  listAdminUsers,
  updateAdminUser,
  resetAdminUserPassword,
  getAdminUserDetail,
  adjustAdminUserWallet,
  setAdminUserMembership,
  listAdminPlans,
  type AdminUser,
  type UserDetail,
  type AdminPlan,
} from '../../api/admin'
import { labelOf, membershipStatusLabel, orderStatusLabel, walletTxTypeLabel, pointsTxTypeLabel } from '../../utils/adminLabels'

const router = useRouter()
const { pointsName: globalPointsName, load: loadPublicConfig } = usePointsLabel()
const users = ref<AdminUser[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const keyword = ref('')
const loading = ref(false)
const roleDialogVisible = ref(false)
const roleTarget = ref<AdminUser | null>(null)
const selectedRole = ref('operator')

const passwordVisible = ref(false)
const passwordSaving = ref(false)
const passwordTarget = ref<AdminUser | null>(null)
const passwordForm = ref({
  new_password: '',
  confirm_password: '',
})

const editVisible = ref(false)
const editSaving = ref(false)
const editTarget = ref<AdminUser | null>(null)
const editForm = ref({
  nickname: '',
  phone: '',
  email: '',
  is_verified: false,
  status: 'active' as 'active' | 'disabled',
  is_admin: false,
  admin_role: 'operator' as string,
})

const detailVisible = ref(false)
const detailLoading = ref(false)
const detail = ref<UserDetail | null>(null)
const detailTab = ref('wallet')

const rechargeVisible = ref(false)
const rechargeSaving = ref(false)
const rechargeTarget = ref<AdminUser | null>(null)
const rechargeForm = ref({
  balance_delta: '' as string,
  points_delta: '' as string,
  validity_days: '' as string,
  remark: '',
})

const vipPlans = ref<AdminPlan[]>([])
const vipForm = ref({
  plan_id: undefined as number | undefined,
  extend_days: undefined as number | undefined,
  cancel: false,
})

const roleOptions = [
  { value: 'super_admin', label: '超级管理员' },
  { value: 'operator', label: '运营主管' },
  { value: 'content_editor', label: '内容编辑' },
  { value: 'viewer', label: '只读查看' },
]

const ADMIN_ROLE_LABELS: Record<string, string> = Object.fromEntries(
  roleOptions.map((r) => [r.value, r.label]),
)

const PLATFORM_LABELS: Record<string, string> = {
  phone: '手机',
  web: '网页',
  wechat: '微信',
  alipay: '支付宝',
  douyin: '抖音',
}

function adminRoleLabel(role?: string | null) {
  if (!role) return '管理员'
  return ADMIN_ROLE_LABELS[role] || role
}

function platformLabel(p: string) {
  return PLATFORM_LABELS[p] || p
}

async function load() {
  loading.value = true
  try {
    const res = await listAdminUsers(page.value, pageSize.value, keyword.value || undefined)
    users.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

async function openDetail(row: AdminUser) {
  detailVisible.value = true
  detailTab.value = 'wallet'
  detailLoading.value = true
  try {
    detail.value = await getAdminUserDetail(row.id)
  } finally {
    detailLoading.value = false
  }
}

function pointsName(row?: AdminUser | UserDetail | null) {
  if (row && 'points_display_name' in row && row.points_display_name) {
    return row.points_display_name
  }
  if (detail.value?.wallet?.points_display_name) {
    return detail.value.wallet.points_display_name
  }
  return globalPointsName.value
}

function vipExpireText(at?: string | null) {
  if (!at) return ''
  return ` · 至 ${formatTime(at)}`
}

function openRecharge(row: AdminUser) {
  rechargeTarget.value = row
  rechargeForm.value = { balance_delta: '', points_delta: '', validity_days: '', remark: '' }
  rechargeVisible.value = true
}

async function saveRecharge() {
  if (!rechargeTarget.value) return
  const remark = rechargeForm.value.remark.trim()
  if (!remark) {
    ElMessage.warning('请填写调整备注')
    return
  }
  const balanceRaw = rechargeForm.value.balance_delta.trim()
  const pointsRaw = rechargeForm.value.points_delta.trim()
  const balance_delta = balanceRaw === '' ? undefined : Number(balanceRaw)
  const points_delta = pointsRaw === '' ? undefined : Number(pointsRaw)
  if (balance_delta === undefined && points_delta === undefined) {
    ElMessage.warning('请填写余额或积分调整量')
    return
  }
  if (balance_delta !== undefined && Number.isNaN(balance_delta)) {
    ElMessage.warning('余额调整量无效')
    return
  }
  if (points_delta !== undefined && (!Number.isInteger(points_delta) || Number.isNaN(points_delta))) {
    ElMessage.warning('积分调整量须为整数')
    return
  }
  const validityRaw = rechargeForm.value.validity_days.trim()
  const validity_days = validityRaw === '' ? undefined : Number(validityRaw)
  rechargeSaving.value = true
  try {
    await adjustAdminUserWallet(rechargeTarget.value.id, {
      balance_delta,
      points_delta,
      validity_days,
      remark,
    })
    ElMessage.success('资产已调整')
    rechargeVisible.value = false
    await load()
  } catch (e: unknown) {
    const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    if (msg) ElMessage.error(String(msg))
  } finally {
    rechargeSaving.value = false
  }
}

async function loadVipPlans() {
  if (vipPlans.value.length) return
  const all = await listAdminPlans()
  vipPlans.value = all.filter((p) => p.plan_type === 'subscription' && p.status === 'active')
}

function openEdit(row: AdminUser) {
  editTarget.value = row
  editForm.value = {
    nickname: row.nickname || '',
    phone: row.phone || '',
    email: row.email || '',
    is_verified: !!row.is_verified,
    status: row.status === 'disabled' ? 'disabled' : 'active',
    is_admin: row.is_admin,
    admin_role: row.admin_role || 'operator',
  }
  vipForm.value = { plan_id: undefined, extend_days: undefined, cancel: false }
  void loadVipPlans()
  editVisible.value = true
}

function hasVipChanges() {
  return !!(vipForm.value.cancel || vipForm.value.plan_id || vipForm.value.extend_days)
}

async function saveEdit() {
  if (!editTarget.value) return
  editSaving.value = true
  try {
    const payload: Parameters<typeof updateAdminUser>[1] = {
      nickname: editForm.value.nickname.trim() || undefined,
      phone: editForm.value.phone.trim() || null,
      email: editForm.value.email.trim() || null,
      is_verified: editForm.value.is_verified,
      status: editForm.value.status,
      is_admin: editForm.value.is_admin,
    }
    if (editForm.value.is_admin) {
      payload.admin_role = editForm.value.admin_role as AdminUser['admin_role']
    } else {
      payload.is_admin = false
      payload.admin_role = undefined
    }
    await updateAdminUser(editTarget.value.id, payload)
    const vipChanged = hasVipChanges()
    if (vipChanged) {
      await setAdminUserMembership(editTarget.value.id, {
        plan_id: vipForm.value.cancel ? undefined : vipForm.value.plan_id,
        extend_days: vipForm.value.cancel ? undefined : vipForm.value.extend_days,
        cancel: vipForm.value.cancel,
      })
      vipForm.value = { plan_id: undefined, extend_days: undefined, cancel: false }
    }
    ElMessage.success(vipChanged ? '用户与会员配置已保存' : '用户信息已保存')
    editVisible.value = false
    await load()
  } catch (e: unknown) {
    const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    if (msg) ElMessage.error(String(msg))
  } finally {
    editSaving.value = false
  }
}

function viewConversations(userId: number) {
  router.push({ path: '/admin/conversations', query: { user_id: String(userId) } })
}

async function toggleStatus(row: AdminUser) {
  const status = row.status === 'active' ? 'disabled' : 'active'
  await updateAdminUser(row.id, { status })
  ElMessage.success(status === 'disabled' ? '账号已禁用' : '账号已启用')
  await load()
}

function openPassword(row: AdminUser) {
  passwordTarget.value = row
  passwordForm.value = { new_password: '', confirm_password: '' }
  passwordVisible.value = true
}

async function savePassword() {
  if (!passwordTarget.value) return
  const pwd = passwordForm.value.new_password
  const confirm = passwordForm.value.confirm_password
  if (pwd.length < 6 || pwd.length > 64) {
    ElMessage.warning('密码长度为 6–64 位')
    return
  }
  if (pwd !== confirm) {
    ElMessage.warning('两次输入的密码不一致')
    return
  }
  passwordSaving.value = true
  try {
    await resetAdminUserPassword(passwordTarget.value.id, pwd)
    ElMessage.success('密码已重置，该用户需重新登录')
    passwordVisible.value = false
  } catch (e: unknown) {
    const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    if (msg) ElMessage.error(String(msg))
  } finally {
    passwordSaving.value = false
  }
}

function openRoleDialog(row: AdminUser) {
  roleTarget.value = row
  selectedRole.value = row.admin_role || 'operator'
  roleDialogVisible.value = true
}

async function confirmRole() {
  if (!roleTarget.value) return
  await updateAdminUser(roleTarget.value.id, {
    is_admin: true,
    admin_role: selectedRole.value as AdminUser['admin_role'],
  })
  ElMessage.success('管理员角色已更新')
  roleDialogVisible.value = false
  await load()
}

async function removeAdmin(row: AdminUser) {
  await updateAdminUser(row.id, { is_admin: false, admin_role: undefined })
  ElMessage.success('已取消管理员')
  await load()
}

function formatTime(t: string) {
  return t?.slice(0, 19).replace('T', ' ')
}

onMounted(async () => {
  await loadPublicConfig()
  await load()
})
</script>

<template>
  <div class="admin-page admin-page--fill users-page">
    <div class="admin-page-header">
      <div>
        <h2>用户列表</h2>
        <p class="admin-page-desc">管理平台注册用户、VIP、余额与积分（运营人工调整，P0）。</p>
      </div>
    </div>

    <AdminFilterBar>
      <el-input v-model="keyword" placeholder="搜索手机号/邮箱/昵称" style="width: 280px" clearable @keyup.enter="load" />
      <el-button type="primary" @click="load">搜索</el-button>
    </AdminFilterBar>

    <AdminTableCard :loading="loading" fill>
      <el-table :data="users" class="admin-table" stripe table-layout="fixed" height="100%">
        <el-table-column prop="id" label="ID" width="96" align="center" class-name="users-id-col" />
        <el-table-column prop="nickname" label="昵称" min-width="100" show-overflow-tooltip />
        <el-table-column prop="phone" label="手机号" width="120" />
        <el-table-column prop="email" label="邮箱" min-width="160" show-overflow-tooltip />
        <el-table-column label="认证" width="72" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_verified ? 'success' : 'info'" size="small">
              {{ row.is_verified ? '已认证' : '未认证' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="来源" width="72" align="center">
          <template #default="{ row }">{{ platformLabel(row.platform) }}</template>
        </el-table-column>
        <el-table-column label="VIP" min-width="100" show-overflow-tooltip>
          <template #default="{ row }">
            <span>{{ row.vip_label || '免费版' }}（{{ row.vip_expire_at ? formatTime(row.vip_expire_at).slice(0, 10) : '-' }}）</span>
          </template>
        </el-table-column>
        <el-table-column label="余额" width="120" align="right">
          <template #default="{ row }">¥{{ Number(row.balance ?? 0).toFixed(2) }}</template>
        </el-table-column>
        <el-table-column :label="pointsName()" width="120" align="right">
          <template #default="{ row }">{{ row.points ?? 0 }}</template>
        </el-table-column>
        <el-table-column label="状态" width="72" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'danger'" size="small">
              {{ row.status === 'active' ? '正常' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="管理员" width="100" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.is_admin" type="warning" size="small">{{ adminRoleLabel(row.admin_role) }}</el-tag>
            <span v-else class="cell-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="注册时间" width="168" show-overflow-tooltip>
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="430" align="center" class-name="users-op-col admin-table-op-col">
          <template #default="{ row }">
            <AdminOpBtnGroup nowrap compact class="admin-table-actions users-actions">
              <AdminIconAction action="view" label="详情" @click="openDetail(row)" />
              <AdminOpBtn variant="success" label="充值" @click="openRecharge(row)" />
              <AdminOpBtn variant="muted" label="编辑" :icon="Edit" @click="openEdit(row)" />
              <AdminOpBtn variant="warn" label="改密" :icon="Lock" @click="openPassword(row)" />
              <AdminOpBtn
                v-if="row.status === 'active'"
                variant="danger"
                label="禁用"
                :icon="Switch"
                @click="toggleStatus(row)"
              />
              <AdminOpBtn
                v-else
                variant="success"
                label="启用"
                :icon="Switch"
                @click="toggleStatus(row)"
              />
              <el-tooltip v-if="!row.is_admin" content="设为管理员" placement="top" :show-after="300">
                <AdminOpBtn variant="warn" label="设管" :icon="UserFilled" @click="openRoleDialog(row)" />
              </el-tooltip>
              <el-tooltip v-if="row.is_admin" content="修改角色" placement="top" :show-after="300">
                <AdminOpBtn variant="edit" label="改角色" @click="openRoleDialog(row)" />
              </el-tooltip>
              <el-tooltip v-if="row.is_admin" content="取消管理员" placement="top" :show-after="300">
                <AdminOpBtn variant="slate" label="取消管" @click="removeAdmin(row)" />
              </el-tooltip>
            </AdminOpBtnGroup>
          </template>
        </el-table-column>
      </el-table>
      <template #footer>
        <AdminPagination v-model:page="page" v-model:page-size="pageSize" :total="total" @change="load" />
      </template>
    </AdminTableCard>

    <el-drawer
      v-model="detailVisible"
      title="用户详情"
      size="560px"
      destroy-on-close
      append-to-body
      class="admin-drawer"
    >
      <div v-loading="detailLoading">
        <template v-if="detail">
          <el-descriptions :column="2" border size="small">
            <el-descriptions-item label="ID">{{ detail.id }}</el-descriptions-item>
            <el-descriptions-item label="手机号">{{ detail.phone || '-' }}</el-descriptions-item>
            <el-descriptions-item label="邮箱">{{ detail.email || '-' }}</el-descriptions-item>
            <el-descriptions-item label="认证">{{ detail.is_verified ? '已认证' : '未认证' }}</el-descriptions-item>
            <el-descriptions-item label="昵称">{{ detail.nickname || '-' }}</el-descriptions-item>
            <el-descriptions-item label="来源">{{ platformLabel(detail.platform) }}</el-descriptions-item>
            <el-descriptions-item label="状态">{{ detail.status === 'active' ? '正常' : '禁用' }}</el-descriptions-item>
            <el-descriptions-item label="注册时间">{{ formatTime(detail.created_at) }}</el-descriptions-item>
            <el-descriptions-item label="VIP">{{ detail.vip_label || '免费版' }}{{ vipExpireText(detail.vip_expire_at) }}</el-descriptions-item>
            <el-descriptions-item label="余额">¥{{ Number(detail.wallet?.balance ?? 0).toFixed(2) }}</el-descriptions-item>
            <el-descriptions-item :label="detail.wallet?.points_display_name || '法理豆'">{{ detail.wallet?.points ?? 0 }}</el-descriptions-item>
            <el-descriptions-item label="即将过期">{{ detail.wallet?.points_expiring_soon ?? 0 }}</el-descriptions-item>
            <el-descriptions-item label="对话数">{{ detail.conversation_count }}</el-descriptions-item>
            <el-descriptions-item label="消息数">{{ detail.message_count }}</el-descriptions-item>
          </el-descriptions>

          <el-button type="primary" link style="margin: 16px 0" @click="viewConversations(detail.id)">
            查看该用户全部对话 →
          </el-button>

          <el-tabs v-model="detailTab" class="admin-segment-tabs admin-segment-tabs--inner" style="margin-top: 16px">
            <el-tab-pane name="wallet">
              <template #label>
                <span class="segment-tab-label">资产流水</span>
              </template>
            </el-tab-pane>
            <el-tab-pane name="memberships">
              <template #label>
                <span class="segment-tab-label">会员记录</span>
              </template>
            </el-tab-pane>
            <el-tab-pane name="orders">
              <template #label>
                <span class="segment-tab-label">订单列表</span>
              </template>
            </el-tab-pane>
          </el-tabs>
          <div class="detail-tab-body">
            <template v-if="detailTab === 'wallet'">
              <p class="detail-section-title">余额流水</p>
              <el-table :data="detail.wallet_transactions || []" size="small" empty-text="暂无余额流水">
                <el-table-column label="类型" width="100">
                  <template #default="{ row }">{{ labelOf(walletTxTypeLabel, row.type) }}</template>
                </el-table-column>
                <el-table-column label="变动" width="90" align="right">
                  <template #default="{ row }">
                    {{ row.amount >= 0 ? '+' : '' }}{{ Number(row.amount).toFixed(2) }}
                  </template>
                </el-table-column>
                <el-table-column label="余额后" width="90" align="right">
                  <template #default="{ row }">{{ Number(row.balance_after).toFixed(2) }}</template>
                </el-table-column>
                <el-table-column prop="remark" label="备注" min-width="100" show-overflow-tooltip />
                <el-table-column label="时间" width="160">
                  <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
                </el-table-column>
              </el-table>
              <p class="detail-section-title">{{ detail.wallet?.points_display_name || '法理豆' }}流水</p>
              <el-table :data="detail.points_ledger || []" size="small" empty-text="暂无积分流水">
                <el-table-column label="类型" width="100">
                  <template #default="{ row }">{{ labelOf(pointsTxTypeLabel, row.type) }}</template>
                </el-table-column>
                <el-table-column label="变动" width="80" align="right">
                  <template #default="{ row }">{{ row.delta >= 0 ? '+' : '' }}{{ row.delta }}</template>
                </el-table-column>
                <el-table-column prop="balance_after" label="余额后" width="80" align="right" />
                <el-table-column prop="remark" label="备注" min-width="100" show-overflow-tooltip />
                <el-table-column label="时间" width="160">
                  <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
                </el-table-column>
              </el-table>
            </template>
            <el-table v-else-if="detailTab === 'memberships'" :data="detail.memberships" size="small" empty-text="暂无会员记录">
              <el-table-column prop="plan_name" label="套餐" />
              <el-table-column prop="level" label="等级" width="70" />
              <el-table-column label="状态" width="90">
                <template #default="{ row }">
                  <el-tag size="small" :type="row.status === 'active' ? 'success' : 'info'">
                    {{ labelOf(membershipStatusLabel, row.status) }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="开始" width="160">
                <template #default="{ row }">{{ formatTime(row.start_at) }}</template>
              </el-table-column>
              <el-table-column label="到期" width="160">
                <template #default="{ row }">{{ row.expire_at ? formatTime(row.expire_at) : '-' }}</template>
              </el-table-column>
            </el-table>
            <el-table v-else :data="detail.orders" size="small" empty-text="暂无订单">
              <el-table-column prop="order_no" label="订单号" min-width="140" />
              <el-table-column prop="plan_name" label="套餐" />
              <el-table-column label="金额" width="90">
                <template #default="{ row }">¥{{ Number(row.amount).toFixed(2) }}</template>
              </el-table-column>
              <el-table-column label="状态" width="90">
                <template #default="{ row }">
                  <el-tag size="small" :type="row.status === 'paid' ? 'success' : row.status === 'pending' ? 'warning' : 'info'">
                    {{ labelOf(orderStatusLabel, row.status) }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="时间" width="160">
                <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
              </el-table-column>
            </el-table>
          </div>
        </template>
      </div>
    </el-drawer>

    <el-dialog
      v-model="editVisible"
      title="编辑用户"
      width="520px"
      class="admin-dialog"
      append-to-body
      align-center
      destroy-on-close
    >
      <el-form label-width="96px">
        <el-form-item label="用户 ID">
          <el-input :model-value="String(editTarget?.id ?? '')" disabled />
        </el-form-item>
        <el-form-item label="昵称">
          <el-input v-model="editForm.nickname" placeholder="用户昵称" maxlength="64" show-word-limit />
        </el-form-item>
        <el-form-item label="手机号">
          <el-input v-model="editForm.phone" placeholder="11 位手机号，可留空" maxlength="11" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="editForm.email" placeholder="邮箱地址，可留空" maxlength="255" />
        </el-form-item>
        <el-form-item label="是否认证">
          <el-switch v-model="editForm.is_verified" active-text="已认证" inactive-text="未认证" />
        </el-form-item>
        <el-form-item label="注册来源">
          <el-input :model-value="platformLabel(editTarget?.platform ?? '')" disabled />
        </el-form-item>
        <el-form-item label="账号状态">
          <el-radio-group v-model="editForm.status">
            <el-radio value="active">正常</el-radio>
            <el-radio value="disabled">禁用</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="后台管理员">
          <el-switch v-model="editForm.is_admin" active-text="是" inactive-text="否" />
        </el-form-item>
        <el-form-item v-if="editForm.is_admin" label="管理员角色">
          <el-select v-model="editForm.admin_role" style="width: 100%">
            <el-option v-for="r in roleOptions" :key="r.value" :label="r.label" :value="r.value" />
          </el-select>
        </el-form-item>
        <el-divider content-position="left">VIP 配置</el-divider>
        <el-form-item label="当前 VIP">
          <span>{{ editTarget?.vip_label || '免费版' }}{{ vipExpireText(editTarget?.vip_expire_at) }}</span>
        </el-form-item>
        <el-form-item label="开通套餐">
          <el-select v-model="vipForm.plan_id" clearable placeholder="选择订阅套餐" style="width: 100%" :disabled="vipForm.cancel">
            <el-option v-for="p in vipPlans" :key="p.id" :label="`${p.name}（${p.duration_days}天）`" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="延期天数">
          <el-input-number v-model="vipForm.extend_days" :min="1" :max="3650" :disabled="vipForm.cancel" controls-position="right" style="width: 100%" />
        </el-form-item>
        <el-form-item label="取消会员">
          <el-switch v-model="vipForm.cancel" active-text="是" inactive-text="否" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="editSaving" @click="saveEdit">保存用户信息</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="rechargeVisible"
      title="人工充值 / 扣减"
      width="480px"
      class="admin-dialog"
      append-to-body
      align-center
      destroy-on-close
    >
      <p class="recharge-hint">用户 #{{ rechargeTarget?.id }} · 当前余额 ¥{{ Number(rechargeTarget?.balance ?? 0).toFixed(2) }} · {{ pointsName(rechargeTarget) }} {{ rechargeTarget?.points ?? 0 }}</p>
      <el-form label-width="108px">
        <el-form-item label="余额调整(元)">
          <el-input v-model="rechargeForm.balance_delta" placeholder="正数充值，负数扣减，可留空" />
        </el-form-item>
        <el-form-item :label="`${pointsName(rechargeTarget)}调整`">
          <el-input v-model="rechargeForm.points_delta" placeholder="整数，正发负扣，可留空" />
        </el-form-item>
        <el-form-item label="积分有效期(天)">
          <el-input v-model="rechargeForm.validity_days" placeholder="留空用系统默认 90 天；0 表示永久" />
        </el-form-item>
        <el-form-item label="备注" required>
          <el-input v-model="rechargeForm.remark" type="textarea" :rows="2" maxlength="500" show-word-limit placeholder="必填，记入流水" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="rechargeVisible = false">取消</el-button>
        <el-button type="primary" :loading="rechargeSaving" @click="saveRecharge">确认调整</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="passwordVisible"
      title="重置用户密码"
      width="440px"
      class="admin-dialog"
      append-to-body
      align-center
      destroy-on-close
    >
      <p class="recharge-hint">
        用户 #{{ passwordTarget?.id }}
        <template v-if="passwordTarget?.nickname"> · {{ passwordTarget.nickname }}</template>
        <template v-if="passwordTarget?.phone"> · {{ passwordTarget.phone }}</template>
      </p>
      <el-form label-width="96px">
        <el-form-item label="新密码" required>
          <el-input
            v-model="passwordForm.new_password"
            type="password"
            show-password
            maxlength="64"
            placeholder="6–64 位"
            autocomplete="new-password"
          />
        </el-form-item>
        <el-form-item label="确认密码" required>
          <el-input
            v-model="passwordForm.confirm_password"
            type="password"
            show-password
            maxlength="64"
            placeholder="再次输入新密码"
            autocomplete="new-password"
            @keyup.enter="savePassword"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="passwordVisible = false">取消</el-button>
        <el-button type="primary" :loading="passwordSaving" @click="savePassword">确认重置</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="roleDialogVisible"
      title="分配管理员角色"
      width="420px"
      class="admin-dialog"
      append-to-body
      align-center
      destroy-on-close
    >
      <el-form label-width="80px">
        <el-form-item label="角色">
          <el-select v-model="selectedRole" style="width: 100%">
            <el-option v-for="r in roleOptions" :key="r.value" :label="r.label" :value="r.value" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="roleDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmRole">确认</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.cell-muted {
  color: var(--ft-text-secondary);
  font-size: 13px;
}

.cell-sub {
  display: block;
  font-size: 11px;
}

.detail-section-title {
  margin: 12px 0 8px;
  font-size: 13px;
  font-weight: 600;
  color: var(--ft-text-secondary);
}

.recharge-hint {
  margin: 0 0 16px;
  font-size: 13px;
  color: var(--ft-text-secondary);
}

.detail-tab-body {
  padding-top: 12px;
}

.users-page :deep(.users-id-col .cell) {
  white-space: nowrap;
  word-break: keep-all;
}

.users-page :deep(.users-op-col .cell) {
  overflow: visible;
}

.users-actions {
  flex-wrap: nowrap !important;
  justify-content: center;
  gap: 4px !important;
  padding: 2px 0;
}

.users-actions :deep(.admin-op-btn) {
  height: 26px;
  padding: 0 7px;
  font-size: 11px;
  gap: 3px;
}

.users-actions :deep(.admin-op-btn__icon) {
  font-size: 12px;
}
</style>
