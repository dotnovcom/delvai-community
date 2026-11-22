<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Edit, Lightning } from '@element-plus/icons-vue'
import {
  getIntegrationsHealth,
  listAdminSettings,
  listAiProviders,
  testAiProvider,
  updateAdminSettings,
  updateAiProvider,
  type AiProvider,
  type IntegrationHealthItem,
  type SystemSetting,
} from '../../api/admin'
import { resolveAdminIcon, type AdminIconName } from '../../components/admin/adminIcons'
import {
  EMAIL_CHANNELS,
  PAYMENT_CHANNELS,
  SMS_CHANNELS,
  STORAGE_CHANNELS,
  allSettingsKeys,
  type SettingsChannelDef,
  type SettingsFieldDef,
} from './config/integrationChannels'

type TabKey = 'ai' | 'storage' | 'sms' | 'email' | 'payment'

const TABS: { key: TabKey; label: string; icon: AdminIconName }[] = [
  { key: 'ai', label: 'AI 大模型', icon: 'ai' },
  { key: 'storage', label: '文件存储', icon: 'storage' },
  { key: 'sms', label: '短信', icon: 'sms' },
  { key: 'email', label: '邮件', icon: 'email' },
  { key: 'payment', label: '支付', icon: 'payment' },
]

const HEALTH_LABELS: Record<string, string> = {
  redis: 'Redis',
  deepseek: '对话模型',
  sms: '短信',
  wechat_pay: '微信支付',
}

const BOOL_KEYS = new Set(['email_enabled', 'smtp_use_tls', 'wechat_pay_enabled', 'alipay_enabled'])

function normalizeCat(raw: unknown): TabKey {
  const value = String(raw || '')
  if (value === 'chat' || value === 'ai') return 'ai'
  if (value === 'storage' || value === 'sms' || value === 'email' || value === 'payment') return value
  return 'ai'
}

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const saving = ref(false)
const testing = ref<number | null>(null)
const healthLoading = ref(false)
const editVisible = ref(false)
const activeCategory = ref<TabKey>(normalizeCat(route.query.cat))
const providers = ref<AiProvider[]>([])
const editing = ref<AiProvider | null>(null)
const editingChannel = ref<SettingsChannelDef | null>(null)
const settingsMap = ref<Record<string, SystemSetting>>({})
const settingsForm = ref<Record<string, string>>({})
const dialogForm = ref<Record<string, string>>({})
const healthItems = ref<Record<string, IntegrationHealthItem>>({})

const form = reactive({
  name: '',
  description: '',
  base_url: '',
  api_key: '',
  model: '',
  daily_limit: 0,
  enabled: true,
})

const isSettingsCategory = computed(() => activeCategory.value !== 'ai')

function channelsOf(category: Exclude<TabKey, 'ai'>) {
  if (category === 'storage') return STORAGE_CHANNELS
  if (category === 'sms') return SMS_CHANNELS
  if (category === 'email') return EMAIL_CHANNELS
  return PAYMENT_CHANNELS
}

const settingsChannels = computed(() => (activeCategory.value === 'ai' ? [] : channelsOf(activeCategory.value)))

const healthRows = computed(() =>
  Object.entries(HEALTH_LABELS)
    .map(([key, label]) => ({ key, label, item: healthItems.value[key] }))
    .filter((row) => row.item),
)

const healthSummary = computed(() => {
  const checked = healthRows.value.filter((row) => !row.item?.skipped)
  const okCount = checked.filter((row) => row.item?.ok).length
  return {
    okCount,
    total: checked.length,
    ok: checked.length > 0 && okCount === checked.length,
  }
})

const settingsDialogWidth = computed(() => {
  const id = editingChannel.value?.id
  if (id === 'tencent_sms' || id === 'aliyun_sms') return '960px'
  if (id === 'wechat_pay') return '720px'
  return '640px'
})

const settingsFormLabelWidth = computed(() => {
  const id = editingChannel.value?.id
  if (id === 'tencent_sms' || id === 'aliyun_sms') return '300px'
  if (id === 'wechat_pay') return '168px'
  return '148px'
})

function asBoolString(value?: string) {
  const text = (value || '').trim().toLowerCase()
  if (text === '1' || text === 'true' || text === 'yes') return 'true'
  return 'false'
}

function parseExtra(raw?: string): Record<string, string> {
  try {
    const data = JSON.parse(raw || '{}') as Record<string, unknown>
    return Object.fromEntries(Object.entries(data).map(([key, value]) => [key, String(value ?? '')]))
  } catch {
    return {}
  }
}

