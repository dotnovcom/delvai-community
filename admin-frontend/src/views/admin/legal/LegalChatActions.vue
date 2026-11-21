<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { UploadRequestOptions } from 'element-plus'
import {
  deleteMessageShare,
  getAiChatSettings,
  listMessageFeedbacks,
  listMessageShares,
  saveAiChatSettings,
  uploadAdminFile,
  type AdminMessageFeedback,
  type AdminMessageShare,
} from '../../../api/admin'
import { userOrigin } from '../../../utils/userOrigin'

const saving = ref(false)
const form = reactive({
  ai_reply_avatar: '',
  ai_action_copy: true,
  ai_action_regenerate: true,
  ai_action_like: true,
  ai_action_dislike: true,
  ai_action_speak: true,
  ai_action_share: true,
})

const switches = [
  { key: 'ai_action_copy', label: '复制' },
  { key: 'ai_action_regenerate', label: '重新生成' },
  { key: 'ai_action_like', label: '赞' },
  { key: 'ai_action_dislike', label: '踩' },
  { key: 'ai_action_speak', label: '朗读' },
  { key: 'ai_action_share', label: '分享' },
] as const

const feedbacks = ref<AdminMessageFeedback[]>([])
const feedbackTotal = ref(0)
const feedbackPage = ref(1)
const feedbackVote = ref('')
const shares = ref<AdminMessageShare[]>([])
const shareTotal = ref(0)
const sharePage = ref(1)
const loadingFeedback = ref(false)
const loadingShare = ref(false)

function isOn(value: string | null | undefined) {
  return ['1', 'true', 'yes', 'on'].includes(String(value || '').toLowerCase())
}

async function loadSettings() {
  const rows = await getAiChatSettings()
  for (const row of rows) {
    if (row.key === 'ai_reply_avatar') form.ai_reply_avatar = row.value || ''
    else if (row.key in form) {
      (form as Record<string, string | boolean>)[row.key] = isOn(row.value)
    }
  }
}

async function loadFeedbacks() {
  loadingFeedback.value = true
  try {
    const res = await listMessageFeedbacks(feedbackPage.value, 10, feedbackVote.value)
    feedbacks.value = res.items
    feedbackTotal.value = res.total
  } finally {
    loadingFeedback.value = false
  }
}

async function loadShares() {
  loadingShare.value = true
  try {
    const res = await listMessageShares(sharePage.value, 10)
    shares.value = res.items
    shareTotal.value = res.total
  } finally {
    loadingShare.value = false
  }
}

async function handleUpload(options: UploadRequestOptions) {
  const file = options.file as File
  const res = await uploadAdminFile(file)
  form.ai_reply_avatar = res.url
  ElMessage.success('头像已上传，请保存后生效')
  options.onSuccess?.(res)
}

async function save() {
  saving.value = true
  try {
    await saveAiChatSettings([
      { key: 'ai_reply_avatar', value: form.ai_reply_avatar.trim(), category: 'ai_chat', label: 'AI 回复头像', value_type: 'image' },
      { key: 'ai_action_copy', value: String(form.ai_action_copy), category: 'ai_chat', label: '显示复制', value_type: 'boolean' },
      { key: 'ai_action_regenerate', value: String(form.ai_action_regenerate), category: 'ai_chat', label: '显示重新生成', value_type: 'boolean' },
      { key: 'ai_action_like', value: String(form.ai_action_like), category: 'ai_chat', label: '显示赞', value_type: 'boolean' },
      { key: 'ai_action_dislike', value: String(form.ai_action_dislike), category: 'ai_chat', label: '显示踩', value_type: 'boolean' },
      { key: 'ai_action_speak', value: String(form.ai_action_speak), category: 'ai_chat', label: '显示朗读', value_type: 'boolean' },
      { key: 'ai_action_share', value: String(form.ai_action_share), category: 'ai_chat', label: '显示分享', value_type: 'boolean' },
    ])
    ElMessage.success('已保存')
  } finally {
    saving.value = false
  }
}

function shareUrl(path: string) {
  return `${userOrigin()}${path}`
}

async function copyLink(path: string) {
  const url = shareUrl(path)
  await navigator.clipboard.writeText(url)
  ElMessage.success('链接已复制')
}

async function removeShare(row: AdminMessageShare) {
  await ElMessageBox.confirm('删除后，该链接和二维码将无法再打开。', '删除分享', { type: 'warning' })
  await deleteMessageShare(row.id)
  ElMessage.success('已删除')
  await loadShares()
}

