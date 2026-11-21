<script setup lang="ts">
import type { Component } from 'vue'

withDefaults(
  defineProps<{
    label: string
    variant?: 'view' | 'edit' | 'success' | 'warn' | 'danger' | 'muted' | 'slate'
    icon?: Component
    disabled?: boolean
  }>(),
  { variant: 'edit', disabled: false },
)

defineEmits<{ click: [e: MouseEvent] }>()
</script>

<template>
  <button
    type="button"
    class="admin-op-btn"
    :class="`admin-op-btn--${variant}`"
    :disabled="disabled"
    @click="$emit('click', $event)"
  >
    <el-icon v-if="icon" class="admin-op-btn__icon"><component :is="icon" /></el-icon>
    <span>{{ label }}</span>
  </button>
</template>

<style scoped>
.admin-op-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  height: 28px;
  padding: 0 10px;
  border: none;
  border-radius: 5px;
  font-size: 12px;
  font-weight: 500;
  line-height: 1;
  cursor: pointer;
  white-space: nowrap;
  color: #fff;
  transition: transform 0.15s, box-shadow 0.15s, opacity 0.15s;
  box-shadow: 0 2px 8px rgba(67, 56, 202, 0.15);
}

.admin-op-btn:hover {
  transform: translateY(-1px);
  opacity: 0.92;
}

.admin-op-btn:active {
  transform: scale(0.97);
}

.admin-op-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
  transform: none;
  pointer-events: none;
}

.admin-op-btn__icon {
  font-size: 13px;
}

.admin-op-btn--view {
  background: linear-gradient(145deg, #6366f1, #4338ca);
  box-shadow: 0 2px 8px rgba(67, 56, 202, 0.28);
}

.admin-op-btn--edit {
  background: linear-gradient(145deg, #60a5fa, #2563eb);
  box-shadow: 0 2px 8px rgba(37, 99, 235, 0.3);
}

.admin-op-btn--success {
  background: linear-gradient(145deg, #34d399, #059669);
  box-shadow: 0 2px 8px rgba(5, 150, 105, 0.25);
}

.admin-op-btn--warn {
  background: linear-gradient(145deg, #fbbf24, #d97706);
  box-shadow: 0 2px 8px rgba(217, 119, 6, 0.25);
}

.admin-op-btn--danger {
  background: linear-gradient(145deg, #fb7185, #e11d48);
  box-shadow: 0 2px 8px rgba(225, 29, 72, 0.25);
}

.admin-op-btn--muted {
  background: linear-gradient(145deg, #fb923c, #ea580c);
  box-shadow: 0 2px 8px rgba(234, 88, 12, 0.25);
}

.admin-op-btn--slate {
  background: linear-gradient(145deg, #94a3b8, #475569);
  box-shadow: 0 2px 8px rgba(71, 85, 105, 0.25);
}
</style>
