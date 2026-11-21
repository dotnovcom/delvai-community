import { get } from '../utils/request'

export interface PublicConfig {
  platform_name?: string
  ai_nav_label?: string
  logo_url?: string
  favicon_url?: string
  support_qr_url?: string
  wechat_official_qr_url?: string
  icp_number?: string
  police_icp_number?: string
  support_phone?: string
  support_email?: string
  company_address?: string
  site_title?: string
  site_keywords?: string
  site_description?: string
  og_image?: string
  pc_site_url?: string
  auth_login_phone_enabled?: string
  auth_login_phone_sms_enabled?: string
  auth_login_email_enabled?: string
  auth_login_email_sms_enabled?: string
  auth_login_wechat_enabled?: string
  auth_register_phone_enabled?: string
  auth_register_email_enabled?: string
  auth_require_phone_bind?: string
  auth_require_email_bind?: string
  /** 积分展示名称（billing 配置，全站只读） */
  points_display_name?: string
  [key: string]: string | undefined
}

export function getPublicConfig() {
  return get<PublicConfig>('/api/v1/config/public')
}

export interface NewsArticle {
  id: number
  title: string
  summary?: string
  category: string
  cover_url?: string
  published_at?: string
}

export interface NewsDetail extends NewsArticle {
  content: string
}

export function listNews(params?: { page?: number; size?: number; category?: string }) {
  const q = new URLSearchParams()
  if (params?.page) q.set('page', String(params.page))
  if (params?.size) q.set('size', String(params.size))
  if (params?.category) q.set('category', params.category)
  return get<{ total: number; items: NewsArticle[] }>(`/api/v1/cms/articles?${q}`)
}

export function listAnnouncements(size = 10) {
  return listNews({ page: 1, size, category: 'announcement' })
}

export function getNewsDetail(id: number) {
  return get<NewsDetail>(`/api/v1/cms/articles/${id}`)
}

export interface LegalPages {
  user_agreement: string
  privacy_policy: string
  /** 移动端设置「关于平台」；PC 注册/页脚可不使用 */
  about_platform?: string
  /** 移动端设置「联系我们」；PC 注册/页脚可不使用 */
  contact_us?: string
}

export const EMPTY_LEGAL_PAGES: LegalPages = {
  user_agreement: '',
  privacy_policy: '',
}

export function getLegalPages() {
  return get<LegalPages>('/api/v1/config/legal-pages')
}
