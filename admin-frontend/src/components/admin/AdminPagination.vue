<script setup lang="ts">
const page = defineModel<number>('page', { required: true })
const pageSize = defineModel<number>('pageSize', { required: true })

defineProps<{
  total: number
}>()

const emit = defineEmits<{ change: [] }>()

const pageSizes = [10, 20, 50, 100]

function onChange() {
  emit('change')
}
</script>

<template>
  <div class="admin-pagination">
    <span class="admin-pagination__hint">共 {{ total }} 条</span>
    <el-pagination
      v-model:current-page="page"
      v-model:page-size="pageSize"
      :total="total"
      :page-sizes="pageSizes"
      layout="sizes, prev, pager, next, jumper"
      background
      @size-change="onChange"
      @current-change="onChange"
    />
  </div>
</template>
