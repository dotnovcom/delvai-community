<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import type { ApiErrorDetail } from '../utils/error'

const router = useRouter()

function perUseQuery(detail: ApiErrorDetail) {
  const feature = detail.feature || ''
  const query: Record<string, string> = { tab: 'peruse' }
  if (feature === 'contract_review') {
    query.highlight = 'contract_review_once'
  } else if (feature === 'analysis') {
    query.highlight = 'analysis_once'
  } else if (feature === 'chat') {
    query.highlight = 'consult_once'
  }
  return query
}

function onMembershipRequired(e: Event) {
  const detail = (e as CustomEvent<ApiErrorDetail>).detail || {}
  if (detail.code === 'ENTERPRISE_SUBSCRIPTION_REQUIRED') {
    ElMessageBox.confirm(detail.message || '创建企业需要先购买企业版套餐', '需要企业版', {
      confirmButtonText: '购买企业版',
      cancelButtonText: '取消',
      type: 'warning',
    })
      .then(() => {
        router.push({ path: '/profile/membership', query: { audience: 'enterprise' } })
      })
      .catch(() => undefined)
    return
  }

  const msg = detail.message || '该功能需要升级会员或购买按次包'

  ElMessageBox.confirm(msg, '会员权限不足', {
    confirmButtonText: '升级会员',
    cancelButtonText: '购买按次包',
    distinguishCancelAndClose: true,
    type: 'warning',
  })
    .then(() => {
      router.push('/profile/membership')
    })
    .catch((action) => {
      if (action === 'cancel') {
        router.push({ path: '/profile/membership', query: perUseQuery(detail) })
      }
    })
}

onMounted(() => {
  window.addEventListener('membership-required', onMembershipRequired)
})

onUnmounted(() => {
  window.removeEventListener('membership-required', onMembershipRequired)
})
</script>

<template>
  <span style="display: none" />
</template>
