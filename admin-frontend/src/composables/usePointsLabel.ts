import { computed } from 'vue'
import { usePublicConfig } from './usePublicConfig'

/** 全站积分展示名（来自后台 billing → points_display_name，公开配置下发） */
export function usePointsLabel() {
  const { config, load, loaded } = usePublicConfig()

  const pointsName = computed(
    () => (config.value.points_display_name || '').trim() || '法理豆',
  )

  return { pointsName, config, load, loaded }
}
