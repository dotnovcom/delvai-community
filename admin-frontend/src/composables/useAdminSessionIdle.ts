import { onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { listAdminSettings } from '../api/admin'
import type { SystemSetting } from '../api/admin'
import { useUserStore } from '../store/user'
import { buildLoginRoute } from '../utils/authRedirect'

const ACTIVITY_EVENTS = ['mousemove', 'mousedown', 'keydown', 'touchstart', 'scroll', 'click'] as const

/** 与后端 resolve_admin_idle_minutes 一致：未配置或 0 时为 30 分钟。 */
export function resolveAdminIdleMinutes(settings: SystemSetting[]): number {
  const dedicated = Number(settings.find((s) => s.key === 'admin_session_idle_minutes')?.value ?? 30)
  if (Number.isFinite(dedicated) && dedicated > 0) return dedicated
  return 30
}

/** 管理后台：无操作超过配置时长自动登出。保存安全配置后立即按新时长计时。 */
export function useAdminSessionIdle() {
  const userStore = useUserStore()
  const router = useRouter()

  let idleMinutes = 30
  let timer: ReturnType<typeof setTimeout> | null = null
  let poll: ReturnType<typeof setInterval> | null = null
  let expired = false
  let lastActivity = Date.now()

  function clearTimer() {
    if (timer) {
      clearTimeout(timer)
      timer = null
    }
  }

  function logoutIdle() {
    if (expired) return
    expired = true
    clearTimer()
    userStore.logout()
    ElMessage.warning('闲置时间已到，请重新登录')
    const redirect = router.currentRoute.value.fullPath || '/admin'
    void router.replace(buildLoginRoute(redirect, 'session_expired'))
  }

  function scheduleIdleCheck() {
    clearTimer()
    if (idleMinutes <= 0 || expired) return
    const remain = idleMinutes * 60 * 1000 - (Date.now() - lastActivity)
    if (remain <= 0) {
      logoutIdle()
      return
    }
    timer = setTimeout(logoutIdle, remain)
  }

  function onActivity() {
    if (expired) return
    lastActivity = Date.now()
    scheduleIdleCheck()
  }

  async function reloadIdleMinutes() {
    if (expired) return
    try {
      const settings = await listAdminSettings('basic')
      const next = resolveAdminIdleMinutes(settings)
      if (next !== idleMinutes) {
        idleMinutes = next
        scheduleIdleCheck()
      }
    } catch {
      if (idleMinutes <= 0) idleMinutes = 30
    }
  }

  function onSettingsSaved() {
    void reloadIdleMinutes()
  }

  onMounted(async () => {
    await reloadIdleMinutes()
    for (const evt of ACTIVITY_EVENTS) {
      window.addEventListener(evt, onActivity, { passive: true })
    }
    window.addEventListener('admin-settings-saved', onSettingsSaved)
    window.addEventListener('focus', onSettingsSaved)
    scheduleIdleCheck()
    poll = setInterval(() => {
      void reloadIdleMinutes()
    }, 20000)
  })

  onUnmounted(() => {
    clearTimer()
    if (poll) clearInterval(poll)
    for (const evt of ACTIVITY_EVENTS) {
      window.removeEventListener(evt, onActivity)
    }
    window.removeEventListener('admin-settings-saved', onSettingsSaved)
    window.removeEventListener('focus', onSettingsSaved)
  })
}
