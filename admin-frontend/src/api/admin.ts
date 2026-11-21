import { del, get, patch, post, put } from '../utils/request'

export interface DashboardStats {
  user_total: number
  user_active: number
  user_new_week: number
  conversation_total: number
  enterprise_total: number
  order_total: number
  order_paid: number
  revenue_total: number
  membership_active: number
  search_total_7d?: number
  search_es_hits_7d?: number
  search_farui_calls_7d?: number
  search_indexed_7d?: number
  search_es_hit_rate_7d?: number
  ai_usage_7d?: { engine: string; label: string; messages: number; tokens: number }[]
}

export interface AdminUser {
  id: number
  phone?: string
  email?: string
  nickname?: string
  platform: string
  status: string
  is_admin: boolean
  is_verified?: boolean
  admin_role?: string
  created_at: string
  vip_label?: string
  vip_expire_at?: string
  balance?: number
  points?: number
  points_display_name?: string
}

export interface WalletSummary {
  balance: number
  points: number
  points_display_name: string
  points_expiring_soon?: number
}

export interface WalletTransactionItem {
  id: number
  type: string
  amount: number
  balance_after: number
  remark?: string
  created_at: string
}

export interface PointsLedgerItem {
  id: number
  type: string
  delta: number
  balance_after: number
  remark?: string
  created_at: string
}

export interface ContentArticle {
  id: number
  title: string
  summary?: string
  content: string
  category: string
  cover_url?: string
  status: string
  published_at?: string
  created_at: string
  updated_at: string
}

export interface PushTask {
  id: number
  title: string
  content: string
  target_type: string
  target_value?: string
  push_type: string
  status: string
  sent_count: number
  payload?: string
  sent_at?: string
  created_at: string
}

export function getAdminStats() {
  return get<DashboardStats>('/api/v1/admin/stats')
}

export interface IntegrationHealthItem {
  ok: boolean
  detail: string
  latency_ms?: number
  skipped?: boolean
}

export interface IntegrationsHealthResponse {
  ok: boolean
  ok_count: number
  total: number
  items: Record<string, IntegrationHealthItem>
}

export function getIntegrationsHealth() {
  return get<IntegrationsHealthResponse>('/api/v1/admin/integrations/health')
}

export interface TrendPoint {
  date: string
  users: number
  conversations: number
  orders: number
}

export interface MembershipSlice {
  name: string
  value: number
}

export interface DashboardCharts {
  trend: TrendPoint[]
  membership_distribution: MembershipSlice[]
  recent_orders: AdminOrder[]
}

export function getAdminCharts() {
  return get<DashboardCharts>('/api/v1/admin/stats/charts')
}

export interface UserDetail {
  id: number
  phone?: string
  email?: string
  is_verified?: boolean
  nickname?: string
  platform: string
  status: string
  is_admin: boolean
  admin_role?: string
  created_at: string
  conversation_count: number
  message_count: number
  vip_label?: string
  vip_expire_at?: string
  wallet: WalletSummary
  memberships: { plan_name: string; level: number; status: string; start_at: string; expire_at?: string }[]
  orders: { order_no: string; plan_name: string; amount: number; status: string; created_at: string }[]
  wallet_transactions?: WalletTransactionItem[]
  points_ledger?: PointsLedgerItem[]
}

export function getAdminUserDetail(id: number) {
  return get<UserDetail>(`/api/v1/admin/users/${id}`)
}

export function adjustAdminUserWallet(
  userId: number,
  data: {
    balance_delta?: number
    points_delta?: number
    validity_days?: number
    remark: string
  },
) {
  return post<WalletSummary>(`/api/v1/admin/users/${userId}/wallet/adjust`, data)
}

export function setAdminUserMembership(
  userId: number,
  data: { plan_id?: number; extend_days?: number; cancel?: boolean },
) {
  return patch<Record<string, unknown>>(`/api/v1/admin/users/${userId}/membership`, data)
}

export interface AuditLogItem {
  id: number
  user_id?: number
  operator_name?: string
  action: string
  action_label?: string
  resource: string
  resource_label?: string
  resource_id?: string
  summary?: string
  detail?: Record<string, unknown>
  ip?: string
  created_at: string
}

