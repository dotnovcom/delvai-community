export function userOrigin(): string {
  const raw = String(import.meta.env.VITE_USER_ORIGIN || 'http://localhost:18080')
  return raw.replace(/\/$/, '')
}

export function openUserSite(path = '/'): void {
  const p = path.startsWith('/') ? path : `/${path}`
  window.open(`${userOrigin()}${p}`, '_blank', 'noopener,noreferrer')
}
