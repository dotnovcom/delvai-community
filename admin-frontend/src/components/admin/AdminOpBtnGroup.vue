<script setup lang="ts">
defineProps<{ nowrap?: boolean; compact?: boolean }>()
</script>

<template>
  <div
    class="admin-op-btn-group"
    :class="{ 'admin-op-btn-group--nowrap': nowrap, 'admin-op-btn-group--compact': compact }"
    @click.stop
  >
    <slot />
  </div>
</template>

<style scoped>
.admin-op-btn-group {
  display: inline-flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.admin-op-btn-group--nowrap {
  flex-wrap: nowrap;
}

.admin-op-btn-group--compact {
  width: 100%;
  justify-content: center;
  gap: 4px;
}

.admin-op-btn-group--compact :deep(.admin-op-btn) {
  flex: 0 1 auto;
  min-width: 0;
  padding: 0 8px;
  font-size: 11px;
  height: 26px;
  justify-content: center;
}
</style>