export function listAuditLogs(params: {
  page?: number
  size?: number
  keyword?: string
  action?: string
  resource?: string
} = {}) {
  const q = new URLSearchParams()
  q.set('page', String(params.page ?? 1))
  q.set('size', String(params.size ?? 20))
  if (params.keyword) q.set('keyword', params.keyword)
  if (params.action) q.set('action', params.action)
  if (params.resource) q.set('resource', params.resource)
  return get<{ total: number; items: AuditLogItem[] }>(`/api/v1/admin/audit-logs?${q}`)
}

export function deleteAuditLog(id: number) {
  return del(`/api/v1/admin/audit-logs/${id}`)
}

export function deleteAuditLogs(ids: number[]) {
  return post<{ message: string; deleted: number }>('/api/v1/admin/audit-logs/batch-delete', { ids })
}

export interface AdminConversation {
  id: number
  title: string
  user_id: number
  user_phone?: string
  user_nickname?: string
  interaction_type: string
  status: string
  message_count: number
  created_at: string
  updated_at: string
}

export interface AdminConversationDetail {
  id: number
  title: string
  user_id: number
  user_phone?: string
  interaction_type: string
  status: string
  created_at: string
  messages: {
    id: number
    role: string
    content_type: string
    content: string
    ai_engine?: string
    tokens_used?: number
    created_at: string
  }[]
}

export function listAdminConversations(params: {
  page?: number
  size?: number
  keyword?: string
  user_id?: number
  interaction_type?: string
  interaction_types?: string
} = {}) {
  const q = new URLSearchParams()
  q.set('page', String(params.page ?? 1))
  q.set('size', String(params.size ?? 20))
  if (params.keyword) q.set('keyword', params.keyword)
  if (params.user_id) q.set('user_id', String(params.user_id))
  if (params.interaction_type) q.set('interaction_type', params.interaction_type)
  if (params.interaction_types) q.set('interaction_types', params.interaction_types)
  return get<{ total: number; items: AdminConversation[] }>(`/api/v1/admin/conversations?${q}`)
}

export function getAdminConversationDetail(id: number) {
  return get<AdminConversationDetail>(`/api/v1/admin/conversations/${id}`)
}

export function updateAdminConversation(id: number, data: { title?: string; status?: string }) {
  return patch(`/api/v1/admin/conversations/${id}`, data)
}

export function deleteAdminConversation(id: number) {
  return del(`/api/v1/admin/conversations/${id}`)
}

export interface AiUsageSummary {
  total_tokens: number
  total_cost: number
  record_count: number
  user_count: number
}

export interface AdminAiUsageItem {
  id: number
  user_id: number
  user_phone?: string
  user_nickname?: string
  service_key: string
  service_label: string
  ai_engine: string
  ai_engine_label: string
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
  estimated_cost: number
  ref_type?: string
  ref_id?: string
  created_at?: string
}

export interface AdminAiUsageByUserItem {
  user_id: number
  user_phone?: string
  user_nickname?: string
  total_tokens: number
  total_cost: number
  call_count: number
}

function buildAiUsageQuery(params: {
  page?: number
  size?: number
  user_id?: number
  service_key?: string
  ai_engine?: string
  keyword?: string
  date_from?: string
  date_to?: string
} = {}) {
  const q = new URLSearchParams()
  q.set('page', String(params.page ?? 1))
  q.set('size', String(params.size ?? 20))
  if (params.user_id) q.set('user_id', String(params.user_id))
  if (params.service_key) q.set('service_key', params.service_key)
  if (params.ai_engine) q.set('ai_engine', params.ai_engine)
  if (params.keyword) q.set('keyword', params.keyword)
  if (params.date_from) q.set('date_from', params.date_from)
  if (params.date_to) q.set('date_to', params.date_to)
  return q
}

export function listAdminAiUsage(params: {
  page?: number
  size?: number
  user_id?: number
  service_key?: string
  ai_engine?: string
  keyword?: string
  date_from?: string
  date_to?: string
} = {}) {
  const q = buildAiUsageQuery(params)
  return get<{ total: number; items: AdminAiUsageItem[]; summary: AiUsageSummary }>(
    `/api/v1/admin/ai-usage?${q}`,
  )
}

export function listAdminAiUsageByUser(params: {
  page?: number
  size?: number
  user_id?: number
  service_key?: string
  ai_engine?: string
  keyword?: string
  date_from?: string
  date_to?: string
} = {}) {
  const q = buildAiUsageQuery(params)
  return get<{ total: number; items: AdminAiUsageByUserItem[]; summary: AiUsageSummary }>(
    `/api/v1/admin/ai-usage/by-user?${q}`,
  )
}