function displayValue(field: SettingsFieldDef) {
  const raw = settingsForm.value[field.key] || ''
  if (!raw) return '未配置'
  if (field.type === 'secret' || raw.includes('****')) return raw.includes('****') ? raw : '已保存'
  const option = field.options?.find((item) => item.value === raw)
  if (option) return option.label
  if (raw.length > 42) return `${raw.slice(0, 18)}…`
  return raw
}

function channelSummary(channel: SettingsChannelDef) {
  if (channel.id === 'sms_global') {
    return settingsForm.value.sms_active_provider === 'tencent' ? '当前：腾讯云短信' : '当前：阿里云短信'
  }
  if (channel.enabledKey) return asBoolString(settingsForm.value[channel.enabledKey]) === 'true' ? '已启用' : '未启用'
  const filled = channel.fields.filter((field) => {
    const value = settingsForm.value[field.key]
    return Boolean(value) && value !== 'false'
  }).length
  return filled ? `已填写 ${filled} 项` : '尚未配置'
}

function isChannelEnabled(channel: SettingsChannelDef) {
  if (!channel.enabledKey) return true
  const source = editingChannel.value?.id === channel.id ? dialogForm.value : settingsForm.value
  return asBoolString(source[channel.enabledKey]) === 'true'
}

async function loadHealth() {
  healthLoading.value = true
  try {
    const data = await getIntegrationsHealth()
    const next: Record<string, IntegrationHealthItem> = {}
    for (const key of Object.keys(HEALTH_LABELS)) {
      if (data.items?.[key]) next[key] = data.items[key]
    }
    healthItems.value = next
  } catch {
    healthItems.value = {}
  } finally {
    healthLoading.value = false
  }
}

let loadSeq = 0

async function load() {
  const seq = ++loadSeq
  const category = activeCategory.value
  loading.value = true
  try {
    if (category === 'ai') {
      const rows = await listAiProviders()
      if (seq !== loadSeq) return
      providers.value = rows.filter((row) => row.code === 'deepseek')
    } else {
      const rows = await listAdminSettings(category)
      if (seq !== loadSeq || activeCategory.value !== category) return
      const allowed = new Set(allSettingsKeys(channelsOf(category)))
      const next: Record<string, string> = {}
      const map: Record<string, SystemSetting> = {}
      for (const row of rows) {
        if (!allowed.has(row.key)) continue
        map[row.key] = row
        next[row.key] = BOOL_KEYS.has(row.key) ? asBoolString(row.value) : row.value || ''
      }
      settingsMap.value = map
      settingsForm.value = next
    }
  } catch (error) {
    if (seq === loadSeq) ElMessage.error(error instanceof Error ? error.message : '配置加载失败')
  } finally {
    if (seq === loadSeq) loading.value = false
  }
}

function openEdit(row: AiProvider) {
  editing.value = row
  editingChannel.value = null
  const extra = parseExtra(row.extra_json)
  form.name = row.name
  form.description = row.description || ''
  form.base_url = row.base_url || ''
  form.api_key = ''
  form.model = extra.model || 'deepseek-chat'
  form.daily_limit = row.daily_limit || 0
  form.enabled = row.enabled
  editVisible.value = true
}

function openSettingsEdit(channel: SettingsChannelDef) {
  editing.value = null
  editingChannel.value = channel
  dialogForm.value = { ...settingsForm.value }
  for (const field of channel.fields) {
    if (field.type === 'secret') dialogForm.value[field.key] = ''
  }
  if (channel.enabledKey && !dialogForm.value[channel.enabledKey]) {
    dialogForm.value[channel.enabledKey] = 'false'
  }
  editVisible.value = true
}

async function handleSaveProvider() {
  if (!editing.value) return
  saving.value = true
  try {
    const extra = { ...parseExtra(editing.value.extra_json), model: form.model || 'deepseek-chat' }
    const payload: Record<string, unknown> = {
      name: form.name,
      description: form.description,
      base_url: form.base_url,
      enabled: form.enabled,
      daily_limit: form.daily_limit,
      extra_json: JSON.stringify(extra),
    }
    if (form.api_key.trim()) payload.api_key = form.api_key.trim()
    await updateAiProvider(editing.value.id, payload)
    ElMessage.success('服务配置已保存')
    editVisible.value = false
    await load()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '保存失败')
  } finally {
    saving.value = false
  }
}

