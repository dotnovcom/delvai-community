<script setup lang="ts">

import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import Quill from 'quill'

import 'quill/dist/quill.snow.css'

import {

  documentBodyHtml,

  resolveDocumentTitle,

  stripLeadingDocumentTitle,

} from '../../utils/documentExport'

import { sanitizeDocumentHtml } from '../../utils/sanitizeHtml'
import { contractPlainToHtml } from '../../utils/contractRevision'



const props = withDefaults(

  defineProps<{

    modelValue: string

    title?: string

    docType?: string

    editableTitle?: boolean

    readonly?: boolean

    placeholder?: string

    minHeight?: string

    /** 管理端模板编辑：不展示/剥离标题，原样渲染 HTML 骨架 */
    templateMode?: boolean

    /** 合同审查预览：工具栏固定，仅正文区滚动；纯文本按段落渲染 */
    contractMode?: boolean

    /** 工具栏固定在顶部，仅编辑区滚动 */
    stickyToolbar?: boolean

    /** 保留 Word 原版式：不经 Quill 渲染，直接输出 HTML（表格/对齐/缩进） */
    preserveLayout?: boolean

  }>(),

  {

    title: '',

    docType: '',

    editableTitle: false,

    readonly: false,

    placeholder: '在此编辑文书正文…',

    minHeight: '360px',

    templateMode: false,

    contractMode: false,

    stickyToolbar: false,

    preserveLayout: false,

  },

)



const emit = defineEmits<{

  'update:modelValue': [value: string]

  'update:title': [value: string]

}>()



const toolbarRef = ref<HTMLElement | null>(null)

const editorRef = ref<HTMLElement | null>(null)

const nativeBodyRef = ref<HTMLElement | null>(null)

const localTitle = ref('')

const HIGHLIGHT_BLOCK_CLASS = 'contract-revision-highlight'

const HIGHLIGHT_MARK_CLASS = 'contract-revision-mark'

let quill: Quill | null = null

let syncing = false



function resolvedDisplayTitle(content = props.modelValue) {

  return resolveDocumentTitle(props.title || localTitle.value || '', props.docType, content)

}



const showTitle = computed(() => (props.templateMode ? '' : resolvedDisplayTitle()))



function syncTitleFromContent(content = props.modelValue) {

  const resolved = resolvedDisplayTitle(content)

  if (resolved && resolved !== localTitle.value) {

    localTitle.value = resolved

    emit('update:title', resolved)

  }

}



function htmlFromContent(content: string) {

  if (!content?.trim()) return ''

  if (props.templateMode) {

    if (content.trim().startsWith('<')) return sanitizeDocumentHtml(content)

    if (props.contractMode) return contractPlainToHtml(content)

    return documentBodyHtml(content)

  }

  const displayTitle = resolvedDisplayTitle(content)

  const body = stripLeadingDocumentTitle(content, displayTitle, props.docType)

  if (body.trim().startsWith('<')) return sanitizeDocumentHtml(body)

  return documentBodyHtml(body)

}



function getEditorRoot(): HTMLElement | null {
  if (props.preserveLayout) return nativeBodyRef.value
  return quill?.root ?? null
}



function getHtml(): string {

  if (props.preserveLayout) {

    const raw = nativeBodyRef.value?.innerHTML || ''

    if (!raw || raw === '<p><br></p>') return ''

    return sanitizeDocumentHtml(raw)

  }

  if (!quill) return sanitizeDocumentHtml(props.modelValue)

  const raw = quill.root.innerHTML

  if (!raw || raw === '<p><br></p>') return ''

  return sanitizeDocumentHtml(raw)

}



function setHtml(content: string, silent = false) {

  clearRevisionHighlight()

  syncTitleFromContent(content)

  const html = htmlFromContent(content) || '<p><br></p>'

  if (props.preserveLayout) {

    syncing = true

    if (nativeBodyRef.value) nativeBodyRef.value.innerHTML = html

    syncing = false

    if (!silent) emit('update:modelValue', getHtml())

    return

  }

  if (!quill) return

  syncing = true

  quill.setContents([])

  quill.clipboard.dangerouslyPasteHTML(html, 'silent')

  syncing = false

  if (!silent) emit('update:modelValue', getHtml())

}



function clearRevisionHighlight() {

  const root = getEditorRoot()

  if (!root) return

  root.querySelectorAll(`.${HIGHLIGHT_BLOCK_CLASS}`).forEach((el) => {

    el.classList.remove(HIGHLIGHT_BLOCK_CLASS)

  })

  root.querySelectorAll(`mark.${HIGHLIGHT_MARK_CLASS}`).forEach((el) => {

    const mark = el as HTMLElement

    const parent = mark.parentNode

    if (!parent) return

    while (mark.firstChild) parent.insertBefore(mark.firstChild, mark)

    parent.removeChild(mark)

    parent.normalize?.()

  })

}