export function listAdminAiUsageServiceOptions() {
  return get<{ service_key: string; label: string }[]>('/api/v1/admin/ai-usage/service-options')
}

export function listAdminUsers(page = 1, size = 20, keyword?: string) {
  const q = new URLSearchParams({ page: String(page), size: String(size) })
  if (keyword) q.set('keyword', keyword)
  return get<{ total: number; items: AdminUser[] }>(`/api/v1/admin/users?${q}`)
}

export function updateAdminUser(
  id: number,
  data: Partial<Omit<AdminUser, 'phone' | 'email'>> & { phone?: string | null; email?: string | null },
) {
  return patch(`/api/v1/admin/users/${id}`, data)
}

export function resetAdminUserPassword(id: number, newPassword: string) {
  return post<{ message: string }>(`/api/v1/admin/users/${id}/password`, { new_password: newPassword })
}

export function listContent(page = 1, size = 20, status?: string, category?: string, excludeCategory?: string) {
  const q = new URLSearchParams({ page: String(page), size: String(size) })
  if (status) q.set('status', status)
  if (category) q.set('category', category)
  if (excludeCategory) q.set('exclude_category', excludeCategory)
  return get<{ total: number; items: ContentArticle[] }>(`/api/v1/admin/content?${q}`)
}

export function createContent(data: Partial<ContentArticle>) {
  return post<ContentArticle>('/api/v1/admin/content', data)
}

export function updateContent(id: number, data: Partial<ContentArticle>) {
  return patch<ContentArticle>(`/api/v1/admin/content/${id}`, data)
}

export function deleteContent(id: number) {
  return del(`/api/v1/admin/content/${id}`)
}

export function listPushTasks(page = 1, size = 20) {
  return get<{ total: number; items: PushTask[] }>(`/api/v1/admin/push?page=${page}&size=${size}`)
}

export function createPush(data: {
  title: string
  content: string
  target_type: string
  target_value?: string
  push_type?: string
  user_ids?: number[]
  channels?: string[]
}) {
  return post<PushTask>('/api/v1/admin/push', data)
}

export function previewPushCount(params: {
  target_type?: string
  target_value?: string
  user_ids?: number[]
} = {}) {
  const q = new URLSearchParams()
  q.set('target_type', params.target_type || 'all')
  if (params.target_value) q.set('target_value', params.target_value)
  if (params.user_ids?.length) q.set('user_ids', params.user_ids.join(','))
  return get<{ user_count: number; email_bound_count: number }>(`/api/v1/admin/push/preview-count?${q}`)
}

export function triggerContractReminders(days = 30) {
  return post(`/api/v1/admin/push/contract-reminders?days=${days}`)
}

export interface AdminPlan {
  id: number
  name: string
  code: string
  level: number
  plan_type: string
  audience: string
  billing_cycle: string
  price: number
  original_price?: number
  duration_days: number
  description?: string
  features?: string[]
  quota?: Record<string, number>
  status: string
  sort_order: number
  created_at: string
}

export interface SystemSetting {
  key: string
  value?: string
  category: string
  label?: string
  value_type: string
  is_secret?: boolean
  updated_at?: string
}

export interface AiProvider {
  id: number
  code: string
  name: string
  category: string
  description?: string
  api_key_masked: string
  api_secret_masked?: string
  has_api_key: boolean
  has_api_secret?: boolean
  base_url?: string
  extra_json?: string
  enabled: boolean
  daily_limit: number
  call_count_today: number
  updated_at?: string
}

export interface RolePermissions {
  roles: string[]
  modules: string[]
  actions: string[]
  matrix: Record<string, Record<string, string[]>>
}

export interface AdminOrder {
  order_no: string
  status: string
  amount: number
  platform: string
  original_amount?: number
  cash_amount?: number
  balance_used?: number
  points_used?: number
  points_yuan?: number
  pay_channel?: string
  payment_method?: string
  order_type?: string
  plan_name: string
  user_id: number
  user_phone?: string
  user_nickname?: string
  paid_at?: string
  created_at: string
  payment_mode?: string
  invoice_title?: string
  tax_id?: string
  invoice_email?: string
  invoice_status?: string
  bank_reference?: string
}

