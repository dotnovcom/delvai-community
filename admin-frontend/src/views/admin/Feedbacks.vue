<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import AdminFilterBar from '../../components/admin/AdminFilterBar.vue'
import AdminTableCard from '../../components/admin/AdminTableCard.vue'
import AdminPagination from '../../components/admin/AdminPagination.vue'
import AdminIconAction from '../../components/admin/AdminIconAction.vue'
import AdminOpBtnGroup from '../../components/admin/AdminOpBtnGroup.vue'
import {
  listAdminFeedbacks, replyAdminFeedback, updateAdminFeedbackStatus, type AdminFeedback,
} from '../../api/admin'
import { labelOf, feedbackStatusLabel } from '../../utils/adminLabels'

const list = ref<AdminFeedback[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const keyword = ref('')
const statusFilter = ref('')
const loading = ref(false)
const replyVisible = ref(false)
const current = ref<AdminFeedback | null>(null)
const replyText = ref('')

async function load() {
  loading.value = true
  try {
    const res = await listAdminFeedbacks({
      page: page.value,
      size: pageSize.value,
      keyword: keyword.value || undefined,
      status: statusFilter.value || undefined,
    })
    list.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

function openReply(row: AdminFeedback) {
  current.value = row
  replyText.value = row.admin_reply || ''
  replyVisible.value = true
}

async function submitReply() {
  if (!current.value || !replyText.value.trim()) return
  await replyAdminFeedback(current.value.id, replyText.value)
  ElMessage.success('回复已发送')
  replyVisible.value = false
  await load()
}

async function closeFeedback(row: AdminFeedback) {
  await updateAdminFeedbackStatus(row.id, 'closed')
  ElMessage.success('已关闭')
  await load()
}

function formatTime(t: string) {
  return t?.slice(0, 19).replace('T', ' ')
}

onMounted(load)
</script>

<template>
  <div class="admin-page">
    <div class="admin-page-header">
      <div>
        <h2>用户反馈</h2>
        <p class="admin-page-desc">处理用户提交的意见与问题，支持回复与关闭。</p>
      </div>
    </div>
    <AdminFilterBar>
      <el-input v-model="keyword" placeholder="搜索内容/联系方式" style="width: 240px" clearable @keyup.enter="load" />
      <el-select v-model="statusFilter" placeholder="全部状态" clearable style="width: 130px" @change="load">
        <el-option label="待处理" value="pending" />
        <el-option label="已回复" value="replied" />
        <el-option label="已关闭" value="closed" />
      </el-select>
      <el-button type="primary" @click="load">搜索</el-button>
    </AdminFilterBar>

    <AdminTableCard :loading="loading">
    <el-table :data="list" class="admin-table" stripe table-layout="fixed">
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column label="用户" width="120">
        <template #default="{ row }">{{ row.user_nickname || row.user_phone || '-' }}</template>
      </el-table-column>
      <el-table-column prop="category" label="分类" width="90" />
      <el-table-column prop="content" label="反馈内容" min-width="200" show-overflow-tooltip />
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag size="small" :type="row.status === 'pending' ? 'warning' : row.status === 'replied' ? 'success' : 'info'">
            {{ labelOf(feedbackStatusLabel, row.status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="时间" width="170">
        <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" min-width="14%" align="center">
        <template #default="{ row }">
          <AdminOpBtnGroup nowrap class="admin-table-actions">
            <AdminIconAction action="reply" label="回复" @click="openReply(row)" />
            <AdminIconAction v-if="row.status !== 'closed'" action="muted" @click="closeFeedback(row)" />
          </AdminOpBtnGroup>
        </template>
      </el-table-column>
    </el-table>
      <template #footer>
        <AdminPagination v-model:page="page" v-model:page-size="pageSize" :total="total" @change="load" />
      </template>
    </AdminTableCard>

    <el-dialog
      v-model="replyVisible"
      title="回复反馈"
      width="520px"
      class="admin-dialog"
      append-to-body
      align-center
      destroy-on-close
    >
      <p v-if="current" class="feedback-content">
        <el-alert type="info" :closable="false" :title="current.content" />
      </p>
      <el-input v-model="replyText" type="textarea" :rows="5" placeholder="输入回复内容" />
      <template #footer>
        <el-button @click="replyVisible = false">取消</el-button>
        <el-button type="primary" @click="submitReply">发送回复</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.feedback-content { margin-bottom: 12px; }
</style>