function wrapFirstTextMatch(root: HTMLElement, search: string): HTMLElement | null {

  const fullText = root.innerText || ''

  const idx = fullText.indexOf(search)

  if (idx < 0) return null

  let charCount = 0

  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT)

  let startNode: Text | null = null

  let startOffset = 0

  let endNode: Text | null = null

  let endOffset = 0

  const endIdx = idx + search.length

  while (walker.nextNode()) {

    const node = walker.currentNode as Text

    const len = node.length

    if (!startNode && charCount + len > idx) {

      startNode = node

      startOffset = idx - charCount

    }

    if (charCount + len >= endIdx) {

      endNode = node

      endOffset = endIdx - charCount

      break

    }

    charCount += len

  }

  if (!startNode || !endNode) return null

  try {

    const range = document.createRange()

    range.setStart(startNode, startOffset)

    range.setEnd(endNode, endOffset)

    const mark = document.createElement('mark')

    mark.className = HIGHLIGHT_MARK_CLASS

    range.surroundContents(mark)

    return mark

  } catch {

    return null

  }

}



/** 定位并高亮刚修订的片段（接受修订后调用；会先清除上一次高亮） */
function highlightRevisionSnippet(snippet: string): boolean {

  clearRevisionHighlight()

  const root = getEditorRoot()

  if (!root || !snippet?.trim()) return false

  const variants = [

    snippet.trim(),

    snippet.trim().slice(0, 120),

    snippet.trim().slice(0, 60),

    snippet.trim().slice(0, 30),

  ].filter((s, i, arr) => s.length >= 10 && arr.indexOf(s) === i)

  for (const search of variants) {

    const compact = search.replace(/\s+/g, '')

    const blocks = root.querySelectorAll('p, td, .contract-sign-row, .contract-clause-heading, .contract-doc-title, table')

    for (const block of blocks) {

      const blockText = (block.textContent || '').replace(/\s+/g, '')

      const probe = compact.slice(0, Math.min(28, compact.length))

      if (probe.length >= 8 && blockText.includes(probe)) {

        block.classList.add(HIGHLIGHT_BLOCK_CLASS)

        block.scrollIntoView({ behavior: 'smooth', block: 'center' })

        return true

      }

    }

    const mark = wrapFirstTextMatch(root, search)

    if (mark) {

      mark.scrollIntoView({ behavior: 'smooth', block: 'center' })

      return true

    }

  }

  return false

}



function initQuill() {

  if (!editorRef.value || !toolbarRef.value || quill) return

  quill = new Quill(editorRef.value, {

    theme: 'snow',

    placeholder: props.placeholder,

    modules: { toolbar: toolbarRef.value },

  })

  quill.on('text-change', () => {

    if (syncing || props.readonly) return

    emit('update:modelValue', getHtml())

  })

  quill.enable(!props.readonly)

  setHtml(props.modelValue, true)

  nextTick(() => {

    if (!props.readonly) emit('update:modelValue', getHtml())

  })

}



onMounted(() => {

  if (props.preserveLayout) {

    nextTick(() => setHtml(props.modelValue, true))

    return

  }

  nextTick(initQuill)

})



onBeforeUnmount(() => {

  if (!syncing && quill && !props.readonly) {

    emit('update:modelValue', getHtml())

  }

  quill = null

})



watch(

  () => [props.title, props.modelValue, props.docType] as const,

  () => syncTitleFromContent(),

  { immediate: true },

)



watch(

  () => props.modelValue,

  (v) => {

    if (props.preserveLayout) {

      if (syncing) return

      const normalized = htmlFromContent(v)

      const current = sanitizeDocumentHtml(nativeBodyRef.value?.innerHTML || '')

      if (current !== normalized) setHtml(v, true)

      return

    }

    if (!quill || syncing) return

    const normalized = htmlFromContent(v)

    const current = sanitizeDocumentHtml(quill.root.innerHTML)

    if (current !== normalized) setHtml(v, true)

  },

)



watch(

  () => props.readonly,

  (ro) => {

    quill?.enable(!ro)

  },

)



defineExpose({ getHtml, setHtml, highlightRevisionSnippet, clearRevisionHighlight })

</script>



