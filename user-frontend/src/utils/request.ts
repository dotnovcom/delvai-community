import axios, { type AxiosInstance, type AxiosRequestConfig, type AxiosResponse, type InternalAxiosRequestConfig } from 'axios'
import { ElMessage } from 'element-plus'
import {
  parseApiError,
  parseApiErrorDetail,
  type ApiErrorDetail,
  SESSION_REPLACED_CODE,
  SESSION_REPLACED_MESSAGE,
  SESSION_IDLE_EXPIRED_CODE,
  SESSION_IDLE_EXPIRED_MESSAGE,
} from './error'
import { openLoginDialog } from '../composables/useLoginDialog'
import { hardRedirectToLogin, isAdminPath } from './authRedirect'

const BASE_URL =
  import.meta.env.VITE_API_BASE_URL !== undefined && import.meta.env.VITE_API_BASE_URL !== ''
    ? import.meta.env.VITE_API_BASE_URL
    : import.meta.env.PROD
      ? ''
      : 'http://localhost:8000'
const TOKEN_KEY = 'access_token'
const REFRESH_KEY = 'refresh_token'

export function getToken(): string {
  return localStorage.getItem(TOKEN_KEY) || ''
}

function isJwtExpired(token: string, skewMs = 10_000): boolean {
  const parts = token.split('.')
  if (parts.length !== 3) return false
  try {
    const json = atob(parts[1].replace(/-/g, '+').replace(/_/g, '/'))
    const payload = JSON.parse(json) as { exp?: number }
    return typeof payload.exp === 'number' && payload.exp * 1000 <= Date.now() + skewMs
  } catch {
    return false
  }
}

export function getRefreshToken(): string {
  return localStorage.getItem(REFRESH_KEY) || ''
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
}

export function setRefreshToken(token: string): void {
  localStorage.setItem(REFRESH_KEY, token)
}

export function removeToken(): void {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(REFRESH_KEY)
}

let refreshing: Promise<boolean> | null = null
let sessionReplacedHandling = false

function isSessionReplaced(error: unknown): boolean {
  return parseApiErrorDetail(error)?.code === SESSION_REPLACED_CODE
}

function isSessionIdleExpired(error: unknown): boolean {
  return parseApiErrorDetail(error)?.code === SESSION_IDLE_EXPIRED_CODE
}

function handleSessionExpired(notice = SESSION_IDLE_EXPIRED_MESSAGE): void {
  removeToken()
  localStorage.removeItem('user_info')
  const redirect = window.location.pathname + window.location.search
  if (isAdminPath()) {
    hardRedirectToLogin(redirect, 'session_expired')
    return
  }
  openLoginDialog({ redirect, notice })
}

function handleSessionReplaced(): void {
  if (sessionReplacedHandling) return
  sessionReplacedHandling = true
  removeToken()
  localStorage.removeItem('user_info')
  ElMessage.warning({
    message: SESSION_REPLACED_MESSAGE,
    duration: 5000,
  })
  if (isAdminPath()) {
    hardRedirectToLogin(window.location.pathname + window.location.search, 'other_device')
    return
  }
  openLoginDialog({ notice: SESSION_REPLACED_MESSAGE })
}

/** fetch 响应 401 且为其它设备登录时，与 axios 拦截器一致的处理 */
export async function handleFetchSessionReplaced(response: Response): Promise<boolean> {
  if (response.status !== 401) return false
  const err = await response.clone().json().catch(() => ({}))
  const detail = (err as { detail?: { code?: string } }).detail
  if (detail?.code !== SESSION_REPLACED_CODE) return false
  handleSessionReplaced()
  return true
}

async function tryRefreshToken(): Promise<boolean> {
  const refreshToken = getRefreshToken()
  if (!refreshToken) return false
  if (!refreshing) {
    refreshing = axios
      .post(`${BASE_URL}/api/v1/auth/refresh`, { refresh_token: refreshToken })
      .then((resp) => {
        setToken(resp.data.access_token)
        setRefreshToken(resp.data.refresh_token)
        if (resp.data.user) {
          localStorage.setItem('user_info', JSON.stringify(resp.data.user))
        }
        return true
      })
      .catch((err) => {
        if (isSessionIdleExpired(err)) {
          handleSessionExpired()
        }
        return false
      })
      .finally(() => {
        refreshing = null
      })
  }
  return refreshing
}

const instance: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