async function handleSaveSettings() {
  const channel = editingChannel.value
  if (!channel || activeCategory.value === 'ai') return
  saving.value = true
  try {
    const keys = new Set<string>(channel.fields.map((field) => field.key))
    if (channel.enabledKey) keys.add(channel.enabledKey)
    const items = [...keys].map((key) => {
      const meta = settingsMap.value[key]
      const raw = dialogForm.value[key] ?? ''
      const secret = channel.fields.some((field) => field.key === key && field.type === 'secret')
      const value = secret && (!raw.trim() || raw.includes('****')) ? '' : raw
      return {
        key,
        value,
        category: activeCategory.value,
        label: meta?.label,
        value_type: meta?.value_type,
      }
    })
    await updateAdminSettings(items)
    ElMessage.success('配置已保存，实时生效')
    editVisible.value = false
    await load()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '保存失败')
  } finally {
    saving.value = false
  }
}

async function handleTest(row: AiProvider) {
  testing.value = row.id
  try {
    const res = await testAiProvider(row.id)
    ElMessage[res.success ? 'success' : 'error'](`${res.message}（${res.latency_ms}ms）`)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '测试失败')
  } finally {
    testing.value = null
  }
}

watch(activeCategory, (cat, prev) => {
  if (cat === prev) return
  const current = normalizeCat(route.query.cat)
  if (current !== cat) router.replace({ query: { ...route.query, cat } })
  load()
})

watch(
  () => route.query.cat,
  (cat) => {
    const next = normalizeCat(cat)
    if (activeCategory.value !== next) activeCategory.value = next
  },
)

onMounted(() => {
  load()
  loadHealth()
})
</script>

