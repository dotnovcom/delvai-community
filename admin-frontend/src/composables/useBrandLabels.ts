import { computed } from 'vue'
import { WORKSPACE_NAV, WORKSPACE_META } from '../constants/workspaceNav'
import { usePublicConfig } from './usePublicConfig'

/** 平台名称与 AI 导航名（来自后台 general 配置，公开 API 下发） */
export function useBrandLabels() {
  const { config, load, loaded } = usePublicConfig()

  const platformName = computed(() => (config.value.platform_name || '').trim())
  const aiNavLabel = computed(() => (config.value.ai_nav_label || '').trim())

  const workspaceNav = computed(() =>
    WORKSPACE_NAV.map((item) =>
      item.key === 'ai' ? { ...item, label: aiNavLabel.value || '咨询' } : item,
    ),
  )

  function workspaceMeta(key: string) {
    const base = WORKSPACE_META[key] || WORKSPACE_META.ai
    const name = platformName.value
    const desc =
      base.desc && name ? `${name} · ${base.desc}` : base.desc
    if (key === 'ai') {
      return { ...base, title: aiNavLabel.value || '咨询', desc }
    }
    return { ...base, desc }
  }

  const brandInitial = computed(() => (platformName.value[0] || '').toUpperCase())

  return {
    platformName,
    aiNavLabel,
    brandInitial,
    workspaceNav,
    workspaceMeta,
    config,
    load,
    loaded,
  }
}
