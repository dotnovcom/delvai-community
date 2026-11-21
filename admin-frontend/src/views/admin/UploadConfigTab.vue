<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { listAdminSettings, updateAdminSettings, type SystemSetting } from '../../api/admin'

const UPLOAD_KEYS = ['upload_active_provider', 'upload_max_size_mb', 'upload_allowed_types']

const PROVIDER_OPTIONS = [
  { label: '本地存储', value: 'local' },
  { label: '阿里云 OSS', value: 'aliyun' },
  { label: '腾讯云 COS', value: 'tencent' },
  { label: '七牛云 Kodo', value: 'qiniu' },
]

const loading = ref(false)
const saving = ref(false)
const settingsMap = ref<Record<string, SystemSetting>>({})
const form = ref({
  upload_active_provider: 'local',
  upload_max_size_mb: 10,
  upload_allowed_types: 'jpg,jpeg,png,gif,webp,pdf,doc,docx,xls,xlsx,txt',
})

async function load() {
  loading.value = true
  try {
    const items = await listAdminSettings('basic')
    const map: Record<string, SystemSetting> = {}
    for (const item of items) {
      if (UPLOAD_KEYS.includes(item.key)) {
        map[item.key] = item
        if (item.key === 'upload_max_size_mb') {
          form.value.upload_max_size_mb = Number(item.value || 10)
        } else if (item.key === 'upload_active_provider') {
          form.value.upload_active_provider = item.value || 'local'
        } else if (item.key === 'upload_allowed_types') {
          form.value.upload_allowed_types = item.value || form.value.upload_allowed_types
        }
      }
    }
    settingsMap.value = map
    const legacy = items.find((i) => i.key === 'upload_provider')
    if (legacy?.value === 'oss' && form.value.upload_active_provider === 'local') {
      form.value.upload_active_provider = 'aliyun'
    }
  } finally {
    loading.value = false
  }
}

async function save() {
  saving.value = true
  try {
    const items = UPLOAD_KEYS.map((key) => ({
      key,
      value: key === 'upload_max_size_mb' ? String(form.value.upload_max_size_mb) : String(form.value[key as keyof typeof form.value] ?? ''),
      category: settingsMap.value[key]?.category || 'basic',
      label: settingsMap.value[key]?.label,
      value_type: settingsMap.value[key]?.value_type,
    }))
    await updateAdminSettings(items)
    ElMessage.success('上传配置已保存')
    await load()
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<template>
  <div v-loading="loading" class="admin-page upload-config-page">
    <div class="admin-card settings-card">
      <el-form label-width="220px" label-position="left" class="settings-form">
        <div class="settings-section-title">上传策略</div>
        <el-form-item label="单文件大小上限">
          <el-input-number v-model="form.upload_max_size_mb" :min="1" :max="512" />
          <span class="field-hint">单位：MB</span>
        </el-form-item>
        <el-form-item label="允许文件类型">
          <el-input
            v-model="form.upload_allowed_types"
            placeholder="jpg,jpeg,png,gif,pdf"
          />
          <p class="field-desc">多个扩展名用英文逗号分隔，不含点号</p>
        </el-form-item>
        <el-form-item label="当前存储方式">
          <el-select v-model="form.upload_active_provider" style="width: 100%">
            <el-option
              v-for="opt in PROVIDER_OPTIONS"
              :key="opt.value"
              :label="opt.label"
              :value="opt.value"
            />
          </el-select>
          <p class="field-desc">
            选择云存储后，请在
            <router-link to="/admin/hub/system/integrations?cat=storage">服务集成 → 文件存储</router-link>
            中配置对应参数
          </p>
        </el-form-item>
      </el-form>
    </div>
    <div class="settings-footer">
      <el-button type="primary" :loading="saving" @click="save">保存上传配置</el-button>
    </div>
  </div>
</template>

<style scoped>
.upload-config-page { width: 100%; }
.settings-card { width: 100%; box-sizing: border-box; }
.settings-form { max-width: 920px; padding: 16px 8px; width: 100%; }
.settings-section-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--ft-primary);
  margin: 8px 0 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--ft-border);
}
.field-hint { margin-left: 12px; font-size: 13px; color: var(--ft-text-secondary); }
.field-desc {
  margin: 6px 0 0;
  font-size: 12px;
  color: var(--ft-text-secondary);
  line-height: 1.5;
}
.field-desc a { color: var(--ft-primary); }
.settings-footer { margin-top: 16px; padding: 0 8px 8px; }
</style>
