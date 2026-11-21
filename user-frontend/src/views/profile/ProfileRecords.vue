<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  listMyDocuments,
  getMyDocument,
  updateMyDocument,
  deleteMyDocument,
  listMyContractReviews,
  getMyContractReview,
  listMyContractExtracts,
  getMyContractExtract,
  listMySearchHistory,
  getMySearchHistory,
  listMyAnalysisReports,
  getMyAnalysisReport,
  listMyDocumentReads,
  getMyDocumentRead,
  deleteMyDocumentRead,
  type MyDocumentDetail,
  type MyDocumentReadDetail,
  type ContractReviewDetail,
  type MyContractExtractDetail,
  type MySearchHistoryDetail,
  type MyAnalysisReportDetail,
} from '../../api/userRecords'
import {
  resolveDocumentTitle,
  documentPreviewHtml,
  downloadDocumentWord,
  downloadDocumentTxt,
  printDocumentPreview,
  documentPlainPreview,
  stripLeadingDocumentTitle,
  contractReviewToMarkdown,
  contractExtractToMarkdown,
  searchHistoryToMarkdown,
  analysisReportToMarkdown,
} from '../../utils/legalRecordExport'
import DocumentRichEditor from '../../components/legal/DocumentRichEditor.vue'
import { View, Edit, Document, Printer, Delete } from '@element-plus/icons-vue'
import { formatLegalSearchText } from '../../utils/legalChatContent'
import { sanitizeUserBrandText } from '../../utils/contractRevision'
import FaIcon from '../../components/FaIcon.vue'
import { getMessages, listConversations, type ChatMessage } from '../../api/chat'

type TabKey = 'consult' | 'documents' | 'reviews' | 'extracts' | 'read' | 'search' | 'analysis'

const route = useRoute()
const router = useRouter()

const activeTab = ref<TabKey>('consult')
const loading = ref(false)
const page = ref(1)
const pageSize = ref(15)
const total = ref(0)
const rows = ref<Record<string, unknown>[]>([])

const drawerVisible = ref(false)
const drawerLoading = ref(false)
const drawerTitle = ref('')
const drawerKind = ref<'consult' | 'document' | 'review' | 'extract' | 'read' | 'search' | 'analysis'>('consult')
const consultMessages = ref<ChatMessage[]>([])
const drawerDocMode = ref<'view' | 'edit'>('view')

const docDetail = ref<MyDocumentDetail | null>(null)
const editDocTitle = ref('')
const editDocContent = ref('')
const saveDocLoading = ref(false)
const docEditorRef = ref<InstanceType<typeof DocumentRichEditor> | null>(null)
const reviewDetail = ref<ContractReviewDetail | null>(null)
const extractDetail = ref<MyContractExtractDetail | null>(null)
const searchDetail = ref<MySearchHistoryDetail | null>(null)
const analysisDetail = ref<MyAnalysisReportDetail | null>(null)
const readDetail = ref<MyDocumentReadDetail | null>(null)

const analysisHtml = computed(() => {
  if (!analysisDetail.value) return ''
  const raw = analysisDetail.value.content?.trim()
  if (raw) return documentPreviewHtml(raw)
  const cases = analysisDetail.value.related_cases || []
  if (cases.length) {
    const md = cases
      .map((c) => {
        const row = c as { title?: string; case_no?: string; summary?: string }
        return `- **${row.title || '案例'}**（${row.case_no || '—'}）：${row.summary || '暂无摘要'}`
      })
      .join('\n')
    return documentPreviewHtml(`## 相关类案摘要\n\n${md}`, '类案分析')
  }
  return '<p class="record-empty-body">暂无分析正文，请在「文本分析」工作台重新生成报告。</p>'
})

const canEditInWorkspace = computed(() =>
  ['review', 'extract', 'read', 'search', 'analysis'].includes(drawerKind.value),
)

const readPreviewHtml = computed(() => {
  if (!readDetail.value) return ''
  const html = (readDetail.value.contract_html || '').trim()
  if (html) return documentPreviewHtml(html)
  return documentPreviewHtml(readDetail.value.contract_text || '', readDetail.value.file_name)
})

const searchSummaryText = computed(() =>
  searchDetail.value?.ai_summary ? formatLegalSearchText(searchDetail.value.ai_summary) : '',
)

function searchHitSnippet(snippet?: string) {
  return formatLegalSearchText(snippet || '')
}

function syncDocEditor() {
  if (!docDetail.value) return
  const displayTitle = resolveDocumentTitle(
    docDetail.value.title,
    docDetail.value.doc_type,
    docDetail.value.content,
  )
  editDocTitle.value = displayTitle
  editDocContent.value = stripLeadingDocumentTitle(
    docDetail.value.content,
    displayTitle,
    docDetail.value.doc_type,
  )
}