export function listAdminOrders(params: {
  page?: number
  size?: number
  status?: string
  keyword?: string
} = {}) {
  const q = new URLSearchParams()
  q.set('page', String(params.page ?? 1))
  q.set('size', String(params.size ?? 20))
  if (params.status) q.set('status', params.status)
  if (params.keyword) q.set('keyword', params.keyword)
  return get<{ total: number; items: AdminOrder[] }>(`/api/v1/admin/orders?${q}`)
}

export function updateAdminOrder(
  orderNo: string,
  data: {
    status?: 'cancelled' | 'refunded' | 'paid'
    invoice_status?: 'none' | 'requested' | 'issued'
    bank_reference?: string
  },
) {
  return patch(`/api/v1/admin/orders/${orderNo}`, data)
}

export function deleteAdminOrder(orderNo: string) {
  return del(`/api/v1/admin/orders/${orderNo}`)
}

export function listAdminPlans() {
  return get<AdminPlan[]>('/api/v1/admin/membership/plans')
}

export function createAdminPlan(data: Partial<AdminPlan>) {
  return post<AdminPlan>('/api/v1/admin/membership/plans', data)
}

export function updateAdminPlan(id: number, data: Partial<AdminPlan>) {
  return patch<AdminPlan>(`/api/v1/admin/membership/plans/${id}`, data)
}

export function deleteAdminPlan(id: number) {
  return del(`/api/v1/admin/membership/plans/${id}`)
}

export function listAdminSettings(category?: string) {
  const q = category ? `?category=${category}` : ''
  return get<SystemSetting[]>(`/api/v1/admin/settings${q}`)
}

export function updateAdminSettings(items: Partial<SystemSetting>[]) {
  return put<SystemSetting[]>('/api/v1/admin/settings', { items })
}

export interface PosterItem {
  id: string
  type: 'text' | 'qr' | 'avatar'
  bind?: string
  text?: string
  x: number
  y: number
  w?: number
  h?: number
  size: number
  color?: string
  bg?: string
  weight?: 'normal' | 'bold'
  italic?: boolean
}

export interface PosterLayout {
  width: number
  height: number
  background: string
  items: PosterItem[]
}

export function getReferralPoster() {
  return get<{ layout: PosterLayout; background_url: string }>('/api/v1/admin/referral-poster')
}

export function saveReferralPoster(layout: PosterLayout) {
  return put<{ layout: PosterLayout; background_url: string }>('/api/v1/admin/referral-poster', { layout })
}

export function previewReferralPoster(layout: PosterLayout) {
  return post<Blob>('/api/v1/admin/referral-poster/preview', { layout }, { responseType: 'blob' })
}

export function syncLegalPagesDefaults(options?: { keys?: string[]; force?: boolean }) {
  return post<{ updated_keys: string[]; count: number }>(
    '/api/v1/admin/settings/legal-pages/sync-defaults',
    options ?? {},
  )
}

export function uploadAdminFile(file: File) {
  const fd = new FormData()
  fd.append('file', file)
  return post<{ url: string }>('/api/v1/admin/upload', fd)
}

export function listAiProviders(category?: string) {
  const q = category ? `?category=${category}` : ''
  return get<AiProvider[]>(`/api/v1/admin/ai-providers${q}`)
}

export function updateAiProvider(id: number, data: Record<string, unknown>) {
  return patch<AiProvider>(`/api/v1/admin/ai-providers/${id}`, data)
}

export function testAiProvider(id: number) {
  return post<{ success: boolean; latency_ms: number; message: string }>(`/api/v1/admin/ai-providers/${id}/test`)
}

export function getAdminRoles() {
  return get<RolePermissions>('/api/v1/admin/roles')
}

export function updateAdminRoles(matrix: Record<string, Record<string, string[]>>) {
  return put<RolePermissions>('/api/v1/admin/roles', { matrix })
}

export interface AdminEnterprise {
  id: number
  name: string
  industry?: string
  credit_code?: string
  contact_name?: string
  contact_phone?: string
  owner_user_id: number
  owner_phone?: string
  owner_nickname?: string
  status: string
  member_count: number
  contract_count?: number
  compliance_count?: number
  created_at: string
  plan_id?: number
  plan_name?: string
  seat_limit?: number
  seats_used?: number
  subscription_expires_at?: string
  subscription_active?: boolean
  is_trial?: boolean
}

