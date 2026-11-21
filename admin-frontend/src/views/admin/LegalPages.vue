<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import AdminRichEditor from '../../components/admin/AdminRichEditor.vue'
import { listAdminSettings, syncLegalPagesDefaults, updateAdminSettings } from '../../api/admin'

const loading = ref(false)
const saving = ref(false)
const syncing = ref(false)
const activeDoc = ref('agreement')
const agreementHtml = ref('')
const privacyHtml = ref('')
const aboutHtml = ref('')
const contactHtml = ref('')
const contractReviewHelpHtml = ref('')
const contractExtractHelpHtml = ref('')

async function load() {
  loading.value = true
  try {
    const items = await listAdminSettings('legal_page')
    for (const item of items) {
      if (item.key === 'user_agreement_html') agreementHtml.value = item.value || ''
      if (item.key === 'privacy_policy_html') privacyHtml.value = item.value || ''
      if (item.key === 'about_platform_html') aboutHtml.value = item.value || ''
      if (item.key === 'contact_us_html') contactHtml.value = item.value || ''
      if (item.key === 'contract_review_help_html') contractReviewHelpHtml.value = item.value || ''
      if (item.key === 'contract_extract_help_html') contractExtractHelpHtml.value = item.value || ''
    }
  } finally {
    loading.value = false
  }
}

async function save() {
  saving.value = true
  try {
    await updateAdminSettings([
      { key: 'user_agreement_html', value: agreementHtml.value, category: 'legal_page' },
      { key: 'privacy_policy_html', value: privacyHtml.value, category: 'legal_page' },
      { key: 'about_platform_html', value: aboutHtml.value, category: 'legal_page' },
      { key: 'contact_us_html', value: contactHtml.value, category: 'legal_page' },
      { key: 'contract_review_help_html', value: contractReviewHelpHtml.value, category: 'legal_page' },
      { key: 'contract_extract_help_html', value: contractExtractHelpHtml.value, category: 'legal_page' },
    ])
    ElMessage.success('内容已保存')
  } finally {
    saving.value = false
  }
}

async function syncDefaults() {
  try {
    await ElMessageBox.confirm(
      '将从代码中的默认模板覆盖「用户协议」与「隐私政策」正文，当前未保存的编辑会丢失。是否继续？',
      '同步默认模板',
      { type: 'warning', confirmButtonText: '同步', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  syncing.value = true
  try {
    const res = await syncLegalPagesDefaults({
      keys: ['user_agreement_html', 'privacy_policy_html'],
      force: true,
    })
    if (res.count > 0) {
      await load()
      ElMessage.success(`已同步 ${res.count} 项默认正文`)
    } else {
      ElMessage.info('无内容变更')
    }
  } finally {
    syncing.value = false
  }
}

onMounted(load)
</script>

<template>
  <div v-loading="loading" class="admin-page">
    <div class="admin-page-header">
      <div>
        <h2>协议政策</h2>
        <p class="admin-page-desc">
          用户协议、隐私政策、关于平台、联系我们等静态页正文保存在数据库。空内容会在服务启动时自动写入默认模板；也可点击下方按钮从代码默认模板同步用户协议与隐私政策。
        </p>
      </div>
      <div class="admin-page-header__actions">
        <el-button :loading="syncing" @click="syncDefaults">同步默认模板</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存全部</el-button>
      </div>
    </div>

    <div class="admin-panel-card">
      <el-tabs v-model="activeDoc" class="admin-segment-tabs">
        <el-tab-pane name="agreement">
          <template #label>
            <span class="segment-tab-label">用户服务协议</span>
          </template>
        </el-tab-pane>
        <el-tab-pane name="privacy">
          <template #label>
            <span class="segment-tab-label">隐私政策</span>
          </template>
        </el-tab-pane>
        <el-tab-pane name="about">
          <template #label>
            <span class="segment-tab-label">关于平台</span>
          </template>
        </el-tab-pane>
        <el-tab-pane name="contact">
          <template #label>
            <span class="segment-tab-label">联系我们</span>
          </template>
        </el-tab-pane>
        <el-tab-pane name="contractReview">
          <template #label>
            <span class="segment-tab-label">合同审查说明</span>
          </template>
        </el-tab-pane>
        <el-tab-pane name="contractExtract">
          <template #label>
            <span class="segment-tab-label">合同抽取说明</span>
          </template>
        </el-tab-pane>
      </el-tabs>
      <div class="admin-panel-body">
        <AdminRichEditor
          v-if="activeDoc === 'agreement'"
          :key="'agreement'"
          v-model="agreementHtml"
          placeholder="编辑用户协议正文…"
          min-height="480px"
        />
        <AdminRichEditor
          v-else-if="activeDoc === 'privacy'"
          :key="'privacy'"
          v-model="privacyHtml"
          placeholder="编辑隐私政策正文…"
          min-height="480px"
        />
        <AdminRichEditor
          v-else-if="activeDoc === 'about'"
          :key="'about'"
          v-model="aboutHtml"
          placeholder="编辑「关于平台」正文（移动端设置页展示）…"
          min-height="480px"
        />
        <AdminRichEditor
          v-else-if="activeDoc === 'contact'"
          :key="'contact'"
          v-model="contactHtml"
          placeholder="编辑「联系我们」正文（移动端设置页展示）…"
          min-height="480px"
        />
        <AdminRichEditor
          v-else-if="activeDoc === 'contractReview'"
          :key="'contract-review'"
          v-model="contractReviewHelpHtml"
          placeholder="编辑合同审查页右上角「使用说明」…"
          min-height="480px"
        />
        <AdminRichEditor
          v-else
          :key="'contract-extract'"
          v-model="contractExtractHelpHtml"
          placeholder="编辑合同抽取页右上角「使用说明」…"
          min-height="480px"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.admin-page-header__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}
</style>