<template>
  <div v-loading="loading" class="admin-page integrations-page">
    <div class="admin-page-header">
      <div>
        <h2>第三方服务集成</h2>
        <p class="admin-page-desc">后台配置为唯一标准，运行时自动读取以下参数</p>
      </div>
    </div>

    <el-card v-loading="healthLoading" class="admin-panel-card health-card">
      <template #header>
        <div class="health-head">
          <span>集成健康检查</span>
          <el-button size="small" @click="loadHealth">刷新</el-button>
        </div>
      </template>
      <el-alert
        v-if="healthRows.length"
        :title="`探活 ${healthSummary.okCount}/${healthSummary.total}${healthSummary.ok ? ' · 全部正常' : ' · 存在异常'}`"
        :type="healthSummary.ok ? 'success' : 'warning'"
        show-icon
        :closable="false"
        class="health-alert"
      />
      <el-row v-if="healthRows.length" :gutter="12">
        <el-col v-for="row in healthRows" :key="row.key" :xs="24" :sm="12" :md="8">
          <div class="health-item" :class="{ ok: row.item?.ok && !row.item?.skipped, skipped: row.item?.skipped }">
            <span class="health-name">{{ row.label }}</span>
            <el-tag :type="row.item?.skipped ? 'info' : row.item?.ok ? 'success' : 'danger'" size="small">
              {{ row.item?.skipped ? '未开启' : row.item?.ok ? '正常' : '异常' }}
            </el-tag>
            <p v-if="!row.item?.skipped" class="health-detail">
              {{ row.item?.detail }}{{ row.item?.latency_ms != null ? ` · ${row.item.latency_ms}ms` : '' }}
            </p>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <div class="admin-panel-card integrations-panel">
      <el-tabs v-model="activeCategory" class="admin-segment-tabs">
        <el-tab-pane v-for="tab in TABS" :key="tab.key" :name="tab.key">
          <template #label>
            <span class="segment-tab-label">{{ tab.label }}</span>
          </template>
        </el-tab-pane>
      </el-tabs>

      <div class="admin-panel-body integrations-panel-body">
        <el-alert
          v-if="activeCategory === 'storage'"
          type="info"
          :closable="false"
          show-icon
          class="tab-note"
          title="这里填写各云存储的密钥和空间。当前实际使用哪一种，在基础配置的上传配置里选择。"
        />
        <el-alert
          v-if="activeCategory === 'payment'"
          type="info"
          :closable="false"
          show-icon
          class="tab-note"
          title="社区版只保存微信支付和支付宝参数，没有会员下单、余额支付和抖音支付。"
        />

        <div v-if="!isSettingsCategory" class="integration-grid">
          <el-card v-for="item in providers" :key="item.id" shadow="hover" class="integration-ep-card">
            <template #header>
              <div class="integration-card-head">
                <div class="integration-card-head-main">
                  <span class="icon-badge">
                    <el-icon :size="20"><component :is="resolveAdminIcon('ai')" /></el-icon>
                  </span>
                  <div>
                    <h3>{{ item.name }}</h3>
                    <p>{{ item.description || '法律咨询使用的对话模型' }}</p>
                  </div>
                </div>
                <el-tag :type="item.enabled ? 'success' : 'info'" effect="dark" round size="small">
                  {{ item.enabled ? '已启用' : '已禁用' }}
                </el-tag>
              </div>
            </template>
            <el-descriptions :column="1" size="small" border>
              <el-descriptions-item label="API Key">{{ item.api_key_masked || '未配置' }}</el-descriptions-item>
              <el-descriptions-item v-if="item.base_url" label="接口地址">{{ item.base_url }}</el-descriptions-item>
              <el-descriptions-item label="模型">{{ parseExtra(item.extra_json).model || 'deepseek-chat' }}</el-descriptions-item>
              <el-descriptions-item label="今日调用">{{ item.call_count_today }} / {{ item.daily_limit }}</el-descriptions-item>
            </el-descriptions>
            <div class="integration-card-actions">
              <el-button type="primary" plain @click="openEdit(item)">
                <el-icon><Edit /></el-icon>
                编辑配置
              </el-button>
              <el-button type="warning" plain :loading="testing === item.id" @click="handleTest(item)">
                <el-icon v-if="testing !== item.id"><Lightning /></el-icon>
                {{ testing === item.id ? '测试中…' : '测试连接' }}
              </el-button>
            </div>
          </el-card>
          <el-empty v-if="!providers.length" description="还没有对话模型。请重启后端，启动时会写入默认可编辑的模型配置。" />
        </div>

        <div v-else class="integration-grid">
          <el-card
            v-for="channel in settingsChannels"
            :key="channel.id"
            shadow="hover"
            class="integration-ep-card"
            :class="{ 'integration-ep-card--strategy': !channel.enabledKey }"
          >
            <template #header>
              <div class="integration-card-head">
                <div class="integration-card-head-main">
                  <span class="icon-badge">
                    <el-icon :size="20"><component :is="resolveAdminIcon(channel.icon)" /></el-icon>
                  </span>
                  <div>
                    <h3>{{ channel.name }}</h3>
                    <p>{{ channel.description }}</p>
                  </div>
                </div>
                <el-tag
                  :type="!channel.enabledKey || asBoolString(settingsForm[channel.enabledKey]) === 'true' ? 'success' : 'info'"
                  effect="dark"
                  round
                  size="small"
                >
                  {{ channel.enabledKey ? (asBoolString(settingsForm[channel.enabledKey]) === 'true' ? '已启用' : '已禁用') : '策略' }}
                </el-tag>
              </div>
            </template>
            <el-descriptions :column="1" size="small" border>
              <el-descriptions-item label="状态">{{ channelSummary(channel) }}</el-descriptions-item>
              <el-descriptions-item v-for="field in channel.fields.slice(0, 3)" :key="field.key" :label="field.label || field.key">
                {{ displayValue(field) }}
              </el-descriptions-item>
              <el-descriptions-item v-if="channel.fields.length > 3" label="更多">
                共 {{ channel.fields.length }} 项参数
              </el-descriptions-item>
            </el-descriptions>
            <div class="integration-card-actions">
              <el-button type="primary" plain @click="openSettingsEdit(channel)">
                <el-icon><Edit /></el-icon>
                {{ channel.id === 'sms_global' ? '编辑策略' : '编辑配置' }}
              </el-button>
            </div>
          </el-card>
        </div>
      </div>
    </div>

    <el-dialog
      v-model="editVisible"
      :title="editingChannel ? `编辑 · ${editingChannel.name}` : `编辑 · ${editing?.name || '对话模型'}`"
      :width="editingChannel ? settingsDialogWidth : '620px'"
      append-to-body
      align-center
      destroy-on-close
    >
      <el-form
        v-if="editingChannel"
        label-position="right"
        :label-width="settingsFormLabelWidth"
      >
        <el-form-item v-if="editingChannel.enabledKey" label="启用">
          <el-switch v-model="dialogForm[editingChannel.enabledKey]" active-value="true" inactive-value="false" />
        </el-form-item>

        <template v-if="isChannelEnabled(editingChannel)">
          <el-alert
            v-if="editingChannel.id === 'tencent_sms'"
            type="info"
            :closable="false"
            show-icon
            class="dialog-alert"
            title="SecretId 与 SecretKey 必须成对填写。模板变量个数要和模板正文里的 {1}{2} 一致。"
          />
          <el-alert
            v-if="editingChannel.id === 'aliyun_sms'"
            type="info"
            :closable="false"
            show-icon
            class="dialog-alert"
            title="签名和模板都要先在阿里云审核通过。模板参数使用 code。"
          />
          <el-alert
            v-if="editingChannel.id === 'smtp'"
            type="info"
            :closable="false"
            show-icon
            class="dialog-alert"
            title="QQ 邮箱示例：主机 smtp.qq.com，端口 465，启用 TLS，用户名和发件人都填完整邮箱，密码填授权码。"
          />
          <el-alert
            v-if="editingChannel.id === 'wechat_pay'"
            type="warning"
            :closable="false"
            show-icon
            class="dialog-alert"
            title="公钥模式请填写微信支付公钥和公钥 ID。平台证书请留空，不要把商户证书填进去。"
          />

          <el-form-item v-for="field in editingChannel.fields" :key="field.key" :label="field.label || field.key">
            <el-select
              v-if="field.type === 'select' && field.options?.length"
              v-model="dialogForm[field.key]"
              style="width: 100%"
            >
              <el-option v-for="opt in field.options" :key="opt.value" :label="opt.label" :value="opt.value" />
            </el-select>
            <el-input
              v-else-if="field.type === 'textarea' || field.long"
              v-model="dialogForm[field.key]"
              type="textarea"
              :rows="4"
              :placeholder="field.placeholder || ''"
            />
            <el-input
              v-else-if="field.type === 'secret'"
              v-model="dialogForm[field.key]"
              type="password"
              show-password
              :placeholder="field.placeholder || '留空则不修改'"
            />
            <el-input v-else v-model="dialogForm[field.key]" :placeholder="field.placeholder || ''" />
            <p v-if="field.hint" class="field-hint">{{ field.hint }}</p>
          </el-form-item>
        </template>
      </el-form>

      <el-form v-else label-width="108px">
        <el-form-item label="名称">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="form.description" />
        </el-form-item>
        <el-form-item label="API Key">
          <el-input v-model="form.api_key" type="password" show-password placeholder="留空则不修改已保存的密钥" />
          <p v-if="editing?.api_key_masked" class="field-hint">已保存 {{ editing.api_key_masked }}</p>
        </el-form-item>
        <el-form-item label="接口地址">
          <el-input v-model="form.base_url" placeholder="https://api.deepseek.com/v1" />
        </el-form-item>
        <el-form-item label="模型名">
          <el-input v-model="form.model" placeholder="deepseek-chat" />
        </el-form-item>
        <el-form-item label="每日上限">
          <el-input-number v-model="form.daily_limit" :min="0" style="width: 100%" />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="form.enabled" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="editingChannel ? handleSaveSettings() : handleSaveProvider()">
          保存配置
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.integrations-page .admin-page-desc {
  margin: 4px 0 0;
  max-width: 640px;
}