export function listAdminEnterprises(params: { page?: number; size?: number; keyword?: string; status?: string } = {}) {
  const q = new URLSearchParams()
  q.set('page', String(params.page ?? 1))
  q.set('size', String(params.size ?? 20))
  if (params.keyword) q.set('keyword', params.keyword)
  if (params.status) q.set('status', params.status)
  return get<{ total: number; items: AdminEnterprise[] }>(`/api/v1/admin/enterprises?${q}`)
}

export function getAdminEnterprise(id: number) {
  return get<AdminEnterprise>(`/api/v1/admin/enterprises/${id}`)
}

export function updateAdminEnterprise(
  id: number,
  data: {
    status?: string
    name?: string
    industry?: string
    credit_code?: string
    contact_name?: string
    contact_phone?: string
    seat_limit?: number
    subscription_expires_at?: string
    is_trial?: boolean
    grant_trial_days?: number
  },
) {
  return patch<AdminEnterprise>(`/api/v1/admin/enterprises/${id}`, data)
}

export function createAdminEnterprise(data: {
  name: string
  owner_phone: string
  industry?: string
  credit_code?: string
  contact_name?: string
  contact_phone?: string
  seat_limit?: number
  grant_trial_days?: number
}) {
  return post<AdminEnterprise>('/api/v1/admin/enterprises', data)
}

export function deleteAdminEnterprise(id: number) {
  return del<{ message: string }>(`/api/v1/admin/enterprises/${id}`)
}

export interface AdminEnterpriseMember {
  id: number
  user_id: number
  phone?: string
  nickname?: string
  role: string
  department?: string
  status: string
  joined_at?: string
  created_at: string
}

export interface AdminEnterpriseOverview {
  contract_total: number
  contract_pending: number
  contract_expiring: number
  receivable_total: number
  receivable_overdue: number
  compliance_count: number
  compliance_pending_items: number
  ip_total: number
  ip_alerts: number
  knowledge_docs: number
  case_analyses: number
  todo_count: number
  sla_score: number
  sla_summary: string
  subscription_active: boolean
  usage_metrics: {
    key: string
    label: string
    used: number
    total: number
    unit: string
    unlimited?: boolean
  }[]
}

export interface AdminEnterpriseModuleStat {
  key: string
  label: string
  count: number
  detail?: string
  status: string
}

export interface AdminEnterpriseConfig {
  sso_enabled: boolean
  sso_email_domain?: string
  sso_provider?: string
  department_isolation: boolean
  brand_display_name?: string
  brand_primary_color?: string
  brand_logo_url?: string
  workflow_step_count: number
  workflow_roles: string[]
}

export function getAdminEnterpriseOverview(id: number) {
  return get<AdminEnterpriseOverview>(`/api/v1/admin/enterprises/${id}/overview`)
}

export function listAdminEnterpriseMembers(id: number, params: { page?: number; size?: number } = {}) {
  const q = new URLSearchParams()
  q.set('page', String(params.page ?? 1))
  q.set('size', String(params.size ?? 50))
  return get<{ total: number; items: AdminEnterpriseMember[] }>(`/api/v1/admin/enterprises/${id}/members?${q}`)
}

export function getAdminEnterpriseModules(id: number) {
  return get<{ items: AdminEnterpriseModuleStat[] }>(`/api/v1/admin/enterprises/${id}/modules`)
}

export function getAdminEnterpriseConfig(id: number) {
  return get<AdminEnterpriseConfig>(`/api/v1/admin/enterprises/${id}/config`)
}

export function addAdminEnterpriseMember(
  id: number,
  data: { phone: string; role?: string; department?: string },
) {
  return post<AdminEnterpriseMember>(`/api/v1/admin/enterprises/${id}/members`, data)
}

export function updateAdminEnterpriseMember(
  enterpriseId: number,
  memberId: number,
  data: { role?: string; department?: string; status?: string },
) {
  return patch<AdminEnterpriseMember>(`/api/v1/admin/enterprises/${enterpriseId}/members/${memberId}`, data)
}

export function removeAdminEnterpriseMember(enterpriseId: number, memberId: number) {
  return del<{ message: string }>(`/api/v1/admin/enterprises/${enterpriseId}/members/${memberId}`)
}

export function updateAdminEnterpriseConfig(
  id: number,
  data: {
    department_isolation?: boolean
    sso_enabled?: boolean
    sso_email_domain?: string
    brand_display_name?: string
    brand_primary_color?: string
    brand_logo_url?: string
  },
) {
  return patch<AdminEnterpriseConfig>(`/api/v1/admin/enterprises/${id}/config`, data)
}

