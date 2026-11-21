import { del, get, post } from '../utils/request'

export interface Plan {
  id: number
  name: string
  code: string
  level: number
  level_label?: string
  plan_type: string
  price: number
  original_price?: number
  duration_days: number
  description?: string
  features?: string[]
  quota?: Record<string, number>
  sort_order?: number
  audience: string
  billing_cycle: string
  billing_cycle_label?: string
}

export interface PlanLevelCycleBlock {
  key: string
  label: string
  months: number
  plans: Plan[]
}

export interface PlanLevelBlock {
  level: number
  level_label: string
  permissions: string[]
  cycles: PlanLevelCycleBlock[]
}

export interface PlanAudienceBlock {
  key: string
  label: string
  description: string
  levels: PlanLevelBlock[]
}

export interface PlansCatalog {
  audiences: PlanAudienceBlock[]
  billing_cycles: { key: string; label: string; months: number }[]
}

export interface UserMembership {
  level: number
  level_name: string
  level_label?: string
  plan_name?: string
  audience?: string
  billing_cycle?: string
  billing_cycle_label?: string
  expire_at?: string
  is_active: boolean
  features: string[]
  quota: Record<string, number>
}

export interface UsageQuotaItem {
  key: string
  label: string
  used: number
  limit: number | null
  remaining: number | null
  unlimited: boolean
  period: string
}

export interface UsageSummary {
  level: number
  level_name: string
  plan_name?: string
  items: UsageQuotaItem[]
}

export interface PrepayResponse {
  order_no: string
  amount: number
  platform: string
  prepay_params: Record<string, unknown>
  dev_confirm_url?: string
  paid?: boolean
  corporate?: boolean
  bank_info?: Record<string, string>
}

export function getPlans(params?: { audience?: string; billing_cycle?: string }) {
  const q = new URLSearchParams()
  if (params?.audience) q.set('audience', params.audience)
  if (params?.billing_cycle) q.set('billing_cycle', params.billing_cycle)
  const query = q.toString()
  return get<Plan[]>(`/api/v1/membership/plans${query ? `?${query}` : ''}`)
}

export function getPlansCatalog() {
  return get<PlansCatalog>('/api/v1/membership/plans/catalog')
}

export function getPerUsePlans(audience?: string) {
  const q = audience ? `?audience=${encodeURIComponent(audience)}` : ''
  return get<Plan[]>(`/api/v1/membership/plans/per-use${q}`)
}

export function getMyMembership() {
  return get<UserMembership>('/api/v1/membership/me')
}

export function getUsageSummary() {
  return get<UsageSummary>('/api/v1/membership/usage', { skipGlobalErrorHandler: true })
}

export function createOrder(
  planId: number,
  platform: string,
  payChannel: 'jsapi' | 'native' = 'jsapi',
  opts?: {
    points_to_use?: number
    balance_to_use?: number
    invoice_title?: string
    tax_id?: string
    invoice_email?: string
  },
) {
  return post<PrepayResponse>('/api/v1/payments/orders', {
    plan_id: planId,
    platform,
    pay_channel: payChannel,
    points_to_use: opts?.points_to_use ?? 0,
    balance_to_use: opts?.balance_to_use ?? 0,
    invoice_title: opts?.invoice_title,
    tax_id: opts?.tax_id,
    invoice_email: opts?.invoice_email,
  })
}

export interface OrderItem {
  order_no: string
  status: string
  amount: number
  platform: string
  plan_id: number
  plan_name: string
  paid_at?: string
  created_at: string
}

export function listMyOrders(params: { skip?: number; limit?: number; status?: string } = {}) {
  const qs = new URLSearchParams()
  if (params.skip != null) qs.set('skip', String(params.skip))
  if (params.limit != null) qs.set('limit', String(params.limit))
  if (params.status) qs.set('status', params.status)
  const query = qs.toString()
  return get<{ total: number; items: OrderItem[] }>(`/api/v1/payments/orders${query ? `?${query}` : ''}`)
}

export function getOrderStatus(orderNo: string) {
  return get<{ order_no: string; status: string }>(`/api/v1/payments/orders/${orderNo}`)
}

export function prepayOrder(
  orderNo: string,
  platform: string,
  payChannel: 'jsapi' | 'native' = 'native',
) {
  return post<PrepayResponse>(`/api/v1/payments/orders/${orderNo}/prepay`, {
    platform,
    pay_channel: payChannel,
  })
}

export function cancelOrder(orderNo: string) {
  return post<OrderItem>(`/api/v1/payments/orders/${orderNo}/cancel`)
}

export function deleteOrder(orderNo: string) {
  return del(`/api/v1/payments/orders/${orderNo}`)
}

export async function devConfirmPayment(orderNo: string) {
  return post(`/api/v1/payments/dev-confirm/${orderNo}`)
}
