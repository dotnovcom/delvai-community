import type { RouteLocationRaw } from 'vue-router'

/** 登录中转页（AuthLegacyRedirect 会打开弹窗并跳转到工作台） */
export function buildLoginRoute(redirect?: string, reason?: string): RouteLocationRaw {
  return {
    path: '/login',
    query: {
      ...(redirect ? { redirect } : {}),
      ...(reason ? { reason } : {}),
    },
    replace: true,
  }
}

/** 管理后台会话失效：硬跳转，避免 router 取消导航导致白屏 */
export function hardRedirectToLogin(redirect?: string, reason = 'session_expired'): void {
  const target = redirect ?? `${window.location.pathname}${window.location.search}`
  const q = new URLSearchParams()
  if (target) q.set('redirect', target)
  if (reason) q.set('reason', reason)
  window.location.assign(`/login?${q.toString()}`)
}

export function isAdminPath(path = window.location.pathname): boolean {
  return path === '/admin' || path.startsWith('/admin/')
}
