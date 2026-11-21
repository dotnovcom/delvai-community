/** 登录后 redirect 仅允许站内相对路径，防开放重定向 */
export function safeRedirectPath(raw: unknown, fallback = '/'): string {
  if (typeof raw !== 'string' || !raw.trim()) return fallback
  const path = raw.trim()
  if (!path.startsWith('/') || path.startsWith('//')) return fallback
  if (/^\/\\/.test(path)) return fallback
  if (/[\s:]/.test(path.slice(1).split('?')[0] || '')) {
    const base = path.split('?')[0] || '/'
    if (base.includes(':')) return fallback
  }
  return path
}
