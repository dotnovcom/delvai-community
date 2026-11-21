import { onMounted, onUnmounted, ref } from 'vue'
import { getUnreadNotificationCount } from '../api/auth'
import { useUserStore } from '../store/user'

export function useNotificationUnread() {
  const userStore = useUserStore()
  const unreadCount = ref(0)
  let timer: ReturnType<typeof setInterval> | null = null

  async function refresh() {
    if (!userStore.isLoggedIn) {
      unreadCount.value = 0
      return
    }
    try {
      const res = await getUnreadNotificationCount()
      unreadCount.value = res.count || 0
    } catch {
      unreadCount.value = 0
    }
  }

  function onUpdated() {
    refresh()
  }

  onMounted(() => {
    refresh()
    window.addEventListener('notifications-updated', onUpdated)
    timer = setInterval(refresh, 60000)
  })

  onUnmounted(() => {
    window.removeEventListener('notifications-updated', onUpdated)
    if (timer) clearInterval(timer)
  })

  return { unreadCount, refresh }
}
