<template>
  <div class="ai-provider-page">
    <el-card shadow="never">
      <template #header>通用对话模型</template>
      <p class="hint">社区版使用你自己的对话模型密钥。保存后立即生效，密钥只保存在本机数据库。</p>
      <el-form v-if="provider" label-width="120px" @submit.prevent>
        <el-form-item label="名称">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="接口地址">
          <el-input v-model="form.base_url" placeholder="https://api.example.com/v1" />
        </el-form-item>
        <el-form-item label="模型密钥">
          <el-input v-model="form.api_key" type="password" show-password placeholder="留空则不修改已保存的密钥" />
          <span v-if="provider.api_key_masked" class="masked">已保存 {{ provider.api_key_masked }}</span>
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="form.enabled" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="saving" @click="save">保存</el-button>
          <el-button :loading="testing" @click="test">测试连接</el-button>
        </el-form-item>
      </el-form>
      <el-empty v-else-if="!loading" description="还没有对话模型，请先在数据库写入 deepseek 配置" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { listAiProviders, testAiProvider, updateAiProvider, type AiProvider } from '../../api/admin'

const loading = ref(false)
const saving = ref(false)
const testing = ref(false)
const provider = ref<AiProvider | null>(null)
const form = reactive({
  name: '',
  base_url: '',
  api_key: '',
  enabled: true,
})

function fill(row: AiProvider) {
  provider.value = row
  form.name = row.name
  form.base_url = row.base_url || ''
  form.api_key = ''
  form.enabled = row.enabled
}

async function load() {
  loading.value = true
  try {
    const rows = await listAiProviders('chat')
    const row = rows.find((item) => item.code === 'deepseek') || rows[0]
    if (row) fill(row)
  } finally {
    loading.value = false
  }
}

async function save() {
  if (!provider.value) return
  saving.value = true
  try {
    const payload: Record<string, unknown> = {
      name: form.name,
      base_url: form.base_url,
      enabled: form.enabled,
    }
    if (form.api_key.trim()) payload.api_key = form.api_key.trim()
    fill(await updateAiProvider(provider.value.id, payload))
    ElMessage.success('已保存')
  } finally {
    saving.value = false
  }
}

async function test() {
  if (!provider.value) return
  testing.value = true
  try {
    const result = await testAiProvider(provider.value.id)
    ElMessage[result.success ? 'success' : 'error'](result.message || (result.success ? '连接成功' : '连接失败'))
  } finally {
    testing.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.hint { color: var(--el-text-color-secondary); margin-top: 0; }
.masked { margin-left: 8px; color: var(--el-text-color-secondary); font-size: 12px; }
</style>