const TAB_META: { key: TabKey; label: string; icon: string }[] = [
  { key: 'consult', label: '法律咨询', icon: 'comments' },
  { key: 'documents', label: '我的文书', icon: 'file-lines' },
  { key: 'reviews', label: '合同审查', icon: 'clipboard' },
  { key: 'extracts', label: '合同抽取', icon: 'layer-group' },
  { key: 'read', label: '文本阅读', icon: 'book-open' },
  { key: 'search', label: '检索记录', icon: 'magnifying-glass' },
  { key: 'analysis', label: '类案分析', icon: 'chart-column' },
]

function formatTime(iso: string) {
  if (!iso) return '—'
  const d = new Date(iso)
  return d.toLocaleString('zh-CN', { hour12: false })
}

function syncTabFromRoute() {
  const t = String(route.query.tab || 'consult')
  if (['consult', 'documents', 'reviews', 'extracts', 'read', 'search', 'analysis'].includes(t)) {
    activeTab.value = t as TabKey
  }
}

async function loadList() {
  loading.value = true
  try {
    let res
    if (activeTab.value === 'consult') {
      const items = await listConversations((page.value - 1) * pageSize.value, pageSize.value, 'text')
      rows.value = items as unknown as Record<string, unknown>[]
      total.value = items.length < pageSize.value
        ? (page.value - 1) * pageSize.value + items.length
        : page.value * pageSize.value + 1
      await tryOpenFromQuery()
      return
    } else if (activeTab.value === 'documents') {
      res = await listMyDocuments({ page: page.value, size: pageSize.value })
    } else if (activeTab.value === 'reviews') {
      res = await listMyContractReviews({ page: page.value, size: pageSize.value })
    } else if (activeTab.value === 'extracts') {
      res = await listMyContractExtracts({ page: page.value, size: pageSize.value })
    } else if (activeTab.value === 'read') {
      res = await listMyDocumentReads({ page: page.value, size: pageSize.value })
    } else if (activeTab.value === 'search') {
      res = await listMySearchHistory({ page: page.value, size: pageSize.value })
    } else {
      res = await listMyAnalysisReports({ page: page.value, size: pageSize.value })
    }
    rows.value = res.items as unknown as Record<string, unknown>[]
    total.value = res.total
    await tryOpenFromQuery()
  } catch {
    rows.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

async function tryOpenFromQuery() {
  const openId = route.query.open
  if (!openId || drawerVisible.value) return
  const id = Number(openId)
  if (!id) return
  const row = rows.value.find((r) => Number(r.id) === id)
  if (row) await openDetail(row)
  else await openDetail({ id })
}

function onTabChange(key: TabKey) {
  activeTab.value = key
  page.value = 1
  router.replace({ query: { tab: key } })
  loadList()
}

async function openDetail(row: Record<string, unknown>, mode: 'view' | 'edit' = 'view') {
  const id = Number(row.id)
  drawerVisible.value = true
  drawerLoading.value = true
  drawerDocMode.value = mode
  docDetail.value = null
  consultMessages.value = []
  reviewDetail.value = null
  extractDetail.value = null
  searchDetail.value = null
  analysisDetail.value = null
  readDetail.value = null
  try {
    if (activeTab.value === 'consult') {
      drawerKind.value = 'consult'
      consultMessages.value = await getMessages(id)
      const title = String(row.title || '法律咨询')
      drawerTitle.value = title
    } else if (activeTab.value === 'documents') {
      drawerKind.value = 'document'
      docDetail.value = await getMyDocument(id)
      drawerTitle.value = resolveDocumentTitle(
        docDetail.value.title,
        docDetail.value.doc_type,
        docDetail.value.content,
      )
      syncDocEditor()
    } else if (activeTab.value === 'reviews') {
      drawerKind.value = 'review'
      reviewDetail.value = await getMyContractReview(id)
      drawerTitle.value = `审查 · ${reviewDetail.value.file_name}`
    } else if (activeTab.value === 'extracts') {
      drawerKind.value = 'extract'
      extractDetail.value = await getMyContractExtract(id)
      drawerTitle.value = `抽取 · ${extractDetail.value.file_name}`
    } else if (activeTab.value === 'read') {
      drawerKind.value = 'read'
      readDetail.value = await getMyDocumentRead(id)
      drawerTitle.value = `文本阅读 · ${readDetail.value.file_name}`
    } else if (activeTab.value === 'search') {
      drawerKind.value = 'search'
      searchDetail.value = await getMySearchHistory(id)
      drawerTitle.value = `${searchDetail.value.kind_label} · ${searchDetail.value.query}`
    } else {
      drawerKind.value = 'analysis'
      analysisDetail.value = await getMyAnalysisReport(id)
      drawerTitle.value = `类案分析 · ${(analysisDetail.value.case_description || '').slice(0, 24)}`
    }
  } catch {
    ElMessage.error('加载详情失败')
    drawerVisible.value = false
  } finally {
    drawerLoading.value = false
  }
}

function exportCurrent(fmt: 'word' | 'txt' | 'print') {
  let title = drawerTitle.value
  let md = ''
  if (drawerKind.value === 'document' && docDetail.value) {
    md = (docEditorRef.value?.getHtml() ?? editDocContent.value) || docDetail.value.content
    title = resolveDocumentTitle(
      editDocTitle.value || docDetail.value.title,
      docDetail.value.doc_type,
      md,
    )
    const docType = docDetail.value.doc_type
    if (fmt === 'word') {
      if (!downloadDocumentWord(title, md, docType)) ElMessage.warning('导出失败')
      else ElMessage.success('已下载 Word')
      return
    }
    if (fmt === 'txt') {
      downloadDocumentTxt(title, md, docType)
      ElMessage.success('已下载 TXT')
      return
    }
    if (!printDocumentPreview(title, md, docType)) {
      ElMessage.warning('无法打开打印窗口')
    }
    return
  } else if (drawerKind.value === 'review' && reviewDetail.value) {
    md = contractReviewToMarkdown(
      reviewDetail.value.file_name,
      reviewDetail.value.summary,
      reviewDetail.value.annotations,
    )
  } else if (drawerKind.value === 'extract' && extractDetail.value) {
    md = contractExtractToMarkdown(
      extractDetail.value.file_name,
      extractDetail.value.extract_result,
    )
  } else if (drawerKind.value === 'search' && searchDetail.value) {
    md = searchHistoryToMarkdown(
      searchDetail.value.kind_label,
      searchDetail.value.query,
      searchSummaryText.value,
      searchDetail.value.result_preview.map((hit) => ({
        title: hit.title,
        snippet: searchHitSnippet(hit.snippet),
      })),
    )
  } else if (drawerKind.value === 'read' && readDetail.value) {
    md = readDetail.value.contract_text || ''
    title = readDetail.value.file_name
  } else if (drawerKind.value === 'analysis' && analysisDetail.value) {
    md = analysisReportToMarkdown(
      analysisDetail.value.case_description,
      analysisDetail.value.content,
      analysisDetail.value.related_cases as { title?: string; case_no?: string; summary?: string }[],
    )
  } else if (drawerKind.value === 'consult' && consultMessages.value.length) {
    md = consultMessages.value
      .map((item) => `**${item.role === 'user' ? '我' : '助手'}**\n\n${item.content || ''}`)
      .join('\n\n')
  }
  if (!md.trim()) {
    ElMessage.warning('暂无内容可导出')
    return
  }
  if (fmt === 'word') {
    if (!downloadDocumentWord(title, md)) ElMessage.warning('导出失败')
    else ElMessage.success('已下载 Word')
  } else if (fmt === 'txt') {
    downloadDocumentTxt(title, md)
    ElMessage.success('已下载 TXT')
  } else if (!printDocumentPreview(title, md)) {
    ElMessage.warning('无法打开打印窗口')
  }
}

async function saveDocumentRecord() {
  if (!docDetail.value?.id) return
  saveDocLoading.value = true
  try {
    const content = docEditorRef.value?.getHtml() ?? editDocContent.value
    docDetail.value = await updateMyDocument(docDetail.value.id, {
      title: editDocTitle.value.trim(),
      content,
    })
    drawerTitle.value = resolveDocumentTitle(
      docDetail.value.title,
      docDetail.value.doc_type,
      docDetail.value.content,
    )
    syncDocEditor()
    docEditorRef.value?.setHtml(editDocContent.value, true)
    ElMessage.success('文书已保存')
    await loadList()
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : '保存失败')
  } finally {
    saveDocLoading.value = false
  }
}

function docPreviewText(row: Record<string, unknown>) {
  return documentPlainPreview(String(row.content_preview || ''))
}

async function quickExportDoc(row: Record<string, unknown>, fmt: 'word' | 'print') {
  try {
    const doc = await getMyDocument(Number(row.id))
    const title = resolveDocumentTitle(doc.title, doc.doc_type, doc.content)
    if (fmt === 'word') {
      if (!downloadDocumentWord(title, doc.content, doc.doc_type)) ElMessage.warning('导出失败')
      else ElMessage.success('已下载 Word')
    } else if (!printDocumentPreview(title, doc.content, doc.doc_type)) {
      ElMessage.warning('无法打开打印窗口')
    }
  } catch {
    ElMessage.error('操作失败')
  }
}

async function confirmDeleteDoc(row: Record<string, unknown>, e: Event) {
  e.stopPropagation()
  try {
    await ElMessageBox.confirm('确定删除该文书记录？删除后不可恢复。', '删除文书', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
    await deleteMyDocument(Number(row.id))
    ElMessage.success('已删除')
    if (docDetail.value?.id === Number(row.id)) drawerVisible.value = false
    await loadList()
  } catch {
    /* cancelled */
  }
}

function goWorkspace(tab: TabKey) {
  const map: Record<TabKey, string> = {
    consult: '/chat/ai',
    documents: '/chat/document',
    reviews: '/chat/contract',
    extracts: '/chat/contract?tab=extract',
    read: '/chat/read',
    search: '/chat/search',
    analysis: '/chat/analysis',
  }
  router.push(map[tab])
}

async function confirmDeleteRead(row: Record<string, unknown>, e: Event) {
  e.stopPropagation()
  try {
    await ElMessageBox.confirm('确定删除该文本阅读记录？删除后不可恢复。', '删除记录', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
    await deleteMyDocumentRead(Number(row.id))
    ElMessage.success('已删除')
    if (readDetail.value?.id === Number(row.id)) drawerVisible.value = false
    await loadList()
  } catch {
    /* cancelled */
  }
}

function editRecordInWorkspaceFromRow(row: Record<string, unknown>) {
  router.push({ path: '/chat/read', query: { open: String(row.id) } })
}

function continueConsult() {
  const id = Number(rows.value.find((row) => drawerTitle.value && row.title === drawerTitle.value)?.id || 0)
  const current = consultMessages.value[0]?.conversation_id
  drawerVisible.value = false
  router.push({ path: '/chat/ai', query: current ? { cid: String(current) } : id ? { cid: String(id) } : {} })
}

function editRecordInWorkspace() {
  drawerVisible.value = false
  if (drawerKind.value === 'review' && reviewDetail.value) {
    router.push({ path: '/chat/contract', query: { open: String(reviewDetail.value.id) } })
    return
  }
  if (drawerKind.value === 'extract' && extractDetail.value) {
    router.push({
      path: '/chat/contract',
      query: { tab: 'extract', open: String(extractDetail.value.id) },
    })
    return
  }
  if (drawerKind.value === 'read' && readDetail.value) {
    router.push({ path: '/chat/read', query: { open: String(readDetail.value.id) } })
    return
  }
  if (drawerKind.value === 'search' && searchDetail.value) {
    router.push({ path: '/chat/search', query: { open: String(searchDetail.value.id) } })
    return
  }
  if (drawerKind.value === 'analysis' && analysisDetail.value) {
    router.push({ path: '/chat/analysis', query: { open: String(analysisDetail.value.id) } })
  }
}

watch(
  () => route.query.tab,
  () => {
    syncTabFromRoute()
    page.value = 1
    loadList()
  },
  { immediate: true },
)

watch(
  () => route.query.open,
  () => {
    if (route.name === 'ProfileRecords' && !loading.value) void tryOpenFromQuery()
  },
)
</script>

<template>
  <div class="profile-page profile-records">
    <header class="profile-records__head">
      <div>
        <h1 class="profile-page-title">我的记录</h1>
        <p class="profile-records__sub">法律咨询、文书、合同、文本阅读、检索与类案分析报告将自动保存，可随时查看、导出与继续编辑</p>
      </div>
    </header>

    <nav class="pc-tabs" aria-label="记录类型">
      <button
        v-for="t in TAB_META"
        :key="t.key"
        type="button"
        class="pc-tabs__item"
        :class="{ active: activeTab === t.key }"
        @click="onTabChange(t.key)"
      >
        <FaIcon class="tab-icon" :name="t.icon" />{{ t.label }}
      </button>
    </nav>

    <div v-loading="loading" class="profile-records__card">
      <div v-if="!loading && rows.length === 0" class="profile-records__empty">
        <p>暂无{{ TAB_META.find((t) => t.key === activeTab)?.label }}记录</p>
        <el-button type="primary" @click="goWorkspace(activeTab)">去使用</el-button>
      </div>

      <template v-else-if="activeTab === 'consult'">
        <div
          v-for="row in rows"
          :key="String(row.id)"
          class="record-row"
          @click="openDetail(row)"
        >
          <div class="record-row__main">
            <span class="record-tag">咨询</span>
            <strong class="record-title">{{ row.title || '法律咨询' }}</strong>
            <p class="record-preview">{{ row.last_message || '点击查看完整对话' }}</p>
            <time class="record-time record-time--inline">{{ formatTime(String(row.updated_at || row.created_at || '')) }}</time>
          </div>
        </div>
      </template>

      <template v-else-if="activeTab === 'documents'">
        <div
          v-for="row in rows"
          :key="String(row.id)"
          class="record-row record-row--with-ops"
        >
          <div class="record-row__main">
            <span class="record-tag">{{ row.doc_type }}</span>
            <strong class="record-title">{{ row.title }}</strong>
            <p class="record-preview">{{ docPreviewText(row) }}</p>
            <time class="record-time record-time--inline">{{ formatTime(String(row.created_at)) }}</time>
          </div>
          <div class="record-row__ops" @click.stop>
            <button type="button" class="rec-op rec-op--view" @click="openDetail(row, 'view')">
              <el-icon class="rec-op__icon"><View /></el-icon>
              查看
            </button>
            <button type="button" class="rec-op rec-op--edit" @click="openDetail(row, 'edit')">
              <el-icon class="rec-op__icon"><Edit /></el-icon>
              编辑
            </button>
            <button type="button" class="rec-op rec-op--word" @click="quickExportDoc(row, 'word')">
              <el-icon class="rec-op__icon"><Document /></el-icon>
              导出WORD
            </button>
            <button type="button" class="rec-op rec-op--print" @click="quickExportDoc(row, 'print')">
              <el-icon class="rec-op__icon"><Printer /></el-icon>
              打印
            </button>
            <button type="button" class="rec-op rec-op--del" @click="confirmDeleteDoc(row, $event)">
              <el-icon class="rec-op__icon"><Delete /></el-icon>
              删除
            </button>
          </div>
        </div>
      </template>

      <template v-else-if="activeTab === 'reviews'">
        <div
          v-for="row in rows"
          :key="String(row.id)"
          class="record-row"
          @click="openDetail(row)"
        >
          <div class="record-row__main">
            <strong class="record-title">{{ row.file_name }}</strong>
            <p class="record-preview">{{ sanitizeUserBrandText(String(row.summary_preview || '')) || '点击查看完整审查报告' }}</p>
            <div class="record-badges">
              <span v-if="row.risk_high" class="risk risk--high">高 {{ row.risk_high }}</span>
              <span v-if="row.risk_medium" class="risk risk--med">中 {{ row.risk_medium }}</span>
              <span v-if="row.risk_low" class="risk risk--low">低 {{ row.risk_low }}</span>
            </div>
          </div>
          <time class="record-time">{{ formatTime(String(row.created_at)) }}</time>
        </div>
      </template>

      <template v-else-if="activeTab === 'extracts'">
        <div
          v-for="row in rows"
          :key="String(row.id)"
          class="record-row"
          @click="openDetail(row)"
        >
          <div class="record-row__main">
            <strong class="record-title">{{ row.file_name }}</strong>
            <p class="record-preview">已抽取 {{ row.field_count }} 个字段</p>
          </div>
          <time class="record-time">{{ formatTime(String(row.created_at)) }}</time>
        </div>
      </template>

      <template v-else-if="activeTab === 'read'">
        <div
          v-for="row in rows"
          :key="String(row.id)"
          class="record-row record-row--with-ops"
        >
          <div class="record-row__main" @click="openDetail(row)">
            <span class="record-tag record-tag--read">文本阅读</span>
            <strong class="record-title">{{ row.file_name }}</strong>
            <p class="record-preview">{{ row.text_preview || '点击查看文档正文与阅读笔记' }}</p>
            <time class="record-time record-time--inline">{{ formatTime(String(row.created_at)) }}</time>
          </div>
          <div class="record-row__ops" @click.stop>
            <button type="button" class="rec-op rec-op--view" @click="openDetail(row, 'view')">
              <el-icon class="rec-op__icon"><View /></el-icon>
              查看
            </button>
            <button type="button" class="rec-op rec-op--edit" @click="editRecordInWorkspaceFromRow(row)">
              <el-icon class="rec-op__icon"><Edit /></el-icon>
              编辑
            </button>
            <button type="button" class="rec-op rec-op--del" @click="confirmDeleteRead(row, $event)">
              <el-icon class="rec-op__icon"><Delete /></el-icon>
              删除
            </button>
          </div>
        </div>
      </template>

      <template v-else-if="activeTab === 'search'">
        <div
          v-for="row in rows"
          :key="String(row.id)"
          class="record-row"
          @click="openDetail(row)"
        >
          <div class="record-row__main">
            <span class="record-tag record-tag--search">{{ row.kind_label }}</span>
            <strong class="record-title">{{ row.query }}</strong>
            <p class="record-preview">
              共 {{ row.total }} 条
              <template v-if="row.ai_summary_preview"> · {{ row.ai_summary_preview }}</template>
            </p>
          </div>
          <time class="record-time">{{ formatTime(String(row.created_at)) }}</time>
        </div>
      </template>

      <template v-else-if="activeTab === 'analysis'">
        <div
          v-for="row in rows"
          :key="String(row.id)"
          class="record-row"
          @click="openDetail(row)"
        >
          <div class="record-row__main">
            <span class="record-tag record-tag--analysis">类案分析</span>
            <strong class="record-title">{{ row.case_description_preview }}</strong>
            <p class="record-preview">{{ row.content_preview }}</p>
          </div>
          <time class="record-time">{{ formatTime(String(row.created_at)) }}</time>
        </div>
      </template>

      <div v-if="total > pageSize" class="profile-records__pager">
        <el-pagination
          v-model:current-page="page"
          :page-size="pageSize"
          :total="total"
          layout="prev, pager, next"
          @current-change="loadList"
        />
      </div>
    </div>

    <el-drawer
      v-model="drawerVisible"
      :title="drawerTitle"
      size="50%"
      direction="rtl"
      destroy-on-close
      class="record-detail-drawer"
    >
      <div v-loading="drawerLoading" class="record-drawer-body">
        <div class="record-drawer-actions">
          <el-button
            v-if="drawerKind === 'consult'"
            type="primary"
            plain
            @click="continueConsult"
          >
            继续咨询
          </el-button>
          <el-button
            v-if="canEditInWorkspace"
            type="primary"
            plain
            @click="editRecordInWorkspace"
          >
            编辑
          </el-button>
          <el-button
            v-if="drawerKind === 'document' && docDetail && drawerDocMode === 'edit'"
            type="primary"
            :loading="saveDocLoading"
            @click="saveDocumentRecord"
          >
            保存文书
          </el-button>
          <el-button v-if="drawerKind === 'document' && docDetail && drawerDocMode === 'view'" @click="drawerDocMode = 'edit'">
            进入编辑
          </el-button>
          <el-button type="primary" @click="exportCurrent('word')">导出 Word</el-button>
          <el-button @click="exportCurrent('txt')">导出 TXT</el-button>
          <el-button @click="exportCurrent('print')">打印</el-button>
        </div>

        <article v-if="drawerKind === 'consult'" class="record-consult">
          <div v-for="item in consultMessages" :key="item.id" class="consult-bubble" :class="`consult-bubble--${item.role}`">
            <span class="consult-bubble__role">{{ item.role === 'user' ? '我' : '助手' }}</span>
            <p>{{ item.content }}</p>
          </div>
          <p v-if="!consultMessages.length" class="record-empty-body">这场咨询还没有消息。</p>
        </article>

        <article v-else-if="drawerKind === 'document' && docDetail" class="record-doc-preview">
          <p class="record-doc-meta">
            <span>{{ docDetail.doc_type }}</span>
            <time>{{ formatTime(docDetail.created_at) }}</time>
          </p>
          <DocumentRichEditor
            ref="docEditorRef"
            v-model="editDocContent"
            v-model:title="editDocTitle"
            :doc-type="docDetail.doc_type"
            :readonly="drawerDocMode === 'view'"
            min-height="480px"
          />
        </article>

        <article v-else-if="drawerKind === 'review' && reviewDetail" class="record-review">
          <p class="record-review-summary">{{ sanitizeUserBrandText(reviewDetail.summary) }}</p>
          <div class="record-review-stats">
            <span class="risk risk--high">高风险 {{ reviewDetail.risk_count?.high ?? 0 }}</span>
            <span class="risk risk--med">中风险 {{ reviewDetail.risk_count?.medium ?? 0 }}</span>
            <span class="risk risk--low">低风险 {{ reviewDetail.risk_count?.low ?? 0 }}</span>
          </div>
          <ul class="record-annotation-list">
            <li v-for="a in reviewDetail.annotations" :key="a.id" class="annotation-card">
              <div class="annotation-card__head">
                <span class="risk" :class="`risk--${a.risk_level}`">{{
                  { high: '高', medium: '中', low: '低' }[a.risk_level] || a.risk_level
                }}</span>
                <span>{{ a.category }}</span>
              </div>
              <p class="annotation-quote">{{ a.text }}</p>
              <p class="annotation-suggest"><strong>建议：</strong>{{ a.suggestion }}</p>
            </li>
          </ul>
        </article>

        <article v-else-if="drawerKind === 'extract' && extractDetail" class="record-extract">
          <el-table :data="extractDetail.extract_result" stripe border size="small">
            <el-table-column label="字段" min-width="120">
              <template #default="{ row }">
                {{ row.extractItem || row.extract_item }}
              </template>
            </el-table-column>
            <el-table-column label="抽取值" min-width="200">
              <template #default="{ row }">
                {{
                  (row.value || [])
                    .map((v: { data?: string }) => v?.data)
                    .filter(Boolean)
                    .join('；') || '—'
                }}
              </template>
            </el-table-column>
          </el-table>
        </article>

        <article v-else-if="drawerKind === 'read' && readDetail" class="record-read">
          <p class="record-doc-meta">
            <span>文本阅读</span>
            <time>{{ formatTime(readDetail.created_at) }}</time>
          </p>
          <div class="doc-preview-markdown record-read__body" v-html="readPreviewHtml" />
          <section v-if="readDetail.notes_html" class="record-read__notes">
            <h4>阅读笔记</h4>
            <div class="doc-preview-markdown" v-html="documentPreviewHtml(readDetail.notes_html)" />
          </section>
        </article>

        <article v-else-if="drawerKind === 'search' && searchDetail" class="record-search">
          <p v-if="searchSummaryText" class="record-search-summary">
            {{ searchSummaryText }}
          </p>
          <ul class="record-search-hits">
            <li v-for="(hit, i) in searchDetail.result_preview" :key="i">
              <strong>{{ hit.title || `条目 ${i + 1}` }}</strong>
              <p>{{ searchHitSnippet(hit.snippet) }}</p>
            </li>
          </ul>
        </article>

        <article v-else-if="drawerKind === 'analysis' && analysisDetail" class="record-analysis">
          <section class="record-analysis__case">
            <h4>案情描述</h4>
            <p>{{ analysisDetail.case_description }}</p>
          </section>
          <section class="record-analysis__body">
            <h4>分析内容</h4>
            <div class="doc-preview-markdown" v-html="analysisHtml" />
          </section>
          <section
            v-if="analysisDetail.related_cases?.length"
            class="record-analysis__cases"
          >
            <h4>相关案例（{{ analysisDetail.related_cases.length }}）</h4>
            <ul>
              <li v-for="(c, i) in analysisDetail.related_cases" :key="i">
                <strong>{{ (c as { title?: string }).title || `案例 ${i + 1}` }}</strong>
                <p v-if="(c as { case_no?: string }).case_no">案号：{{ (c as { case_no?: string }).case_no }}</p>
                <p v-if="(c as { summary?: string }).summary">{{ (c as { summary?: string }).summary }}</p>
              </li>
            </ul>
          </section>
          <a
            v-if="analysisDetail.pdf_url"
            :href="analysisDetail.pdf_url"
            target="_blank"
            rel="noopener"
            class="record-analysis__pdf"
          >下载 PDF</a>
        </article>
      </div>
    </el-drawer>
  </div>
</template>

<style scoped>
.profile-records__head {
  margin-bottom: 8px;
}

.profile-page-title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #1f2937;
}

.profile-records__sub {
  margin: 6px 0 0;
  font-size: 13px;
  color: #6b7280;
}

.pc-tabs {
  display: flex;
  align-items: center;
  gap: 24px;
  margin-bottom: 14px;
  padding: 0 4px;
  border-bottom: 1px solid #e8e8e8;
  overflow-x: auto;
}

.pc-tabs__item {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 10px 2px 12px;
  border: none;
  background: none;
  cursor: pointer;
  font-size: 14px;
  font-weight: 400;
  color: #6b7280;
  white-space: nowrap;
}

.pc-tabs__item:hover,
.pc-tabs__item.active {
  color: #10b981;
}

.pc-tabs__item.active::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  bottom: -1px;
  height: 2px;
  border-radius: 2px 2px 0 0;
  background: linear-gradient(90deg, #34d399 0%, #10b981 52%, #059669 100%);
}

.tab-icon {
  font-size: 14px;
}

.profile-records__card {
  background: #fff;
  border: 1px solid #e8e8e8;
  border-radius: 24px;
  min-height: 320px;
  padding: 8px 0;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
}

.profile-records__empty {
  padding: 48px 24px;
  text-align: center;
  color: #6b7280;
}

.record-row--with-ops {
  cursor: default;
  align-items: center;
}

.record-row--with-ops:hover {
  background: #ecfdf5;
}

.record-time--inline {
  display: block;
  margin-top: 6px;
  font-size: 12px;
  color: #94a3b8;
}

.record-row__ops {
  flex-shrink: 0;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  justify-content: flex-end;
  max-width: 480px;
}

.rec-op {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  border: none;
  border-radius: 999px;
  padding: 6px 12px;
  font-size: 12px;
  font-weight: 400;
  line-height: 1.4;
  cursor: pointer;
  white-space: nowrap;
}

.rec-op__icon {
  font-size: 14px;
}

.rec-op--view { background: #ecfdf5; color: #059669; }
.rec-op--edit { background: linear-gradient(90deg, #34d399 0%, #10b981 52%, #059669 100%); color: #fff; }
.rec-op--word,
.rec-op--print { background: #f3f4f6; color: #4b5563; }
.rec-op--del { background: #fef2f2; color: #dc2626; }

@media (max-width: 900px) {
  .record-row--with-ops {
    flex-direction: column;
    align-items: stretch;
  }
  .record-row__ops {
    max-width: none;
    justify-content: flex-start;
  }
}

.record-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 20px;
  border-bottom: 1px solid #f1f5f9;
  cursor: pointer;
  transition: background 0.15s;
}

.record-row:hover {
  background: #ecfdf5;
}

.record-row:last-child {
  border-bottom: none;
}

.record-row__main {
  min-width: 0;
  flex: 1;
}

.record-tag {
  display: inline-block;
  margin-right: 8px;
  padding: 2px 8px;
  font-size: 11px;
  font-weight: 600;
  color: #047857;
  background: #ecfdf5;
  border-radius: 4px;
}

.record-tag--search {
  color: #065f46;
  background: #d1fae5;
}

.record-tag--read {
  color: #047857;
  background: #d1fae5;
}

.record-read__body {
  max-height: 420px;
  overflow-y: auto;
  padding: 12px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #fff;
}

.record-read__notes {
  margin-top: 16px;
}

.record-read__notes h4 {
  margin: 0 0 8px;
  font-size: 14px;
  color: #1e293b;
}

.record-tag--analysis {
  color: #047857;
  background: #ecfdf5;
}

.record-analysis__case,
.record-analysis__body,
.record-analysis__cases {
  margin-bottom: 20px;
}

.record-analysis h4 {
  margin: 0 0 10px;
  font-size: 14px;
  font-weight: 500;
  color: #111827;
}

.record-analysis__case p {
  margin: 0;
  font-size: 14px;
  line-height: 1.65;
  color: #475569;
}

.record-analysis__cases ul {
  list-style: none;
  margin: 0;
  padding: 0;
}

.record-analysis__cases li {
  padding: 10px 0;
  border-bottom: 1px dashed #e2e8f0;
  font-size: 13px;
}

.record-analysis__pdf {
  display: inline-block;
  margin-top: 8px;
  font-size: 13px;
  color: #10b981;
}

.record-empty-body {
  color: #64748b;
  font-size: 14px;
  line-height: 1.7;
}

.record-title {
  font-size: 15px;
  color: #1e293b;
}

.record-preview {
  margin: 6px 0 0;
  font-size: 13px;
  color: #64748b;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.record-time {
  flex-shrink: 0;
  font-size: 12px;
  color: #94a3b8;
}

.record-badges {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}

.risk {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 4px;
}

.risk--high {
  color: #b91c1c;
  background: #fee2e2;
}

.risk--med {
  color: #b45309;
  background: #fef3c7;
}

.risk--low {
  color: #047857;
  background: #d1fae5;
}

.profile-records__pager {
  padding: 12px 20px;
  display: flex;
  justify-content: flex-end;
}

.record-drawer-body {
  padding: 0 4px 24px;
}

.record-drawer-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #e2e8f0;
  position: sticky;
  top: 0;
  background: #fff;
  z-index: 2;
}

.record-doc-meta {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #64748b;
  margin-bottom: 12px;
}

.record-doc-preview :deep(.doc-preview-markdown) {
  font-size: 15px;
  line-height: 1.85;
  color: #1e293b;
}

.record-review-summary {
  font-size: 15px;
  line-height: 1.7;
  color: #334155;
  margin: 0 0 12px;
}

.record-review-stats {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}

.record-annotation-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.annotation-card {
  padding: 12px 14px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
}

.annotation-card__head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  font-size: 13px;
  font-weight: 600;
}

.annotation-quote {
  margin: 0 0 8px;
  font-size: 13px;
  color: #475569;
  line-height: 1.6;
  padding-left: 10px;
  border-left: 3px solid #cbd5e1;
}

.annotation-suggest {
  margin: 0;
  font-size: 13px;
  color: #1e293b;
  line-height: 1.55;
}

.record-search-summary {
  padding: 12px 14px;
  background: #ecfdf5;
  border-left: 3px solid #10b981;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.65;
  margin: 0 0 16px;
}

.record-search-hits {
  list-style: none;
  margin: 0;
  padding: 0;
}

.record-search-hits li {
  padding: 12px 0;
  border-bottom: 1px dashed #e2e8f0;
}

.record-search-hits li:last-child {
  border-bottom: none;
}

.record-search-hits strong {
  display: block;
  font-size: 14px;
  color: #111827;
  margin-bottom: 6px;
}

.record-search-hits p {
  margin: 0;
  font-size: 13px;
  color: #64748b;
  line-height: 1.55;
  white-space: pre-wrap;
  word-break: break-word;
}

.record-consult {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.consult-bubble {
  max-width: 92%;
  padding: 12px 14px;
  border-radius: 14px;
  background: #f4f6fb;
}

.consult-bubble--user {
  align-self: flex-end;
  background: #eef2ff;
}

.consult-bubble__role {
  display: block;
  margin-bottom: 4px;
  font-size: 12px;
  color: #6d5efc;
}

.consult-bubble p {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.6;
  color: #1f2937;
}
</style>

<style src="../../styles/document-preview.css"></style>