export interface AxiosRequestConfigWithErrorFlag extends AxiosRequestConfig {
  skipGlobalErrorHandler?: boolean
}

type InternalConfig = InternalAxiosRequestConfig & { skipGlobalErrorHandler?: boolean; _retry?: boolean }

instance.interceptors.request.use(
  async (config) => {
    let token = getToken()
    if (token && isJwtExpired(token)) {
      const refreshed = await tryRefreshToken()
      token = refreshed ? getToken() : ''
      if (!refreshed) {
        removeToken()
        localStorage.removeItem('user_info')
        return Promise.reject(new axios.CanceledError('access token expired'))
      }
    }
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    if (config.data instanceof FormData) {
      const headers = config.headers as Record<string, unknown> & {
        delete?: (key: string) => void
        setContentType?: (value: false) => void
      }
      if (typeof headers.setContentType === 'function') {
        headers.setContentType(false)
      } else if (typeof headers.delete === 'function') {
        headers.delete('Content-Type')
      } else {
        delete headers['Content-Type']
      }
    }
    return config
  },
  (error) => Promise.reject(error),
)

instance.interceptors.response.use(
  (response: AxiosResponse) => response.data,
  async (error) => {
    const status = error.response?.status
    const originalRequest = error.config as InternalConfig
    const message = parseApiError(error)

    if (status === 401 && isSessionReplaced(error)) {
      handleSessionReplaced()
    } else if (status === 401 && isSessionIdleExpired(error)) {
      handleSessionExpired()
    } else if (status === 401 && originalRequest && !originalRequest._retry) {
      originalRequest._retry = true
      const hadAccess = !!getToken()
      const hadRefresh = !!getRefreshToken()
      if (hadRefresh) {
        const refreshed = await tryRefreshToken()
        if (refreshed) {
          originalRequest.headers.Authorization = `Bearer ${getToken()}`
          return instance(originalRequest)
        }
      }
      if (!hadAccess && !hadRefresh) {
        return Promise.reject(error)
      }
      removeToken()
      if (isAdminPath()) {
        hardRedirectToLogin(window.location.pathname + window.location.search, 'session_expired')
        return Promise.reject(error)
      }
      const redirect = window.location.pathname + window.location.search
      openLoginDialog({ redirect, notice: '登录已过期，请重新登录' })
    } else if (status === 401) {
      removeToken()
      if (isAdminPath()) {
        hardRedirectToLogin(window.location.pathname + window.location.search, 'session_expired')
        return Promise.reject(error)
      }
      const redirect = window.location.pathname + window.location.search
      openLoginDialog({ redirect, notice: '登录已过期，请重新登录' })
    } else if (status === 402) {
      const detail = error.response?.data?.detail
      window.dispatchEvent(new CustomEvent('quota-exceeded', { detail }))
    } else if (status === 403) {
      const detail = error.response?.data?.detail
      const code = detail && typeof detail === 'object' ? (detail as ApiErrorDetail).code : ''
      if (code === 'MEMBERSHIP_REQUIRED' || code === 'ENTERPRISE_SUBSCRIPTION_REQUIRED') {
        window.dispatchEvent(new CustomEvent('membership-required', { detail }))
      } else if (!originalRequest?.skipGlobalErrorHandler) {
        ElMessage.error(typeof message === 'string' ? message : '请求失败')
      }
    } else if (!originalRequest?.skipGlobalErrorHandler) {
      ElMessage.error(typeof message === 'string' ? message : '请求失败')
    }

    return Promise.reject(error)
  },
)

export default instance

export function get<T = unknown>(url: string, config?: AxiosRequestConfigWithErrorFlag): Promise<T> {
  return instance.get(url, config) as Promise<T>
}

export function post<T = unknown>(
  url: string,
  data?: unknown,
  config?: AxiosRequestConfigWithErrorFlag,
): Promise<T> {
  return instance.post(url, data, config) as Promise<T>
}

export function put<T = unknown>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
  return instance.put(url, data, config) as Promise<T>
}

export function patch<T = unknown>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
  return instance.patch(url, data, config) as Promise<T>
}

export function del<T = unknown>(url: string, config?: AxiosRequestConfig): Promise<T> {
  return instance.delete(url, config) as Promise<T>
}

export function request<T = unknown>(config: AxiosRequestConfig): Promise<T> {
  return instance(config) as Promise<T>
}

export { BASE_URL }
