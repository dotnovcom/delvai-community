<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'

const router = useRouter()

function perUseTarget(detail: {
  quota_key?: string
  suggest_level?: string
  message?: string
}) {
  const key = detail?.quota_key || ''
  const isEnterprise =
    detail?.suggest_level === 'enterprise' || (detail?.message || '').includes('企业团队')
  const query: Record<string, string> = { tab: 'peruse' }

  if (key.includes('contract') || key.includes('monthly_contract')) {
    query.audience = isEnterprise ? 'enterprise' : 'personal'
    query.highlight = isEnterprise ? 'enterprise_contract_pack_10' : 'contract_review_once'
  } else if (key.includes('analysis')) {
    query.highlight = 'analysis_once'
  } else if (key.includes('chat')) {
    query.highlight = 'consult_once'
  }
  return query
}

function onQuotaExceeded(e: Event) {
  const detail = (e as CustomEvent).detail as {
    message?: string
    suggest_level?: string
    quota_key?: string
  } | undefined
  const msg = detail?.message || '今日额度已用完'
  const key = detail?.quota_key || ''
  const isEnterprise = detail?.suggest_level === 'enterprise'

  const perUseHint =
    key.includes('chat') ? '可购买「深度法律咨询(1次)」'
      : key.includes('analysis') ? '可购买「类案分析报告(1次)」'
        : key.includes('contract') ? (isEnterprise ? '可购买「企业合同审查 · 10次包」' : '可购买「合同审查(1次)」')
          : '可购买按次包'

  const confirmText = isEnterprise ? '查看订阅方案' : '升级会员'

  ElMessageBox.confirm(
    `${msg}。${isEnterprise ? '可购买企业团队增购包，' : '升级会员可获得更多额度，'}${perUseHint}。`,
    '额度不足',
    {
      confirmButtonText: confirmText,
      cancelButtonText: '购买按次包',
      distinguishCancelAndClose: true,
      type: 'warning',
    },
  ).then(() => {
    router.push({
      path: '/profile/membership',
      query: isEnterprise ? { audience: 'enterprise' } : {},
    })
  }).catch((action) => {
    if (action === 'cancel') {
      router.push({ path: '/profile/membership', query: perUseTarget(detail || {}) })
    }
  })
}

onMounted(() => {
  window.addEventListener('quota-exceeded', onQuotaExceeded)
})

onUnmounted(() => {
  window.removeEventListener('quota-exceeded', onQuotaExceeded)
})
</script>

<template>
  <span style="display: none" />
</template>
