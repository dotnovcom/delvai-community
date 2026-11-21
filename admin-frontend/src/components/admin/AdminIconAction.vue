<script setup lang="ts">
import { ChatLineRound, CircleClose, Delete, Document, Edit, Select, View } from '@element-plus/icons-vue'
import type { Component } from 'vue'
import AdminOpBtn from './AdminOpBtn.vue'

const props = withDefaults(
  defineProps<{
    action: 'view' | 'edit' | 'delete' | 'document' | 'reply' | 'success' | 'warn' | 'muted'
    label?: string
    disabled?: boolean
  }>(),
  { disabled: false },
)

const emit = defineEmits<{ click: [e?: MouseEvent] }>()

const PRESETS: Record<
  string,
  { variant: 'view' | 'edit' | 'success' | 'warn' | 'danger' | 'muted'; label: string; icon: Component }
> = {
  view: { variant: 'view', label: '查看', icon: View },
  edit: { variant: 'edit', label: '编辑', icon: Edit },
  delete: { variant: 'danger', label: '删除', icon: Delete },
  document: { variant: 'view', label: '全文', icon: Document },
  reply: { variant: 'edit', label: '处理', icon: ChatLineRound },
  success: { variant: 'success', label: '通过', icon: Select },
  warn: { variant: 'warn', label: '拒绝', icon: CircleClose },
  muted: { variant: 'muted', label: '关闭', icon: CircleClose },
}

function onClick(e?: MouseEvent) {
  e?.stopPropagation()
  emit('click', e)
}
</script>

<template>
  <AdminOpBtn
    :variant="PRESETS[action]?.variant ?? 'edit'"
    :label="label ?? PRESETS[action]?.label ?? ''"
    :icon="PRESETS[action]?.icon"
    :disabled="disabled"
    @click="onClick"
  />
</template>
