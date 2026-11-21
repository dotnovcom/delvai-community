<script setup lang="ts">
import { nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { sanitizeHtml } from '../../utils/sanitizeHtml'

const props = withDefaults(
  defineProps<{
    modelValue: string
    placeholder?: string
    minHeight?: string
  }>(),
  {
    placeholder: '请输入内容…',
    minHeight: '320px',
  },
)

const emit = defineEmits<{ 'update:modelValue': [value: string] }>()

const editorRef = ref<HTMLDivElement | null>(null)
const sourceRef = ref<HTMLTextAreaElement | null>(null)
const mode = ref<'visual' | 'source'>('visual')
const sourceHtml = ref('')

function syncFromModel() {
  if (mode.value === 'source') {
    sourceHtml.value = props.modelValue || ''
    return
  }
  const el = editorRef.value
  if (!el || el.innerHTML === props.modelValue) return
  el.innerHTML = sanitizeHtml(props.modelValue || '')
}

watch(
  () => props.modelValue,
  () => nextTick(syncFromModel),
  { immediate: true },
)

function emitValue(raw: string) {
  emit('update:modelValue', sanitizeHtml(raw))
}

function onVisualInput() {
  emitValue(editorRef.value?.innerHTML ?? '')
}

function onSourceInput() {
  sourceHtml.value = sourceRef.value?.value ?? ''
  emitValue(sourceHtml.value)
}

function switchMode(next: 'visual' | 'source') {
  if (next === mode.value) return
  if (next === 'source') {
    sourceHtml.value = props.modelValue || ''
    mode.value = 'source'
    nextTick(() => sourceRef.value?.focus())
    return
  }
  emitValue(sourceHtml.value)
  mode.value = 'visual'
  nextTick(syncFromModel)
}

function exec(cmd: string, value?: string) {
  if (mode.value !== 'visual') return
  document.execCommand(cmd, false, value)
  editorRef.value?.focus()
  onVisualInput()
}

function insertLink() {
  if (mode.value !== 'visual') return
  const url = window.prompt('请输入链接地址', 'https://')
  if (url) exec('createLink', url)
}

onBeforeUnmount(() => {
  if (mode.value === 'source') {
    emitValue(sourceHtml.value)
    return
  }
  emitValue(editorRef.value?.innerHTML ?? props.modelValue)
})
</script>

<template>
  <div class="admin-rich-editor">
    <div class="admin-rich-editor__toolbar">
      <template v-if="mode === 'visual'">
        <el-button-group>
          <el-button size="small" @click="exec('bold')"><strong>B</strong></el-button>
          <el-button size="small" @click="exec('italic')"><em>I</em></el-button>
          <el-button size="small" @click="exec('underline')"><u>U</u></el-button>
        </el-button-group>
        <el-button-group>
          <el-button size="small" @click="exec('formatBlock', 'h2')">H2</el-button>
          <el-button size="small" @click="exec('formatBlock', 'h3')">H3</el-button>
          <el-button size="small" @click="exec('formatBlock', 'p')">正文</el-button>
        </el-button-group>
        <el-button-group>
          <el-button size="small" @click="exec('insertUnorderedList')">列表</el-button>
          <el-button size="small" @click="exec('insertOrderedList')">编号</el-button>
        </el-button-group>
        <el-button size="small" @click="insertLink">链接</el-button>
        <el-button size="small" @click="exec('removeFormat')">清除格式</el-button>
      </template>
      <span v-else class="admin-rich-editor__mode-hint">源代码模式：可直接编辑 HTML</span>
      <el-button
        size="small"
        :type="mode === 'source' ? 'primary' : 'default'"
        class="admin-rich-editor__mode-btn"
        @click="switchMode(mode === 'visual' ? 'source' : 'visual')"
      >
        {{ mode === 'visual' ? '源代码' : '可视化' }}
      </el-button>
    </div>
    <div
      v-show="mode === 'visual'"
      ref="editorRef"
      class="admin-rich-editor__body"
      contenteditable="true"
      :data-placeholder="placeholder"
      :style="{ minHeight }"
      @input="onVisualInput"
    />
    <textarea
      v-show="mode === 'source'"
      ref="sourceRef"
      class="admin-rich-editor__source"
      :placeholder="placeholder"
      :style="{ minHeight }"
      :value="sourceHtml"
      spellcheck="false"
      @input="onSourceInput"
    />
  </div>
</template>

<style scoped>
.admin-rich-editor {
  width: 100%;
  border: 1px solid var(--el-border-color);
  border-radius: var(--el-border-radius-base);
  overflow: hidden;
  background: #fff;
}

.admin-rich-editor__toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-bottom: 1px solid var(--el-border-color-lighter);
  background: var(--el-fill-color-light);
}

.admin-rich-editor__mode-btn {
  margin-left: auto;
}

.admin-rich-editor__mode-hint {
  flex: 1;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.admin-rich-editor__body,
.admin-rich-editor__source {
  width: 100%;
  padding: 12px 14px;
  line-height: 1.7;
  font-size: 14px;
  color: var(--el-text-color-primary);
  outline: none;
  overflow-y: auto;
  max-height: 560px;
  box-sizing: border-box;
}

.admin-rich-editor__body:empty::before {
  content: attr(data-placeholder);
  color: var(--el-text-color-placeholder);
}

.admin-rich-editor__source {
  display: block;
  border: none;
  resize: vertical;
  font-family: Consolas, 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
  background: #fafafa;
  tab-size: 2;
}

.admin-rich-editor__body :deep(h2) {
  font-size: 18px;
  margin: 14px 0 8px;
  font-weight: 600;
}

.admin-rich-editor__body :deep(h3) {
  font-size: 16px;
  margin: 12px 0 6px;
  font-weight: 600;
}

.admin-rich-editor__body :deep(h4) {
  font-size: 14px;
  margin: 10px 0 4px;
  font-weight: 600;
}

.admin-rich-editor__body :deep(p) {
  margin: 8px 0;
}

.admin-rich-editor__body :deep(ul),
.admin-rich-editor__body :deep(ol) {
  padding-left: 1.5em;
  margin: 8px 0;
}

.admin-rich-editor__body :deep(li) {
  margin: 4px 0;
}

.admin-rich-editor__body :deep(a) {
  color: var(--el-color-primary);
}

.admin-rich-editor__body :deep(strong) {
  font-weight: 600;
}
</style>
