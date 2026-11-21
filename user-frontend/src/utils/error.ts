export interface ApiErrorDetail {
  code?: string
  message?: string
  quota_key?: string
  suggest_level?: string
  feature?: string
  required_level?: string
  current_level?: string
}

export class QuotaExceededError extends Error {
  override name = 'QuotaExceededError'
}

export const SESSION_REPLACED_CODE = 'SESSION_REPLACED'
export const SESSION_REPLACED_MESSAGE =
  '您已经在其它设备登录，如不是您本人登录，请至用户中心及时更改密码。'

export const SESSION_IDLE_EXPIRED_CODE = 'SESSION_IDLE_EXPIRED'
export const SESSION_IDLE_EXPIRED_MESSAGE = '登录已过期，请重新登录'

export function parseResponseDetail(detail: unknown, fallback = '请求失败'): string {
  if (typeof detail === 'string') return detail
  if (detail && typeof detail === 'object' && !Array.isArray(detail) && 'message' in detail) {
    return String((detail as ApiErrorDetail).message || fallback)
  }
  if (Array.isArray(detail)) {
    return detail.map((d: { msg?: string }) => d.msg).filter(Boolean).join('; ') || fallback
  }
  return fallback
}

export function parseApiErrorDetail(error: unknown): ApiErrorDetail | null {
  const detail = (error as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
  if (detail && typeof detail === 'object' && !Array.isArray(detail)) {
    return detail as ApiErrorDetail
  }
  return null
}

export function parseApiError(error: unknown): string {
  const data = (error as { response?: { data?: { detail?: unknown; message?: string } } })?.response?.data
  if (!data) return '请求失败'

  const parsed = parseResponseDetail(data.detail, '')
  if (parsed) return parsed
  if (data.message) return data.message
  return '请求失败'
}

/** 解析 fetch 响应；402 额度不足时触发全局弹窗并抛出 QuotaExceededError。 */
export async function parseFetchJsonResponse<T>(
  response: Response,
  fallback: string,
): Promise<T> {
  const data = (await response.json().catch(() => ({}))) as { detail?: unknown }
  if (!response.ok) {
    if (response.status === 402) {
      window.dispatchEvent(new CustomEvent('quota-exceeded', { detail: data.detail }))
      throw new QuotaExceededError(parseResponseDetail(data.detail, '额度已用完'))
    }
    throw new Error(parseResponseDetail(data.detail, fallback))
  }
  return data as T
}
