<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import AdminFilterBar from '../../components/admin/AdminFilterBar.vue'
import AdminTableCard from '../../components/admin/AdminTableCard.vue'
import AdminPagination from '../../components/admin/AdminPagination.vue'
import AdminIconAction from '../../components/admin/AdminIconAction.vue'
import AdminOpBtnGroup from '../../components/admin/AdminOpBtnGroup.vue'
import {
  listAdminConversations,
  getAdminConversationDetail,
  type AdminConversation,
  type AdminConversationDetail,
} from '../../api/admin'
import { labelOf, conversationStatusLabel } from '../../utils/adminLabels'

const route = useRoute()
const conversations = ref<AdminConversation[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const keyword = ref('')
const loading = ref(false)
const detailVisible = ref(false)
const detailLoading = ref(false)
const detail = ref<AdminConversationDetail | null>(null)

const TYPE_MAP: Record<string, string> = {
  text: '文字',
  voice: '语音',
  video: '视频',
}

async function load() {
  loading.value = true
  try {
    const userId = route.query.user_id ? Number(route.query.user_id) : undefined
    const res = await listAdminConversations({
      page: page.value,
      size: pageSize.value,
      keyword: keyword.value || undefined,
      user_id: userId,
    })
    conversations.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

async function openDetail(row: AdminConversation) {
  detailVisible.value = true
  detailLoading.value = true
  try {
    detail.value = await getAdminConversationDetail(row.id)
  } finally {
    detailLoading.value = false
  }
}

function formatTime(t: string) {
  return t?.slice(0, 19).replace('T', ' ')
}

onMounted(load)
</script>

<template>
  <div class="admin-page admin-page--fill">
    <div class="admin-page-header">
      <div>
        <h2>对话管理</h2>
        <p class="admin-page-desc">审计用户与 AI 的历史会话记录（只读，不含前台业务配置）。</p>
      </div>
    </div>

    <AdminFilterBar>
      <el-input v-model="keyword" placeholder="标题 / 手机号 / 昵称" style="width: 260px" clearable @keyup.enter="load" />
      <el-button type="primary" @click="load">搜索</el-button>
    </AdminFilterBar>

    <AdminTableCard :loading="loading" fill>
    <el-table :data="conversations" class="admin-table" stripe height="100%">
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="title" label="标题" min-width="180" show-overflow-tooltip />
      <el-table-column label="用户" width="140">
        <template #default="{ row }">{{ row.user_nickname || row.user_phone || row.user_id }}</template>
      </el-table-column>
      <el-table-column label="类型" width="90" align="center">
        <template #default="{ row }">
          <el-tag size="small" type="info">{{ TYPE_MAP[row.interaction_type] || row.interaction_type }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="message_count" label="消息数" width="80" align="center" />
      <el-table-column label="状态" width="90" align="center">
        <template #default="{ row }">
          <el-tag
            size="small"
            :type="row.status === 'active' ? 'success' : row.status === 'archived' ? 'warning' : 'info'"
          >
            {{ labelOf(conversationStatusLabel, row.status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="更新时间" width="170">
        <template #default="{ row }">{{ formatTime(row.updated_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="88" fixed="right" align="center">
        <template #default="{ row }">
          <AdminOpBtnGroup nowrap class="admin-table-actions">
            <AdminIconAction action="view" @click="openDetail(row)" />
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
      title="对话详情"
      size="520px"
      destroy-on-close
      append-to-body
      class="admin-drawer"
    >
      <div v-loading="detailLoading" class="admin-drawer__inner">
        <template v-if="detail">
          <el-descriptions :column="1" border size="small" class="meta">
            <el-descriptions-item label="标题">{{ detail.title }}</el-descriptions-item>
            <el-descriptions-item label="用户">{{ detail.user_phone || detail.user_id }}</el-descriptions-item>
            <el-descriptions-item label="类型">{{ TYPE_MAP[detail.interaction_type] || detail.interaction_type }}</el-descriptions-item>
            <el-descriptions-item label="状态">{{ labelOf(conversationStatusLabel, detail.status) }}</el-descriptions-item>
            <el-descriptions-item label="创建时间">{{ formatTime(detail.created_at) }}</el-descriptions-item>
          </el-descriptions>

          <el-scrollbar class="admin-drawer__scroll messages">
            <el-card
              v-for="msg in detail.messages"
              :key="msg.id"
              shadow="never"
              class="msg-card"
              :class="msg.role"
            >
              <div class="msg-head">
                <el-tag size="small" :type="msg.role === 'user' ? 'primary' : 'success'">
                  {{ msg.role === 'user' ? '用户' : msg.role === 'assistant' ? 'AI' : '系统' }}
                </el-tag>
                <el-tag v-if="msg.ai_engine" size="small" type="warning" effect="plain">
                  {{ msg.ai_engine }}
                </el-tag>
                <el-text v-if="msg.tokens_used" type="info" size="small">{{ msg.tokens_used }} tokens</el-text>
                <el-text type="info" size="small">{{ formatTime(msg.created_at) }}</el-text>
              </div>
              <el-text class="msg-content">{{ msg.content }}</el-text>
            </el-card>
            <el-empty v-if="!detail.messages.length" description="暂无消息" />
          </el-scrollbar>
        </template>
      </div>
    </el-drawer>
  </div>
</template>

<style scoped>
.admin-drawer__inner {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}
.meta {
  flex-shrink: 0;
  margin-bottom: 16px;
}
.messages {
  flex: 1;
  min-height: 0;
  padding-right: 4px;
}
.msg-card {
  margin-bottom: 10px;
  border-left: 3px solid var(--el-border-color);
}
.msg-card.user { border-left-color: var(--el-color-primary); }
.msg-card.assistant { border-left-color: var(--el-color-success); }
.msg-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
}
.msg-content {
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.6;
}
</style>