export function listAdminEnterpriseRecords(
  enterpriseId: number,
  module: string,
  params: { page?: number; size?: number } = {},
) {
  const q = new URLSearchParams()
  q.set('page', String(params.page ?? 1))
  q.set('size', String(params.size ?? 20))
  return get<{ total: number; module: string; items: Record<string, unknown>[] }>(
    `/api/v1/admin/enterprises/${enterpriseId}/records/${module}?${q}`,
  )
}

export function deleteAdminEnterpriseRecord(enterpriseId: number, module: string, recordId: number) {
  return del<{ message: string }>(`/api/v1/admin/enterprises/${enterpriseId}/records/${module}/${recordId}`)
}

export function listAllAdminEnterpriseRecords(
  module: string,
  params: { page?: number; size?: number; enterprise_id?: number; keyword?: string } = {},
) {
  const q = new URLSearchParams()
  q.set('page', String(params.page ?? 1))
  q.set('size', String(params.size ?? 20))
  if (params.enterprise_id) q.set('enterprise_id', String(params.enterprise_id))
  if (params.keyword) q.set('keyword', params.keyword)
  return get<{ total: number; module: string; items: Record<string, unknown>[] }>(
    `/api/v1/admin/enterprise-records/${module}?${q}`,
  )
}

export interface AdminLaunchSplash {
  id: number
  title: string
  platform: string
  enabled: boolean
  content_type: 'image' | 'video' | 'html'
  media_url?: string
  html_content?: string
  link_url?: string
  duration_sec: number
  allow_skip: boolean
  sort_order: number
  status: string
  start_at?: string
  end_at?: string
  created_at: string
  updated_at: string
}

export function listAdminLaunchSplash(page = 1, size = 20, platform?: string, status?: string) {
  const q = new URLSearchParams({ page: String(page), size: String(size) })
  if (platform) q.set('platform', platform)
  if (status) q.set('status', status)
  return get<{ total: number; items: AdminLaunchSplash[] }>(`/api/v1/admin/launch-splash?${q}`)
}

export function createAdminLaunchSplash(data: Partial<AdminLaunchSplash>) {
  return post<AdminLaunchSplash>('/api/v1/admin/launch-splash', data)
}

export function updateAdminLaunchSplash(id: number, data: Partial<AdminLaunchSplash>) {
  return patch<AdminLaunchSplash>(`/api/v1/admin/launch-splash/${id}`, data)
}

export function deleteAdminLaunchSplash(id: number) {
  return del(`/api/v1/admin/launch-splash/${id}`)
}

export interface AdminFeedback {
  id: number
  user_id?: number
  user_phone?: string
  user_nickname?: string
  category: string
  content: string
  contact?: string
  status: string
  admin_reply?: string
  replied_at?: string
  created_at: string
}

export function listAdminFeedbacks(params: { page?: number; size?: number; status?: string; keyword?: string } = {}) {
  const q = new URLSearchParams({ page: String(params.page ?? 1), size: String(params.size ?? 20) })
  if (params.status) q.set('status', params.status)
  if (params.keyword) q.set('keyword', params.keyword)
  return get<{ total: number; items: AdminFeedback[] }>(`/api/v1/admin/feedbacks?${q}`)
}

export function replyAdminFeedback(id: number, admin_reply: string) {
  return patch(`/api/v1/admin/feedbacks/${id}/reply`, { admin_reply })
}

export function updateAdminFeedbackStatus(id: number, status: string) {
  return patch(`/api/v1/admin/feedbacks/${id}/status`, { status })
}

export interface DocumentTemplate {
  id: number
  name: string
  category: string
  template_body: string
  field_schema?: string[]
  sort_order: number
  status: string
  created_at: string
  updated_at: string
}

export function listDocumentTemplateCategories() {
  return get<{ items: string[] }>('/api/v1/admin/document-template-categories')
}

export function listDocumentTemplates(page = 1, size = 50, category?: string) {
  const q = new URLSearchParams({ page: String(page), size: String(size) })
  if (category) q.set('category', category)
  return get<{ total: number; items: DocumentTemplate[] }>(`/api/v1/admin/document-templates?${q}`)
}

export function createDocumentTemplate(data: Partial<DocumentTemplate>) {
  return post<DocumentTemplate>('/api/v1/admin/document-templates', data)
}

