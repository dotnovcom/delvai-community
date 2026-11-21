<script setup lang="ts">
defineProps<{
  selectedCount?: number
  batchDeletable?: boolean
  batchLoading?: boolean
}>()

const emit = defineEmits<{ 'batch-delete': [] }>()
</script>

<template>
  <div class="admin-filter-bar">
    <div class="admin-filter-bar__main">
      <slot />
    </div>
    <div class="admin-filter-bar__actions">
      <el-button
        v-if="batchDeletable && (selectedCount ?? 0) > 0"
        type="danger"
        plain
        :loading="batchLoading"
        @click="emit('batch-delete')"
      >
        批量删除 ({{ selectedCount }})
      </el-button>
      <slot name="actions" />
    </div>
  </div>
</template>
