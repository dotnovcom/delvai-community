import { get, post, put, setToken, removeToken, setRefreshToken, getRefreshToken, type AxiosRequestConfigWithErrorFlag } from '../utils/request'
import type {
  QrcodeCreateResponse,
  QrcodeStatusResponse,
  TokenResponse,
  UserInfo,
} from '../types/user'

export function phoneLogin(data: {
  phone: string
  login_type: 'sms' | 'password'
  code?: string
  password?: string
}) {
  return post<TokenResponse>('/api/v1/auth/phone-login', data, { skipGlobalErrorHandler: true })
}

export function adminLogin(data: {
  phone: string
  login_type: 'password'
  password: string
}) {
  return post<TokenResponse>('/api/v1/auth/admin-login', data, { skipGlobalErrorHandler: true })
}

export function emailLogin(data: {
  email: string
  login_type: 'sms' | 'password'
  code?: string
  password?: string
}) {
  return post<TokenResponse>('/api/v1/auth/email-login', data, { skipGlobalErrorHandler: true })
}

export function register(
  data: { phone: string; password: string; code: string; invite_code?: string },
  config?: AxiosRequestConfigWithErrorFlag,
) {
  return post<TokenResponse>('/api/v1/auth/register', data, config)
}

export function emailRegister(data: { email: string; password: string; code: string; invite_code?: string }) {
  return post<TokenResponse>('/api/v1/auth/email-register', data)
}

export function discoverEnterpriseSso(email: string) {
  return get<{ found: boolean; enterprise_id?: number; name?: string; email_domain?: string; provider?: string }>(
    `/api/v1/auth/enterprise-sso/discover?email=${encodeURIComponent(email)}`,
  )
}

export function listPublicEnterpriseSso() {
  return get<{ id: number; name: string; email_domain: string; provider: string }[]>(
    '/api/v1/auth/enterprise-sso/public',
  )
}

export function getEnterpriseSsoAuthorizeUrl(enterpriseId: number) {
  return get<{ authorize_url: string }>(`/api/v1/auth/enterprise-sso/${enterpriseId}/authorize`)
}

export function exchangeEnterpriseSsoCode(code: string) {
  return post<TokenResponse>('/api/v1/auth/enterprise-sso/exchange', { code })
}

export function checkPhoneRegistered(phone: string) {
  return get<{ registered: boolean }>(
    `/api/v1/auth/check-phone?phone=${encodeURIComponent(phone)}`,
    { skipGlobalErrorHandler: true },
  )
}

export function checkEmailRegistered(email: string) {
  return get<{ registered: boolean }>(
    `/api/v1/auth/check-email?email=${encodeURIComponent(email.trim())}`,
    { skipGlobalErrorHandler: true },
  )
}

export function sendSms(phone: string, purpose: 'login' | 'register' | 'reset_password' | 'bind_phone' = 'login') {
  return post<{ message: string; expire_seconds: number; debug_code?: string }>(
    '/api/v1/auth/send-sms',
    { phone, purpose },
  )
}

export function sendEmailCode(email: string, purpose: 'login' | 'register' | 'reset_password' | 'bind_email' = 'login') {
  return post<{ message: string; expire_seconds: number; debug_code?: string }>(
    '/api/v1/auth/send-email',
    { email, purpose },
  )
}

export function createWsTicket() {
  return post<{ ticket: string; expire_seconds: number }>('/api/v1/auth/ws-ticket')
}

export function getMe() {
  return get<UserInfo>('/api/v1/users/me')
}

export function updateMe(data: { nickname?: string; avatar?: string }) {
  return put<UserInfo>('/api/v1/users/me', data)
}

export function uploadAvatar(file: File) {
  const fd = new FormData()
  fd.append('file', file)
  return post<{ url: string; avatar?: string }>('/api/v1/users/me/avatar', fd)
}

export function createQrcode() {
  return post<QrcodeCreateResponse>('/api/v1/auth/qrcode/create')
}

export function getQrcodeStatus(ticket: string) {
  return get<QrcodeStatusResponse>(`/api/v1/auth/qrcode/status/${ticket}`)
}

export function saveAuthResult(result: TokenResponse) {
  setToken(result.access_token)
  setRefreshToken(result.refresh_token)
  localStorage.setItem('user_info', JSON.stringify(result.user))
}

export function clearAuth() {
  removeToken()
  localStorage.removeItem('user_info')
}

export function refreshAccessToken() {
  return post<TokenResponse>('/api/v1/auth/refresh', { refresh_token: getRefreshToken() })
}

export function resetPassword(data: { phone: string; code: string; new_password: string }) {
  return post<{ message: string }>('/api/v1/auth/reset-password', data)
}

export function resetPasswordByEmail(data: { email: string; code: string; new_password: string }) {
  return post<{ message: string }>('/api/v1/auth/reset-password-email', data)
}

export function bindPhone(data: { phone: string; code: string }) {
  return post<UserInfo>('/api/v1/users/me/bind-phone', data)
}

export function bindEmail(data: { email: string; code: string }) {
  return post<UserInfo>('/api/v1/users/me/bind-email', data)
}

export function createBindWechatTicket() {
  return post<{ ticket: string; expire_seconds: number; qrcode_url: string }>(
    '/api/v1/users/me/bind-wechat/ticket',
  )
}

export function getBindWechatStatus(ticket: string) {
  return get<{ status: 'pending' | 'confirmed' | 'expired' }>(
    `/api/v1/users/me/bind-wechat/status/${ticket}`,
  )
}

export function wechatBindConfirm(data: { code: string; ticket: string }) {
  return post<{ message: string }>('/api/v1/auth/wechat-bind', data)
}

export interface UserNotification {
  id: number
  title: string
  content: string
  category: string
  metadata?: Record<string, unknown> | null
  read_at?: string | null
  created_at: string
}

export function listNotifications(params?: {
  page?: number
  size?: number
  unread_only?: boolean
  category?: string
  category_prefix?: string
}) {
  const qs = new URLSearchParams()
  if (params?.page) qs.set('page', String(params.page))
  if (params?.size) qs.set('size', String(params.size))
  if (params?.unread_only) qs.set('unread_only', 'true')
  if (params?.category) qs.set('category', params.category)
  if (params?.category_prefix) qs.set('category_prefix', params.category_prefix)
  const q = qs.toString()
  return get<{ total: number; items: UserNotification[] }>(
    `/api/v1/users/me/notifications${q ? `?${q}` : ''}`,
  )
}

export function getUnreadNotificationCount(categoryPrefix?: string) {
  const q = categoryPrefix ? `?category_prefix=${encodeURIComponent(categoryPrefix)}` : ''
  return get<{ count: number }>(`/api/v1/users/me/notifications/unread-count${q}`)
}

export function markNotificationRead(id: number) {
  return post<{ message: string }>(`/api/v1/users/me/notifications/${id}/read`)
}

export function markAllNotificationsRead(categoryPrefix?: string) {
  const q = categoryPrefix ? `?category_prefix=${encodeURIComponent(categoryPrefix)}` : ''
  return post<{ message: string; count: number }>(`/api/v1/users/me/notifications/read-all${q}`)
}

export { getRefreshToken, setRefreshToken }

export function loadStoredUser(): UserInfo | null {
  const raw = localStorage.getItem('user_info')
  if (!raw) return null
  try {
    return JSON.parse(raw) as UserInfo
  } catch {
    return null
  }
}