export function updateDocumentTemplate(id: number, data: Partial<DocumentTemplate>) {
  return patch<DocumentTemplate>(`/api/v1/admin/document-templates/${id}`, data)
}

export function deleteDocumentTemplate(id: number) {
  return del(`/api/v1/admin/document-templates/${id}`)
}

export function syncDocumentTemplateCatalog() {
  return post<{
    added: number
    updated?: number
    catalog_types: number
    traffic_types_in_db: number
    traffic_types_in_catalog: number
    message: string
  }>('/api/v1/admin/document-templates/sync-catalog', {})
}

export interface AdminSearchLog {
  id: number
  kind: string
  query: string
  source: string
  es_hit_count: number
  farui_hit_count: number
  indexed_count: number
  latency_ms: number
  created_at: string
}

export function listAdminSearchLogs(params: {
  page?: number
  size?: number
  keyword?: string
  kind?: string
} = {}) {
  const q = new URLSearchParams({ page: String(params.page ?? 1), size: String(params.size ?? 20) })
  if (params.keyword) q.set('keyword', params.keyword)
  if (params.kind) q.set('kind', params.kind)
  return get<{ total: number; items: AdminSearchLog[] }>(`/api/v1/admin/legal/search-logs?${q}`)
}

export interface AdminSearchLogDetail extends AdminSearchLog {
  kind_label: string
  source_label: string
  sample_hits: { title: string; snippet: string; source: string }[]
}

export function getAdminSearchLog(id: number) {
  return get<AdminSearchLogDetail>(`/api/v1/admin/legal/search-logs/${id}`)
}

export function createAdminSearchLog(data: Partial<AdminSearchLog>) {
  return post<AdminSearchLogDetail>('/api/v1/admin/legal/search-logs', data)
}

export function updateAdminSearchLog(id: number, data: Partial<AdminSearchLog>) {
  return patch<AdminSearchLogDetail>(`/api/v1/admin/legal/search-logs/${id}`, data)
}

export function deleteAdminSearchLog(id: number) {
  return del(`/api/v1/admin/legal/search-logs/${id}`)
}

export interface AdminContractReview {
  id: number
  user_id: number
  user_phone?: string
  user_nickname?: string
  file_name: string
  file_type: string
  status: string
  risk_high?: number
  risk_medium?: number
  risk_low?: number
  created_at: string
  file_url?: string
  result?: Record<string, unknown>
}

export function listAdminContractReviews(params: {
  page?: number
  size?: number
  keyword?: string
  status?: string
} = {}) {
  const q = new URLSearchParams({ page: String(params.page ?? 1), size: String(params.size ?? 20) })
  if (params.keyword) q.set('keyword', params.keyword)
  if (params.status) q.set('status', params.status)
  return get<{ total: number; items: AdminContractReview[] }>(`/api/v1/admin/legal/contract-reviews?${q}`)
}

export function getAdminContractReview(id: number) {
  return get<AdminContractReview>(`/api/v1/admin/legal/contract-reviews/${id}`)
}

export function updateAdminContractReview(id: number, data: { status?: string; file_name?: string }) {
  return patch<AdminContractReview>(`/api/v1/admin/legal/contract-reviews/${id}`, data)
}

export function deleteAdminContractReview(id: number) {
  return del(`/api/v1/admin/legal/contract-reviews/${id}`)
}

export interface AdminGeneratedDoc {
  id: number
  user_id: number
  user_phone?: string
  user_nickname?: string
  doc_type: string
  title: string
  content_preview: string
  file_url?: string
  created_at: string
  params?: Record<string, unknown>
  content?: string
}

export function listAdminGeneratedDocs(params: {
  page?: number
  size?: number
  keyword?: string
  doc_type?: string
} = {}) {
  const q = new URLSearchParams({ page: String(params.page ?? 1), size: String(params.size ?? 20) })
  if (params.keyword) q.set('keyword', params.keyword)
  if (params.doc_type) q.set('doc_type', params.doc_type)
  return get<{ total: number; items: AdminGeneratedDoc[] }>(`/api/v1/admin/legal/generated-documents?${q}`)
}

export function getAdminGeneratedDoc(id: number) {
  return get<AdminGeneratedDoc>(`/api/v1/admin/legal/generated-documents/${id}`)
}

export function createAdminGeneratedDoc(data: {
  user_id: number
  doc_type: string
  title: string
  content?: string
}) {
  return post<AdminGeneratedDoc>('/api/v1/admin/legal/generated-documents', data)
}

