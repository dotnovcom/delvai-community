import { computed, onMounted, ref } from 'vue'
import { getUsageSummary, type UsageQuotaItem } from '../api/membership'
import { getToken } from '../utils/request'

/** 在工作台功能页展示剩余额度（对标法睿输入框内额度提示）。 */
export function useFeatureQuotaHint(quotaKeys: string[]) {
  const items = ref<UsageQuotaItem[]>([])

  async function load() {
    if (!getToken()) {
      items.value = []
      return
    }
    try {
      const data = await getUsageSummary()
      items.value = data.items.filter((i) => quotaKeys.includes(i.key))
    } catch {
      items.value = []
    }
  }

  onMounted(load)

  const hintText = computed(() => {
    if (!items.value.length) return ''
    return items.value
      .map((i) => {
        if (i.unlimited) return `${i.label}：不限`
        const rem = i.remaining ?? 0
        const period = i.period === 'daily' ? '/日' : i.period === 'monthly' ? '/月' : ''
        return `${i.label}剩余 ${rem} 次${period}`
      })
      .join(' · ')
  })

  return { hintText, reload: load }
}