onMounted(() => {
  loadSettings()
  loadFeedbacks()
  loadShares()
})
</script>

<template>
  <div class="chat-actions">
    <section class="panel">
      <h3>AI 回复头像</h3>
      <p class="hint">用户端法律咨询里，AI 回复左侧显示这里配置的图片。留空则显示「AI」。</p>
      <div class="avatar-row">
        <el-avatar :size="64" :src="form.ai_reply_avatar || undefined">AI</el-avatar>
        <div class="avatar-fields">
          <el-input v-model="form.ai_reply_avatar" placeholder="图片地址，或点击上传" clearable />
          <el-upload :show-file-list="false" accept="image/*" :http-request="handleUpload">
            <el-button>上传图片</el-button>
          </el-upload>
        </div>
      </div>

      <h3>回复底部操作</h3>
      <p class="hint">关闭后，用户端对应按钮不再显示。赞、踩和分享的记录仍可在下方查看。</p>
      <div class="switch-grid">
        <div v-for="item in switches" :key="item.key" class="switch-item">
          <span>{{ item.label }}</span>
          <el-switch v-model="form[item.key]" />
        </div>
      </div>
      <el-button type="primary" :loading="saving" @click="save">保存配置</el-button>
    </section>

    <section class="panel">
      <div class="panel-head">
        <h3>赞 / 踩</h3>
        <el-select v-model="feedbackVote" clearable placeholder="全部" style="width: 140px" @change="feedbackPage = 1; loadFeedbacks()">
          <el-option label="赞" value="like" />
          <el-option label="踩" value="dislike" />
        </el-select>
      </div>
      <el-table v-loading="loadingFeedback" :data="feedbacks" size="small">
        <el-table-column label="用户" min-width="140">
          <template #default="{ row }">{{ row.nickname || row.phone || row.user_id }}</template>
        </el-table-column>
        <el-table-column label="评价" width="80">
          <template #default="{ row }">{{ row.vote === 'like' ? '赞' : '踩' }}</template>
        </el-table-column>
        <el-table-column prop="content" label="回复摘要" min-width="240" show-overflow-tooltip />
        <el-table-column label="时间" width="170">
          <template #default="{ row }">{{ new Date(row.updated_at || row.created_at).toLocaleString('zh-CN') }}</template>
        </el-table-column>
      </el-table>
      <el-pagination
        v-if="feedbackTotal > 10"
        layout="prev, pager, next"
        :total="feedbackTotal"
        :page-size="10"
        :current-page="feedbackPage"
        @current-change="(p: number) => { feedbackPage = p; loadFeedbacks() }"
      />
    </section>

    <section class="panel">
      <h3>分享记录</h3>
      <el-table v-loading="loadingShare" :data="shares" size="small">
        <el-table-column label="用户" min-width="120">
          <template #default="{ row }">{{ row.nickname || row.phone || row.user_id }}</template>
        </el-table-column>
        <el-table-column prop="question" label="提问" min-width="160" show-overflow-tooltip />
        <el-table-column prop="answer" label="回复" min-width="200" show-overflow-tooltip />
        <el-table-column prop="view_count" label="打开次数" width="90" />
        <el-table-column label="时间" width="170">
          <template #default="{ row }">{{ new Date(row.created_at).toLocaleString('zh-CN') }}</template>
        </el-table-column>
        <el-table-column label="操作" width="160">
          <template #default="{ row }">
            <el-button link type="primary" @click="copyLink(row.path)">复制链接</el-button>
            <el-button link type="danger" @click="removeShare(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination
        v-if="shareTotal > 10"
        layout="prev, pager, next"
        :total="shareTotal"
        :page-size="10"
        :current-page="sharePage"
        @current-change="(p: number) => { sharePage = p; loadShares() }"
      />
    </section>
  </div>
</template>

<style scoped>
.chat-actions {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.panel {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 16px 18px 18px;
}

.panel h3 {
  margin: 16px 0 6px;
  font-size: 15px;
}

.panel h3:first-child {
  margin-top: 0;
}

.hint {
  margin: 0 0 12px;
  color: #64748b;
  font-size: 13px;
}

.avatar-row {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 8px;
}

.avatar-fields {
  flex: 1;
  display: flex;
  gap: 8px;
}

.switch-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px 16px;
  margin-bottom: 14px;
}

.switch-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
}

.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.panel-head h3 {
  margin: 0 0 12px;
}
</style>
