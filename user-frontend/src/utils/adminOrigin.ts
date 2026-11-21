export function adminOrigin(): string {
  const raw = String(import.meta.env.VITE_ADMIN_ORIGIN || 'http://localhost:18090')
  return raw.replace(/\/$/, '')
}

export function adminUrl(path = '/admin'): string {
  const p = path.startsWith('/') ? path : `/${path}`
  return `${adminOrigin()}${p}`
}

export function openAdminConsole(path = '/admin'): void {
  window.open(adminUrl(path), '_blank', 'noopener,noreferrer')
}
