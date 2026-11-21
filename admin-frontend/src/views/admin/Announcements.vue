<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import AdminRichEditor from '../../components/admin/AdminRichEditor.vue'
import AdminFilterBar from '../../components/admin/AdminFilterBar.vue'
import AdminTableCard from '../../components/admin/AdminTableCard.vue'
import AdminPagination from '../../components/admin/AdminPagination.vue'
import AdminIconAction from '../../components/admin/AdminIconAction.vue'
import AdminOpBtnGroup from '../../components/admin/AdminOpBtnGroup.vue'
import { useAdminBatchDelete } from '../../composables/useAdminBatchDelete'
import { createContent, deleteContent, listContent, updateContent, type ContentArticle } from '../../api/admin'
import { contentStatusLabel, labelOf } from '../../utils/adminLabels'

const list = ref<ContentArticle[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loading = ref(false)
const selected = ref<ContentArticle[]>([])
const dialogVisible = ref(false)
const editing = ref<ContentArticle | null>(null)
const form = ref({ title: '', summary: '', content: '', status: 'draft' })

const { deleting, confirmBatchDelete } = useAdminBatchDelete(selected, deleteContent, {
  label: '条公告',
  onDone: load,
})

async function load() {
  loading.value = true
  try {
    const res = await listContent(page.value, pageSize.value, undefined, 'announcement')
    list.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

function onSelectionChange(rows: ContentArticle[]) {
  selected.value = rows
}

function openCreate() {
  editing.value = null
  form.value = { title: '', summary: '', content: '', status: 'draft' }
  dialogVisible.value = true
}

function openEdit(row: ContentArticle) {
  editing.value = row
  form.value = {
    title: row.title,
    summary: row.summary || '',
    content: row.content,
    status: row.status,
  }
  dialogVisible.value = true
}

async function save() {
  if (!form.value.title || !form.value.content) {
    ElMessage.warning('请填写标题和正文')
    return
  }
  const payload = { ...form.value, category: 'announcement' as const }
  if (editing.value) {
    await updateContent(editing.value.id, payload)
  } else {
    await createContent(payload)
  }
  ElMessage.success('已保存')
  dialogVisible.value = false
  await load()
}

async function remove(row: ContentArticle) {
  await ElMessageBox.confirm('确定删除该公告？', '确认', { type: 'warning' })
  await deleteContent(row.id)
  ElMessage.success('已删除')
  await load()
}

onMounted(load)
</script>

<template>
  <div class="admin-page">
    <div class="admin-page-header">
      <div>
        <h2>平台公告</h2>
        <p class="admin-page-desc">支持多条公告发布，前台以滚动条与列表形式展示。</p>
      </div>
      <div class="admin-page-header__actions">
        <el-button type="primary" @click="openCreate">新建公告</el-button>
      </div>
    </div>

    <AdminFilterBar
      :selected-count="selected.length"
      batch-deletable
      :batch-loading="deleting"
      @batch-delete="confirmBatchDelete"
    />

    <AdminTableCard :loading="loading">
      <el-table :data="list" class="admin-table" stripe table-layout="fixed" @selection-change="onSelectionChange">
        <el-table-column type="selection" width="48" align="center" />
        <el-table-column prop="title" label="标题" min-width="28%" show-overflow-tooltip />
        <el-table-column prop="summary" label="摘要" min-width="32%" show-overflow-tooltip />
        <el-table-column label="状态" min-width="12%" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === 'published' ? 'success' : 'info'" size="small">
              {{ labelOf(contentStatusLabel, row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="updated_at" label="更新时间" min-width="16%">
          <template #default="{ row }">{{ row.updated_at?.slice(0, 19).replace('T', ' ') }}</template>
        </el-table-column>
        <el-table-column label="操作" min-width="14%" align="center" fixed="right">
          <template #default="{ row }">
            <AdminOpBtnGroup nowrap class="admin-table-actions">
              <AdminIconAction action="edit" @click="openEdit(row)" />
              <AdminIconAction action="delete" @click="remove(row)" />
            </AdminOpBtnGroup>
          </template>
        </el-table-column>
      </el-table>
      <template #footer>
        <AdminPagination v-model:page="page" v-model:page-size="pageSize" :total="total" @change="load" />
      </template>
    </AdminTableCard>

    <el-dialog
      v-model="dialogVisible"
      :title="editing ? '编辑公告' : '新建公告'"
      width="760px"
      class="admin-dialog"
      append-to-body
      align-center
      destroy-on-close
    >
      <el-form label-width="80px">
        <el-form-item label="标题" required><el-input v-model="form.title" /></el-form-item>
        <el-form-item label="摘要"><el-input v-model="form.summary" type="textarea" :rows="2" placeholder="用于列表与滚动条展示" /></el-form-item>
        <el-form-item label="状态">
          <el-select v-model="form.status" style="width: 100%">
            <el-option label="草稿" value="draft" />
            <el-option label="已发布" value="published" />
          </el-select>
        </el-form-item>
        <el-form-item label="正文" required>
          <AdminRichEditor v-model="form.content" placeholder="编辑公告正文…" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>
