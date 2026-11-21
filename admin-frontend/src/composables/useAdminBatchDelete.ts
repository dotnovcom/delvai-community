import { ref, type Ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

export function useAdminBatchDelete<T extends { id: number }>(
  selected: Ref<T[]>,
  removeOne: (id: number) => Promise<unknown>,
  options?: { label?: string; onDone?: () => void | Promise<void> },
) {
  const deleting = ref(false)

  async function confirmBatchDelete() {
    if (!selected.value.length) return
    const label = options?.label ?? '条记录'
    await ElMessageBox.confirm(
      `确定删除选中的 ${selected.value.length} ${label}？此操作不可恢复。`,
      '批量删除',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
    deleting.value = true
    try {
      await Promise.all(selected.value.map((row) => removeOne(row.id)))
      ElMessage.success(`已删除 ${selected.value.length} 条`)
      selected.value = []
      await options?.onDone?.()
    } finally {
      deleting.value = false
    }
  }

  return { deleting, confirmBatchDelete }
}