<template>

  <div
    class="doc-rich-editor"
    :class="{
      'doc-rich-editor--readonly': readonly,
      'doc-rich-editor--sticky': stickyToolbar,
      'doc-rich-editor--contract': contractMode,
      'doc-rich-editor--preserve': preserveLayout,
    }"
  >

    <div v-show="!readonly && !preserveLayout" ref="toolbarRef" class="doc-quill-toolbar">

      <span class="ql-formats">

        <button type="button" class="ql-bold" title="加粗" />

        <button type="button" class="ql-italic" title="斜体" />

        <button type="button" class="ql-underline" title="下划线" />

        <button type="button" class="ql-strike" title="删除线" />

      </span>

      <span class="ql-formats">

        <select class="ql-align" title="对齐">

          <option selected />

          <option value="center" />

          <option value="right" />

          <option value="justify" />

        </select>

      </span>

      <span class="ql-formats">

        <button type="button" class="ql-header" value="2" title="小标题" />

        <button type="button" class="ql-header" value="false" title="正文" />

      </span>

      <span class="ql-formats">

        <button type="button" class="ql-list" value="ordered" title="编号列表" />

        <button type="button" class="ql-list" value="bullet" title="无序列表" />

        <button type="button" class="ql-indent" value="-1" title="减少缩进" />

        <button type="button" class="ql-indent" value="+1" title="增加缩进" />

      </span>

      <span class="ql-formats">

        <button type="button" class="ql-link" title="链接" />

        <button type="button" class="ql-clean" title="清除格式" />

      </span>

    </div>



    <div class="doc-rich-editor__paper">

      <h1 v-if="showTitle" class="doc-rich-editor__title doc-rich-editor__title--static">

        {{ showTitle }}

      </h1>

      <div
        v-if="preserveLayout"
        ref="nativeBodyRef"
        class="doc-native-body doc-preview-markdown"
        :style="{ minHeight }"
      />

      <div v-else ref="editorRef" class="doc-quill-body doc-preview-markdown" :style="{ minHeight }" />

    </div>

  </div>

</template>



<style scoped>