.health-card {
  margin-bottom: 16px;
}

.health-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.health-alert {
  margin-bottom: 12px;
}

.health-item {
  margin-bottom: 12px;
  padding: 12px 14px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 10px;
  background: var(--el-fill-color-blank);
}

.health-item.ok {
  border-color: var(--el-color-success-light-5);
}

.health-item.skipped {
  opacity: 0.72;
}

.health-name {
  margin-right: 8px;
  font-weight: 600;
}

.health-detail {
  margin: 8px 0 0;
  font-size: 12px;
  line-height: 1.5;
  color: var(--el-text-color-secondary);
  word-break: break-all;
}

.tab-note,
.dialog-alert {
  margin-bottom: 16px;
}

.integration-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
  width: 100%;
}

.integration-ep-card {
  height: 100%;
}

.integration-ep-card :deep(.el-card__header) {
  padding: 14px 16px;
  background: var(--el-fill-color-light);
}

.integration-ep-card--strategy :deep(.el-card__header) {
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.08), rgba(118, 75, 162, 0.08));
}

.integration-card-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}

.integration-card-head-main {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  min-width: 0;
}

.integration-card-head h3 {
  margin: 0 0 4px;
  font-size: 15px;
  font-weight: 600;
}

.integration-card-head p {
  margin: 0;
  font-size: 12px;
  line-height: 1.5;
  color: var(--el-text-color-secondary);
}

.icon-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  margin-top: 2px;
  border-radius: 10px;
  color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
  flex-shrink: 0;
}

.integration-card-actions {
  display: flex;
  gap: 10px;
  margin-top: 16px;
}

.integration-card-actions .el-button {
  flex: 1;
}

.field-hint {
  margin: 6px 0 0;
  font-size: 12px;
  line-height: 1.5;
  color: var(--el-text-color-secondary);
}
</style>
