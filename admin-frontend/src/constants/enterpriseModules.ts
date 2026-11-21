export interface EnterpriseModule {
  key: string
  label: string
  icon: string
  desc: string
  accent?: string
}

export interface EnterpriseModuleGroup {
  key: string
  label: string
  desc: string
  moduleKeys: string[]
}

export const ENTERPRISE_MODULES: EnterpriseModule[] = [
  { key: 'contracts', label: '合同管理', icon: 'clipboard', desc: '全生命周期管理与审批', accent: '#2563eb' },
  { key: 'compliance', label: '合规中心', icon: 'check', desc: '清单生成与政策推送', accent: '#059669' },
  { key: 'notifications', label: '通知中心', icon: 'bell', desc: '合同、审批与合规提醒', accent: '#d97706' },
  { key: 'receivables', label: '账款管理', icon: 'wallet', desc: '诉讼时效与催收函', accent: '#ca8a04' },
  { key: 'ip', label: '知识产权', icon: 'copyright', desc: '商标专利到期监控', accent: '#7c3aed' },
  { key: 'knowledge', label: '知识库', icon: 'book-open', desc: '企业制度文档与智能问答', accent: '#0891b2' },
  { key: 'case-analysis', label: '类案分析', icon: 'chart-column', desc: '团队类案检索与深度报告', accent: '#4f46e5' },
  { key: 'sla', label: 'SLA 报表', icon: 'chart-line', desc: '订阅健康度与用量合规', accent: '#0d9488' },
  { key: 'brand', label: '白标设置', icon: 'palette', desc: '工作台品牌与主题色', accent: '#db2777' },
  { key: 'sso', label: '单点登录', icon: 'lock', desc: 'OIDC / 企微 / 钉钉 SSO', accent: '#475569' },
  { key: 'members', label: '团队管理', icon: 'users', desc: '邀请成员与权限配置', accent: '#1d4ed8' },
  { key: 'workflow', label: '审批配置', icon: 'gear', desc: '可配置审批流', accent: '#64748b' },
  { key: 'usage', label: '用量统计', icon: 'chart-column', desc: 'API 与审查用量监控', accent: '#0369a1' },
]

export const ENTERPRISE_MODULE_GROUPS: EnterpriseModuleGroup[] = [
  {
    key: 'core',
    label: '法务核心业务',
    desc: '合同、合规、账款与知产日常管理',
    moduleKeys: ['contracts', 'compliance', 'receivables', 'ip'],
  },
  {
    key: 'intel',
    label: '知识与智能分析',
    desc: '制度沉淀、类案检索与 AI 辅助决策',
    moduleKeys: ['knowledge', 'case-analysis'],
  },
  {
    key: 'collab',
    label: '协作与流程',
    desc: '通知、团队、审批与用量',
    moduleKeys: ['notifications', 'members', 'workflow', 'usage'],
  },
  {
    key: 'enterprise',
    label: '企业级能力',
    desc: 'SLA、白标、单点登录等企业服务',
    moduleKeys: ['sla', 'brand', 'sso'],
  },
]

export function enterpriseModuleLabel(key: string): string {
  return ENTERPRISE_MODULES.find((m) => m.key === key)?.label || key
}

export function enterpriseModuleByKey(key: string): EnterpriseModule | undefined {
  return ENTERPRISE_MODULES.find((m) => m.key === key)
}
