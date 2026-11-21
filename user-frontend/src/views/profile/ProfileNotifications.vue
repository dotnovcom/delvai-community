<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  listNotifications,
  markAllNotificationsRead,
  markNotificationRead,
  type UserNotification,
} from '../../api/auth'

const loading = ref(false)
const items = ref<UserNotification[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const unreadOnly = ref(false)
const detailVisible = ref(false)
const current = ref<UserNotification | null>(null)

const CATEGORY_MAP: Record<string, string> = {
  system: '系统通知',
  legal_news: '法律资讯',
  order: '订单/支付',
  contract_expiry: '合同提醒',
  billing: '账户/计费',
  enterprise_contract: '企业·合同',
  enterprise_approval: '企业·审批',
  enterprise_compliance: '企业·合规',
  enterprise_receivable: '企业·账款',
}

function formatTime(t?: string | null) {
  return t?.slice(0, 19).replace('T', ' ') || '—'
}

function categoryLabel(category: string) {
  return CATEGORY_MAP[category] || category || '通知'
}

async function load() {
  loading.value = true
  try {
    const res = await listNotifications({
      page: page.value,
      size: pageSize.value,
      unread_only: unreadOnly.value,
    })
    items.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

async function openDetail(row: UserNotification) {
  current.value = row
  detailVisible.value = true
  if (!row.read_at) {
    try {
      await markNotificationRead(row.id)
      row.read_at = new Date().toISOString()
      window.dispatchEvent(new CustomEvent('notifications-updated'))
    } catch {
      /* ignore */
    }
  }
}

async function handleMarkAllRead() {
  const res = await markAllNotificationsRead()
  ElMessage.success(`已标记 ${res.count} 条为已读`)
  window.dispatchEvent(new CustomEvent('notifications-updated'))
  await load()
}

function onFilterChange() {
  page.value = 1
  load()
}

onMounted(load)
</script>

<template>
  <div v-loading="loading" class="profile-page">
    <div class="pc-card notifications-card">
      <div class="header-row">
        <div>
          <h2>站内信</h2>
          <p class="page-desc">查看平台发送的系统通知、订单提醒与运营消息</p>
        </div>
        <div class="header-actions">
          <el-checkbox v-model="unreadOnly" @change="onFilterChange">仅看未读</el-checkbox>
          <el-button type="primary" plain @click="handleMarkAllRead">全部已读</el-button>
        </div>
      </div>

      <el-empty v-if="!loading && !items.length" description="暂无站内信" />

      <div v-else class="notice-list">
        <button
          v-for="item in items"
          :key="item.id"
          type="button"
          class="notice-item"
          :class="{ unread: !item.read_at }"
          @click="openDetail(item)"
        >
          <div class="notice-head">
            <span class="notice-title">{{ item.title }}</span>
            <el-tag size="small" type="info">{{ categoryLabel(item.category) }}</el-tag>
          </div>
          <p class="notice-preview">{{ item.content }}</p>
          <div class="notice-meta">
            <span>{{ formatTime(item.created_at) }}</span>
            <span v-if="!item.read_at" class="unread-dot">未读</span>
          </div>
        </button>
      </div>

      <div v-if="total > pageSize" class="pager-wrap">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          layout="total, prev, pager, next"
          @current-change="load"
          @size-change="onFilterChange"
        />
      </div>
    </div>

    <el-dialog v-model="detailVisible" :title="current?.title || '消息详情'" width="520px" append-to-body>
      <div v-if="current" class="notice-detail">
        <div class="detail-meta">
          <el-tag size="small">{{ categoryLabel(current.category) }}</el-tag>
          <span>{{ formatTime(current.created_at) }}</span>
        </div>
        <div class="detail-content">{{ current.content }}</div>
      </div>
    </el-dialog>
  </div>
</template>

<style scoped>
.pc-card {
  padding: 24px;
  background: #fff;
  border: 1px solid #e8e8e8;
  border-radius: 24px;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
}

.header-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 20px;
}

.header-row h2 {
  margin: 0 0 6px;
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
}

.page-desc {
  margin: 0;
  color: #6b7280;
  font-size: 13px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}

.notice-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.notice-item {
  width: 100%;
  text-align: left;
  border: 1px solid #e8e8e8;
  background: #fff;
  border-radius: 16px;
  padding: 14px 16px;
  cursor: pointer;
}

.notice-item:hover {
  border-color: #6ee7b7;
  box-shadow: 0 4px 14px rgba(16, 185, 129, 0.08);
}

.notice-item.unread {
  border-left: 3px solid #10b981;
  background: #ecfdf5;
}

.notice-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
}

.notice-title {
  font-size: 15px;
  font-weight: 600;
  color: #1f2937;
}

.notice-preview {
  margin: 0 0 10px;
  font-size: 13px;
  color: #6b7280;
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.notice-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 12px;
  color: #9ca3af;
}

.unread-dot {
  color: #10b981;
}

.pager-wrap {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.detail-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  font-size: 13px;
  color: #6b7280;
}

.detail-content {
  white-space: pre-wrap;
  line-height: 1.8;
  font-size: 14px;
  color: #1f2937;
}
</style>
