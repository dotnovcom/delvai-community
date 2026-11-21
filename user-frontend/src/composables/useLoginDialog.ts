import { ref } from 'vue'
import { getToken } from '../utils/request'

export type AuthView = 'login' | 'register' | 'forgot'
export type LoginMethod = 'password' | 'phone' | 'email' | 'wechat'

const visible = ref(false)
const redirectPath = ref<string | undefined>()
const notice = ref('')
const authView = ref<AuthView>('login')
const loginMethod = ref<LoginMethod>('password')
const inviteCode = ref('')
let pending: ((ok: boolean) => void) | null = null

export function useLoginDialog() {
  return { visible, redirectPath, notice, authView, loginMethod, inviteCode }
}

export function setAuthView(
  view: AuthView,
  options?: { notice?: string; loginMethod?: LoginMethod },
) {
  authView.value = view
  if (options?.notice !== undefined) notice.value = options.notice
  loginMethod.value = options?.loginMethod ?? 'password'
}

export function openLoginDialog(options?: {
  redirect?: string
  notice?: string
  view?: AuthView
  invite?: string
  loginMethod?: LoginMethod
}): Promise<boolean> {
  if (getToken()) return Promise.resolve(true)
  if (visible.value && pending) {
    if (options?.redirect) redirectPath.value = options.redirect
    if (options?.notice) notice.value = options.notice
    if (options?.view) authView.value = options.view
    if (options?.invite) inviteCode.value = options.invite
    if (options?.loginMethod) loginMethod.value = options.loginMethod
    return new Promise((resolve) => {
      const prev = pending!
      pending = (ok) => {
        prev(ok)
        resolve(ok)
      }
    })
  }
  redirectPath.value = options?.redirect
  notice.value = options?.notice || ''
  authView.value = options?.view || 'login'
  inviteCode.value = options?.invite || ''
  loginMethod.value = options?.loginMethod || 'password'
  visible.value = true
  return new Promise((resolve) => {
    pending = resolve
  })
}

export function closeLoginDialog(success = false) {
  visible.value = false
  redirectPath.value = undefined
  notice.value = ''
  authView.value = 'login'
  loginMethod.value = 'password'
  inviteCode.value = ''
  pending?.(success)
  pending = null
}

export async function ensureLoggedIn(redirect?: string): Promise<boolean> {
  if (getToken()) return true
  return openLoginDialog({ redirect })
}
