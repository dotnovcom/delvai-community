<script setup lang="ts">
defineProps<{
  loading?: boolean
  fill?: boolean
}>()
</script>

<template>
  <div
    v-loading="loading"
    class="admin-table-card"
    :class="{ 'admin-table-card--fill': fill }"
  >
    <div class="admin-table-card__body">
      <slot />
    </div>
    <div v-if="$slots.footer" class="admin-table-card__footer">
      <slot name="footer" />
    </div>
  </div>
</template>