export function updateAdminGeneratedDoc(
  id: number,
  data: { doc_type?: string; title?: string; content?: string },
) {
  return patch<AdminGeneratedDoc>(`/api/v1/admin/legal/generated-documents/${id}`, data)
}

export function deleteAdminGeneratedDoc(id: number) {
  return del(`/api/v1/admin/legal/generated-documents/${id}`)
}

export interface AdminLawyer {
  id: number
  name: string
  title?: string
  firm?: string
  specialties: string[]
  rating: number
  case_count: number
  avatar?: string
  intro?: string
  status: string
  created_at: string
}

export function listAdminLawyers(params: {
  page?: number
  size?: number
  keyword?: string
  status?: string
} = {}) {
  const q = new URLSearchParams({ page: String(params.page ?? 1), size: String(params.size ?? 20) })
  if (params.keyword) q.set('keyword', params.keyword)
  if (params.status) q.set('status', params.status)
  return get<{ total: number; items: AdminLawyer[] }>(`/api/v1/admin/legal/lawyers?${q}`)
}

export function createAdminLawyer(data: Partial<AdminLawyer>) {
  return post<AdminLawyer>('/api/v1/admin/legal/lawyers', data)
}

export function updateAdminLawyer(id: number, data: Partial<AdminLawyer>) {
  return patch<AdminLawyer>(`/api/v1/admin/legal/lawyers/${id}`, data)
}

export function deleteAdminLawyer(id: number) {
  return del(`/api/v1/admin/legal/lawyers/${id}`)
}

export interface AdminLawyerConsultation {
  id: number
  user_id: number
  user_phone?: string
  user_nickname?: string
  lawyer_id: number
  lawyer_name: string
  topic: string
  description?: string
  status: string
  scheduled_at?: string
  reply?: string
  created_at: string
}

export function listAdminLawyerConsultations(params: {
  page?: number
  size?: number
  keyword?: string
  status?: string
} = {}) {
  const q = new URLSearchParams({ page: String(params.page ?? 1), size: String(params.size ?? 20) })
  if (params.keyword) q.set('keyword', params.keyword)
  if (params.status) q.set('status', params.status)
  return get<{ total: number; items: AdminLawyerConsultation[] }>(`/api/v1/admin/legal/lawyer-consultations?${q}`)
}

export function createAdminLawyerConsultation(data: {
  user_id: number
  lawyer_id: number
  topic: string
  description?: string
  status?: string
}) {
  return post('/api/v1/admin/legal/lawyer-consultations', data)
}

export function updateAdminLawyerConsultation(
  id: number,
  data: { status?: string; reply?: string },
) {
  return patch(`/api/v1/admin/legal/lawyer-consultations/${id}`, data)
}

export function deleteAdminLawyerConsultation(id: number) {
  return del(`/api/v1/admin/legal/lawyer-consultations/${id}`)
}

export interface AiChatSetting {
  key: string
  value: string | null
  category: string
  label: string
  value_type: string
}

export function getAiChatSettings() {
  return get<AiChatSetting[]>('/api/v1/admin/settings?category=ai_chat')
}

export function saveAiChatSettings(items: { key: string; value: string; category: string; label: string; value_type: string }[]) {
  return put('/api/v1/admin/settings', { items })
}

export interface AdminMessageFeedback {
  id: number
  message_id: number
  user_id: number
  phone?: string | null
  nickname?: string | null
  vote: string
  content: string
  created_at: string
  updated_at: string
}

export interface AdminMessageShare {
  id: number
  token: string
  path: string
  message_id?: number | null
  user_id: number
  phone?: string | null
  nickname?: string | null
  question: string
  answer: string
  view_count: number
  created_at: string
}

export function listMessageFeedbacks(page = 1, size = 20, vote = '') {
  const q = new URLSearchParams({ page: String(page), size: String(size) })
  if (vote) q.set('vote', vote)
  return get<{ items: AdminMessageFeedback[]; total: number }>(`/api/v1/admin/chat-actions/feedbacks?${q}`)
}

export function listMessageShares(page = 1, size = 20) {
  return get<{ items: AdminMessageShare[]; total: number }>(
    `/api/v1/admin/chat-actions/shares?page=${page}&size=${size}`,
  )
}

export function deleteMessageShare(id: number) {
  return del(`/api/v1/admin/chat-actions/shares/${id}`)
}
