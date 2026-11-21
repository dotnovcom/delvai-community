const REMEMBER_KEY = 'remember_login'

export interface RememberedLogin {
  phone: string
}

export function saveRememberedLogin(data: RememberedLogin): void {
  localStorage.setItem(REMEMBER_KEY, JSON.stringify({ phone: data.phone }))
}

export function loadRememberedLogin(): RememberedLogin | null {
  const raw = localStorage.getItem(REMEMBER_KEY)
  if (!raw) return null
  try {
    const data = JSON.parse(raw) as { phone?: string; password?: string }
    if (data.password) {
      localStorage.removeItem(REMEMBER_KEY)
    }
    if (data.phone) return { phone: data.phone }
  } catch {
    /* ignore */
  }
  return null
}

export function clearRememberedLogin(): void {
  localStorage.removeItem(REMEMBER_KEY)
}

export function hasRememberedLogin(): boolean {
  return !!loadRememberedLogin()
}
