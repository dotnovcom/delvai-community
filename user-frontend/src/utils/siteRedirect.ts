/** 手机打开电脑站时，按平台配置的 H5 域名跳转。 */

const WEB_TO_H5: Record<string, string> = {
  '/': '/pages/chat/chat',
  '/login': '/pages/login/login',
  '/register': '/pages/auth/register',
  '/forgot-password': '/pages/auth/forgot-password',
  '/news': '/pages/news/list?category=announcement',
  '/membership': '/pages/membership/membership',
  '/chat/ai': '/pages/chat/chat',
  '/chat/search': '/pages/search/search',
  '/chat/read': '/pages/read/read',
  '/chat/contract': '/pages/contracts/contracts',
  '/chat/document': '/pages/documents/documents',
  '/chat/lawyer': '/pages/lawyers/lawyers',
  '/chat/multimodal': '/pages/multimodal/index',
  '/chat/analysis': '/pages/analysis/report',
  '/chat/enterprise': '/pages/enterprise/enterprise',
  '/profile': '/pages/mine/mine',
  '/profile/membership': '/pages/membership/membership',
  '/profile/wallet': '/pages/profile/wallet',
  '/profile/orders': '/pages/orders/orders',
  '/profile/usage': '/pages/profile/usage',
  '/profile/records': '/pages/profile/records',
  '/profile/notifications': '/pages/profile/notifications',
  '/profile/security': '/pages/profile/security',
}

function flagOn(raw: unknown) {
  return ['1', 'true', 'yes', 'on'].includes(String(raw ?? '').trim().toLowerCase())
}

export function isMobileClient() {
  if (typeof navigator === 'undefined') return false
  return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini|Mobile/i.test(navigator.userAgent)
}

function otherOrigin(raw: unknown) {
  const value = String(raw || '').trim().replace(/\/$/, '')
  if (!value || typeof location === 'undefined') return ''
  let host = ''
  try {
    host = new URL(value).host
  } catch {
    return ''
  }
  if (!host || host === location.host) return ''
  const targetLocal = /localhost|127\.0\.0\.1/i.test(host)
  const hereLocal = /localhost|127\.0\.0\.1/i.test(location.hostname)
  if (targetLocal !== hereLocal) return ''
  return value
}

function toH5Hash(fullPath: string) {
  const path = fullPath.split('?')[0]
  const query = fullPath.includes('?') ? fullPath.slice(fullPath.indexOf('?')) : ''
  if (WEB_TO_H5[path]) {
    const mapped = WEB_TO_H5[path]
    if (mapped.includes('?') || !query) return mapped
    return `${mapped}${query}`
  }
  if (path.startsWith('/news/')) return `/pages/news/detail?id=${path.split('/').pop()}`
  return '/pages/chat/chat'
}

export function redirectPcToH5(config: Record<string, string | undefined>, fullPath: string) {
  if (!flagOn(config.pc_redirect_mobile_enabled) || !isMobileClient()) return false
  const origin = otherOrigin(config.h5_site_url)
  if (!origin) return false
  const hash = toH5Hash(fullPath)
  window.location.replace(`${origin}/#${hash}`)
  return true
}