.doc-rich-editor {

  width: 100%;
  overflow: hidden;

  background: var(--ds-paper, #fffdf8);

}



.doc-quill-toolbar {
  background: #f1f5f9;
  padding: 6px 8px;
  border: 1px solid #e2e8f0;

}



.doc-quill-toolbar :deep(.ql-toolbar.ql-snow) {

  border: none;

  padding: 0;

}

.doc-rich-editor__title {

  display: block;

  width: 100%;

  margin: 0 0 14px;

  padding: 0;

  border: none;

  background: transparent;

  text-align: center;

  font-size: 22px;

  font-weight: 700;

  line-height: 1.4;

  color: #1a365d;

  font-family: 'PingFang SC', 'Microsoft YaHei', 'Songti SC', serif;

  outline: none;

}



.doc-rich-editor__title--static {

  text-align: center;

  font-size: 22px;

  font-weight: 700;

  color: #1a365d;

  margin: 0 0 14px;

}



.doc-quill-body :deep(.ql-editor) {
  min-height: inherit;

  font-size: 16px;

  line-height: 1.85;

  color: #1e293b;

  font-family: 'PingFang SC', 'Microsoft YaHei', 'Songti SC', serif;

}



.doc-quill-body :deep(.ql-editor p) {

  margin: 0.5em 0;

  text-indent: 2em;

}



.doc-quill-body :deep(.ql-editor p:first-child) {

  text-indent: 0;

}



.doc-quill-body :deep(.ql-editor .ql-align-center) {

  text-indent: 0;

}



.doc-quill-body :deep(.ql-editor .ql-align-right),
.doc-quill-body :deep(.ql-editor .doc-sign-line),
.doc-quill-body :deep(.ql-editor .doc-sign-block p) {

  text-indent: 0;

  text-align: right;

}



.doc-quill-body :deep(.ql-editor .doc-sign-block) {

  margin-top: 2.5em;

  margin-bottom: 0.5em;

}



.doc-rich-editor--readonly :deep(.ql-toolbar) {

  display: none;

}



.doc-rich-editor--readonly :deep(.ql-container) {

  border: none !important;

}

.ql-container.ql-snow {
    border: 1px solid #e2e8f0;
}

.doc-rich-editor--sticky {

  display: flex;

  flex-direction: column;

  height: 100%;

  min-height: 0;

  overflow: hidden;

}



.doc-rich-editor--sticky .doc-quill-toolbar {

  flex-shrink: 0;

  position: sticky;

  top: 0;

  z-index: 2;

}



.doc-rich-editor--sticky .doc-rich-editor__paper {

  flex: 1;

  min-height: 0;

  overflow-y: auto;

  display: flex;

  flex-direction: column;

}



.doc-rich-editor--contract.doc-rich-editor--sticky .doc-quill-body :deep(.ql-editor p) {

  text-indent: 0;

  margin: 0.45em 0;

  line-height: 1.9;

}



.doc-rich-editor--contract.doc-rich-editor--sticky .doc-quill-body :deep(.ql-editor .contract-doc-title) {

  text-align: center;

  font-size: 18px;

  font-weight: 700;

  line-height: 1.5;

  margin: 0.2em 0 1em;

  letter-spacing: 0.06em;

}



.doc-rich-editor--contract.doc-rich-editor--sticky .doc-quill-body :deep(.ql-editor .contract-clause-heading) {

  font-weight: 700;

  margin-top: 1em;

  margin-bottom: 0.35em;

}



.doc-rich-editor--contract.doc-rich-editor--sticky .doc-quill-body :deep(.ql-editor .contract-sign-block) {

  margin-top: 1.5em;

  line-height: 2;

  font-weight: 600;

}



.doc-rich-editor--contract.doc-rich-editor--sticky .doc-quill-body :deep(.ql-editor .contract-sign-field) {

  margin: 0.15em 0;

  line-height: 1.85;

  padding-left: 2em;

}



.doc-rich-editor--contract.doc-rich-editor--sticky .doc-quill-body :deep(.ql-editor .contract-sign-footer) {

  margin-top: 0.35em;

  line-height: 2;

}



.doc-rich-editor--contract.doc-rich-editor--sticky .doc-quill-body :deep(.ql-editor .contract-sign-row) {

  display: flex;

  justify-content: space-between;

  align-items: flex-start;

  gap: 24px;

  margin: 0.35em 0;

  line-height: 2;

}



.doc-rich-editor--contract.doc-rich-editor--sticky .doc-quill-body :deep(.ql-editor .contract-sign-col) {

  flex: 1;

  min-width: 0;

}



.doc-rich-editor--contract :deep(.ql-editor .contract-revision-highlight) {

  background: rgba(30, 64, 175, 0.12) !important;

  box-shadow: inset 0 0 0 2px rgba(30, 64, 175, 0.5);

  border-radius: 4px;

  transition: background 0.25s ease, box-shadow 0.25s ease;

}



.doc-rich-editor--contract :deep(.ql-editor mark.contract-revision-mark) {

  background: rgba(30, 64, 175, 0.22);

  color: inherit;

  padding: 0 1px;

  border-radius: 2px;

  box-decoration-break: clone;

}



.doc-rich-editor--contract.doc-rich-editor--sticky .doc-quill-body :deep(.ql-editor .contract-doc-table) {

  width: 100%;

  border-collapse: collapse;

  margin: 0.6em 0;

  table-layout: auto;

  border: none;

}



.doc-rich-editor--contract.doc-rich-editor--sticky .doc-quill-body :deep(.ql-editor .contract-doc-table td) {

  border: none;

  padding: 0 8px;

  vertical-align: top;

  text-indent: 0;

}



.doc-rich-editor--contract.doc-rich-editor--sticky .doc-quill-body :deep(.ql-editor .contract-doc-table p) {

  text-indent: 0;

  margin: 0.2em 0;

}



.doc-rich-editor--preserve .doc-native-body {

  padding: 16px 20px;

  font-size: 14px;

  line-height: 1.75;

  color: #1e293b;

  overflow-y: auto;

  max-height: 100%;

}



.doc-rich-editor--preserve.doc-rich-editor--sticky .doc-native-body {

  flex: 1;

  min-height: 0;

}



.doc-rich-editor--preserve .doc-native-body :deep(p) {

  margin: 0.35em 0;

}



.doc-rich-editor--preserve .doc-native-body :deep(.contract-doc-table) {

  width: 100%;

  border-collapse: collapse;

  margin: 0.6em 0;

  table-layout: auto;

  border: none;

}



.doc-rich-editor--preserve .doc-native-body :deep(.contract-doc-table td) {

  border: none;

  padding: 0 8px;

  vertical-align: top;

}



.doc-rich-editor--preserve .doc-native-body :deep(.contract-doc-table p) {

  margin: 0.2em 0;

  text-indent: 0;

}



.doc-rich-editor--preserve .doc-native-body :deep(.contract-revision-highlight) {

  background: rgba(30, 64, 175, 0.12) !important;

  box-shadow: inset 0 0 0 2px rgba(30, 64, 175, 0.5);

  border-radius: 4px;

}



.doc-rich-editor--preserve .doc-native-body :deep(mark.contract-revision-mark) {

  background: rgba(30, 64, 175, 0.22);

  color: inherit;

  padding: 0 1px;

  border-radius: 2px;

}

</style>


