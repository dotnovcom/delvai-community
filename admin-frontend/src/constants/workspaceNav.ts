export interface WorkspaceNavItem {
  key: string
  icon: string
  label: string
  route: string
  tone: string
}

export const WORKSPACE_NAV: WorkspaceNavItem[] = [
  { key: 'ai', icon: 'comments', label: '咨询', tone: 'blue', route: '/chat/ai' },
  { key: 'contract', icon: 'clipboard', label: '合同服务', tone: 'green', route: '/chat/contract' },
  { key: 'search', icon: 'magnifying-glass', label: '法律检索', tone: 'purple', route: '/chat/search' },
  { key: 'read', icon: 'book-open', label: '文本阅读', tone: 'teal', route: '/chat/read' },
  { key: 'document', icon: 'file-lines', label: '文书生成', tone: 'gold', route: '/chat/document' },
  { key: 'lawyer', icon: 'user-tie', label: '律师服务', tone: 'indigo', route: '/chat/lawyer' },
  { key: 'multimodal', icon: 'video', label: '语音视频', tone: 'green', route: '/chat/multimodal' },
  { key: 'enterprise', icon: 'building', label: '企业工作台', tone: 'slate', route: '/chat/enterprise' },
]

export const WORKSPACE_META: Record<string, { title: string; icon: string; desc?: string }> = {
  ai: { title: '', icon: 'robot', desc: '智能法律咨询，支持深度思考与联网检索' },
  contract: { title: '合同服务', icon: 'clipboard', desc: '合同审查 · 关键信息抽取' },
  search: { title: '法律检索', icon: 'magnifying-glass', desc: '法规与案例智能检索，AI 归纳摘要' },
  document: { title: '文书生成', icon: 'file-lines', desc: '多类型法律文书一键智能生成' },
  analysis: { title: '文本分析', icon: 'pen', desc: '案情描述与类案深度分析' },
  read: { title: '文本阅读', icon: 'book-open', desc: '上传起诉状、答辩状、笔录等，AI 辅助阅读' },
  lawyer: { title: '律师服务', icon: 'user-tie', desc: '专业律师在线咨询预约' },
  multimodal: { title: '语音视频', icon: 'video', desc: '多模态语音与视频法律咨询' },
  enterprise: { title: '企业工作台', icon: 'building', desc: '企业法务管理与合规仪表盘' },
}

export function resolveWorkspaceKey(path: string): string {
  if (path.startsWith('/research') || path.startsWith('/chat/search')) return 'search'
  if (path.startsWith('/chat/extract')) return 'contract'
  if (path.startsWith('/chat/read')) return 'read'
  if (path.startsWith('/chat/enterprise')) return 'enterprise'
  const seg = path.replace(/^\/chat\/?/, '').split('/')[0]
  if (seg && WORKSPACE_META[seg]) return seg
  return 'ai'
}
