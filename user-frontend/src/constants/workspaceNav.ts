export interface WorkspaceNavItem {
  key: string
  icon: string
  label: string
  route: string
  tone: string
}

export const WORKSPACE_NAV: WorkspaceNavItem[] = [
  { key: 'ai', icon: 'comments', label: '咨询', tone: 'blue', route: '/chat/ai' },
]

export const WORKSPACE_META: Record<string, { title: string; icon: string; desc?: string }> = {
  ai: { title: '', icon: 'robot', desc: '智能法律咨询，支持深度思考与联网检索' },
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
