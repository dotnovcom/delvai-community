/** 管理后台状态/枚举中文映射 */

export const contentStatusLabel: Record<string, string> = {
  draft: '草稿',
  published: '已发布',
}

export const activeStatusLabel: Record<string, string> = {
  active: '已启用',
  inactive: '已禁用',
}

export const conversationStatusLabel: Record<string, string> = {
  active: '进行中',
  archived: '已归档',
  deleted: '已删除',
}

export const contractReviewStatusLabel: Record<string, string> = {
  pending: '待处理',
  processing: '处理中',
  completed: '已完成',
  failed: '失败',
}

export const pushStatusLabel: Record<string, string> = {
  pending: '待发送',
  sending: '发送中',
  sent: '已送达',
  failed: '失败',
}

export const pushTargetTypeLabel: Record<string, string> = {
  user: '指定用户',
  tag: '标签',
  all: '全部用户',
  email_bound: '已绑定邮箱',
}

export const pushTypeLabel: Record<string, string> = {
  legal_news: '法律资讯',
  contract_expiry: '合同到期',
  system: '系统通知',
  order: '订单/支付',
}

export const contentCategoryLabel: Record<string, string> = {
  legal_news: '法律资讯',
  policy: '政策法规',
  announcement: '公告',
  guide: '指南',
}

export const bannerPositionLabel: Record<string, string> = {
  home: '首页',
  membership: '会员页',
}

export const launchSplashPlatformLabel: Record<string, string> = {
  'mp-weixin': '微信小程序',
  'mp-toutiao': '抖音小程序',
  h5: 'H5 浏览器',
  wechat_h5: '微信公众号 H5',
  'app-android': 'Android App',
  'app-ios': 'iOS App',
  'app-harmony': '鸿蒙 App',
}

export const launchSplashContentTypeLabel: Record<string, string> = {
  image: '图片',
  video: '视频',
  html: 'HTML',
}

/** 订单状态 */
export const orderStatusLabel: Record<string, string> = {
  pending: '待支付',
  paid: '已支付',
  cancelled: '已取消',
  refunded: '已退款',
}

/** 用户会员订阅状态 */
export const membershipStatusLabel: Record<string, string> = {
  active: '有效',
  expired: '已过期',
  cancelled: '已取消',
}

/** 用户账号状态 */
export const userAccountStatusLabel: Record<string, string> = {
  active: '正常',
  disabled: '禁用',
}

/** 企业主体状态 */
export const enterpriseStatusLabel: Record<string, string> = {
  active: '正常',
  suspended: '暂停',
}

/** 企业成员状态 */
export const enterpriseMemberStatusLabel: Record<string, string> = {
  active: '正常',
  pending: '待确认',
  removed: '已移除',
}

/** 企业成员角色 */
export const enterpriseRoleLabel: Record<string, string> = {
  owner: '所有者',
  admin: '管理员',
  member: '成员',
  viewer: '只读',
}

/** 企业业务数据状态（合同/账款/合规/知产/知识库等） */
export const enterpriseBusinessStatusLabel: Record<string, string> = {
  draft: '草稿',
  pending_review: '待审批',
  approved: '已批准',
  rejected: '已驳回',
  active: '生效中',
  expired: '已到期',
  terminated: '已终止',
  pending: '待处理',
  overdue: '已逾期',
  collected: '已收回',
  disputed: '有争议',
  completed: '已完成',
  expiring_soon: '即将到期',
  archived: '已归档',
}

/** 用户反馈状态 */
export const feedbackStatusLabel: Record<string, string> = {
  pending: '待处理',
  replied: '已回复',
  closed: '已关闭',
}

/** 律师咨询状态 */
export const lawyerConsultStatusLabel: Record<string, string> = {
  pending: '待处理',
  accepted: '已接单',
  completed: '已完成',
  cancelled: '已取消',
}

/** 对话类型 */
export const conversationTypeLabel: Record<string, string> = {
  chat: 'AI 对话',
  search: '法律检索',
  contract: '合同服务',
  document: '文书生成',
  analysis: '类案分析',
  lawyer: '律师咨询',
  voice: '语音',
  video: '视频',
}

/** Open API Key 状态 */
export const openApiKeyStatusLabel: Record<string, string> = {
  active: '启用',
  disabled: '禁用',
}

/** 钱包流水类型 */
export const walletTxTypeLabel: Record<string, string> = {
  recharge: '充值入账',
  membership_pay: '会员支付',
  order_hold_release: '订单释放',
  order_refund: '订单退款',
  recharge_refund: '充值退款',
  refund_clawback: '退款扣回',
  consume: '服务消费',
  billing_rollback: '计费回退',
  admin_adjust: '管理员调整',
}

/** 积分流水类型 */
export const pointsTxTypeLabel: Record<string, string> = {
  grant: '积分获取',
  consume: '积分消耗',
  admin_adjust: '管理员调整',
  refund_clawback: '退款扣回',
}

export function labelOf(map: Record<string, string>, key: string, fallback?: string) {
  if (!key) return fallback ?? '—'
  return map[key] ?? fallback ?? key
}

export function memberStatusTagType(status: string): 'success' | 'info' | 'warning' | 'danger' {
  if (status === 'active') return 'success'
  if (status === 'pending') return 'warning'
  if (status === 'removed') return 'info'
  return 'info'
}

export function businessStatusTagType(status: string): 'success' | 'info' | 'warning' | 'danger' {
  if (['approved', 'active', 'collected', 'completed'].includes(status)) return 'success'
  if (['pending_review', 'pending', 'expiring_soon', 'overdue'].includes(status)) return 'warning'
  if (['rejected', 'terminated', 'disputed', 'expired', 'overdue'].includes(status)) return 'danger'
  return 'info'
}
