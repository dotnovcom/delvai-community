import { computed } from 'vue'
import { WORKSPACE_NAV, WORKSPACE_META, type WorkspaceNavItem } from '../constants/workspaceNav'
import { usePublicConfig } from './usePublicConfig'


const extraNav: WorkspaceNavItem[] = [

]
const extraMeta: Record<string, { title: string; icon: string; desc?: string }> = {

}

/** 平台名称与 AI 导航名（来自后台 general 配置，公开 API 下发） */
export function useBrandLabels() {
  const { config, load, loaded } = usePublicConfig()

  const platformName = computed(() => (config.value.platform_name || '').trim())
  const aiNavLabel = computed(() => (config.value.ai_nav_label || '').trim())

  function flagOn(key: string) {
    const raw = config.value[key]
    if (raw == null || String(raw).trim() === '') return true
    return ['1', 'true', 'yes', 'on'].includes(String(raw).trim().toLowerCase())
  }

  const voiceEnabled = computed(() => flagOn('feature_voice_enabled'))
  const videoEnabled = computed(() => flagOn('feature_video_enabled'))
  const esignEnabled = computed(() => flagOn('feature_esign_enabled'))
  const multimodalEnabled = computed(() => voiceEnabled.value || videoEnabled.value)

  const workspaceNav = computed(() =>
    [...WORKSPACE_NAV, ...extraNav]
      .filter((item) => item.key !== 'multimodal' || multimodalEnabled.value)
      .map((item) =>
        item.key === 'ai' ? { ...item, label: aiNavLabel.value || '咨询' } : item,
      ),
  )

  function workspaceMeta(key: string) {
    const base = WORKSPACE_META[key] || extraMeta[key] || WORKSPACE_META.ai
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
    voiceEnabled,
    videoEnabled,
    esignEnabled,
    multimodalEnabled,
    config,
    load,
    loaded,
  }
}
