import { get, patch, post, getToken, BASE_URL } from '../utils/request'
import { parseFetchJsonResponse } from '../utils/error'
import { readSseStream } from '../utils/sseClient'
import { createWsTicket } from './auth'

export interface SearchResponse {
  total: number
  items: any[]
  query: string
  kind?: 'law' | 'case'
  ai_summary?: string
}

export interface SearchSummaryStreamBody {
  query: string
  kind: 'law' | 'case'
  total: number
  filters?: Record<string, unknown>
  items: Record<string, unknown>[]
  record_history?: boolean
}

export function searchRegulations(params: Record<string, unknown>) {
  const qs = new URLSearchParams(params as Record<string, string>).toString()
  return get<SearchResponse>(`/api/v1/search/regulations?${qs}`)
}

export function searchCases(params: Record<string, unknown>) {
  const qs = new URLSearchParams(params as Record<string, string>).toString()
  return get<SearchResponse>(`/api/v1/search/cases?${qs}`)
}

export async function streamSearchSummary(
  body: SearchSummaryStreamBody,
  callbacks: {
    onToken?: (chunk: string) => void
    onDone?: (content: string) => void
    onError?: (msg: string) => void
  },
  options?: { signal?: AbortSignal },
) {
  const token = getToken()
  try {
    const response = await fetch(`${BASE_URL}/api/v1/search/summary/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'text/event-stream',
        Authorization: `Bearer ${token}`,
        'Cache-Control': 'no-cache',
      },
      body: JSON.stringify(body),
      signal: options?.signal,
    })
    await readSseStream<{ type: string }, { type: string; content?: string }>(
      response,
      {
        onToken: callbacks.onToken,
        onDone: (event) => callbacks.onDone?.(event.content || ''),
        onError: callbacks.onError,
      },
      (payload) => JSON.parse(payload),
    )
  } catch (e) {
    if ((e as Error).name === 'AbortError') return
    callbacks.onError?.((e as Error).message || '网络错误')
  }
}

export function generateDocument(docType: string, params: Record<string, unknown>) {
  return post<{
    id: number
    doc_type: string
    title: string
    content: string
    file_url?: string
  }>('/api/v1/documents/generate', { doc_type: docType, params })
}

export function updateMyDocument(
  id: number,
  data: { title?: string; content?: string; params?: Record<string, unknown> },
) {
  return patch<{
    id: number
    doc_type: string
    title: string
    content: string
    file_url?: string
    params?: Record<string, unknown>
  }>(`/api/v1/documents/mine/${id}`, data)
}

import type { DocumentFieldDef } from '../types/documentForm'

export interface DocumentTypesResponse {
  categories: { category: string; types: string[] }[]
  field_hints: Record<string, string[]>
  field_labels?: Record<string, string>
  field_defs?: Record<string, DocumentFieldDef>
  field_defs_by_type?: Record<string, Record<string, DocumentFieldDef>>
  field_layout?: Record<string, string[][]>
}

export function listDocumentTypes() {
  return get<DocumentTypesResponse>('/api/v1/documents/types')
}

export function reviewContract(file: File, position = '0') {
  const form = new FormData()
  form.append('file', file)
  form.append('position', position)
  return fetch(`${BASE_URL}/api/v1/contracts/review`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${getToken()}` },
    body: form,
  }).then((r) => parseFetchJsonResponse(r, '合同审查失败'))
}

export interface ContractExtractField {
  extract_item: string
  desc?: string
  option?: string[]
}

export interface ContractExtractResultItem {
  extract_item?: string
  extractItem?: string
  desc?: string
  value?: string
  display_value?: string
  extract_value?: string
  original_text?: string
  raw_value?: unknown
}

export interface ContractExtractResponse {
  id?: number
  contract_text?: string
  extract_result?: ContractExtractResultItem[]
  file_oss_url?: string
}

export function extractContract(
  file: File,
  fields: ContractExtractField[] = [],
): Promise<ContractExtractResponse> {
  const form = new FormData()
  form.append('file', file)
  form.append('body', JSON.stringify({ fields }))
  return fetch(`${BASE_URL}/api/v1/contracts/extract`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${getToken()}` },
    body: form,
  }).then((r) => parseFetchJsonResponse<ContractExtractResponse>(r, '合同抽取失败'))
}

function parseContentDispositionFilename(header: string | null): string {
  if (!header) return 'contract-修订版.docx'
  const utf8 = /filename\*=UTF-8''([^;]+)/i.exec(header)
  if (utf8?.[1]) {
    try {
      return decodeURIComponent(utf8[1])
    } catch {
      return utf8[1]
    }
  }
  const plain = /filename="?([^";]+)"?/i.exec(header)
  return plain?.[1] || 'contract-修订版.docx'
}

export async function exportRevisedContractDocx(options: {
  reviewId?: number
  file?: File | null
  contractText?: string
  annotations?: unknown[]
  revisionStatuses?: Record<string, string>
}): Promise<{ blob: Blob; filename: string; applied: string[]; skipped: string[] }> {
  const token = getToken()
  let response: Response

  if (options.reviewId) {
    response = await fetch(`${BASE_URL}/api/v1/contracts/reviews/mine/${options.reviewId}/export-docx`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ revision_statuses: options.revisionStatuses || {} }),
    })
  } else if (options.file) {
    const form = new FormData()
    form.append('file', options.file)
    form.append('contract_text', options.contractText || '')
    form.append('annotations', JSON.stringify(options.annotations || []))
    form.append('revision_statuses', JSON.stringify(options.revisionStatuses || {}))
    response = await fetch(`${BASE_URL}/api/v1/contracts/export-revised-docx`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
      body: form,
    })
  } else {
    throw new Error('缺少可导出的合同文件')
  }

  if (!response.ok) {
    await parseFetchJsonResponse(response, '修订版 Word 导出失败')
  }

  const applied = (response.headers.get('X-Revision-Applied') || '')
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean)
  const skipped = (response.headers.get('X-Revision-Skipped') || '')
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean)
  const filename = parseContentDispositionFilename(response.headers.get('Content-Disposition'))
  const blob = await response.blob()
  return { blob, filename, applied, skipped }
}

export function createAnalysisReport(caseDescription: string) {
  return post('/api/v1/analysis/report', { case_description: caseDescription })
}

export interface CitationVerifyItem {
  citation: string
  type: string
  valid: boolean
  source: string
  matches: { title?: string; case_no?: string; source?: string }[]
}

export function verifyCitations(text: string) {
  return post<{
    total: number
    valid_count: number
    invalid_count: number
    items: CitationVerifyItem[]
  }>('/api/v1/legal/verify-citations', { text })
}

export interface VideoRoomInfo {
  room_id: string
  app_id: string
  token: string
  token_base64?: string | null
  nonce?: string | null
  expire_at: number
  user_id: string
  rtc_mode: string
  is_host?: boolean
  invite_code?: string | null
  invite_url?: string | null
  pc_invite_url?: string | null
  config: Record<string, unknown>
  lingjing: { avatar_id?: string; [key: string]: unknown }
  docs: string
  ws_url: string
}

export function createVideoRoom() {
  return post<VideoRoomInfo>('/api/v1/video/room')
}

export function joinVideoRoomByInvite(inviteCode: string) {
  return post<VideoRoomInfo>('/api/v1/video/room/join', { invite_code: inviteCode })
}

/** PC 工作台邀请路径（history 路由） */
export function buildVideoInvitePath(inviteCode: string) {
  return `/chat/multimodal?invite=${encodeURIComponent(inviteCode)}`
}

export function resolvePcInviteUrl(room: Pick<VideoRoomInfo, 'invite_code' | 'pc_invite_url'>) {
  if (room.pc_invite_url) return room.pc_invite_url
  if (!room.invite_code) return ''
  if (typeof window !== 'undefined' && window.location?.origin) {
    return `${window.location.origin}${buildVideoInvitePath(room.invite_code)}`
  }
  return buildVideoInvitePath(room.invite_code)
}

function wsBaseUrl() {
  let httpBase = String(BASE_URL || '').replace(/\/$/, '')
  if (!httpBase && typeof window !== 'undefined') httpBase = window.location.origin
  if (!httpBase) httpBase = 'http://localhost:8000'
  return httpBase.replace(/^http/i, 'ws')
}

export async function getVoiceWsUrl() {
  const { ticket } = await createWsTicket()
  return `${wsBaseUrl()}/ws/voice?ticket=${encodeURIComponent(ticket)}`
}

export async function getVideoWsUrl(roomId: string) {
  const { ticket } = await createWsTicket()
  return `${wsBaseUrl()}/ws/video/${encodeURIComponent(roomId)}?ticket=${encodeURIComponent(ticket)}`
}

export function recognizeFrame(file: File, question = '') {
  const form = new FormData()
  form.append('file', file)
  return fetch(`${BASE_URL}/api/v1/video/recognize-frame?question=${encodeURIComponent(question)}`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${getToken()}` },
    body: form,
  }).then((r) => r.json())
}

export function transcribeVoiceFile(file: File) {
  const form = new FormData()
  form.append('file', file)
  return fetch(`${BASE_URL}/api/v1/voice/transcribe`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${getToken()}` },
    body: form,
  }).then((r) => parseFetchJsonResponse<{ text: string; provider?: string }>(r, '语音识别失败'))
}

export function synthesizeSpeech(text: string) {
  return post<{ audio: string; mime_type: string; provider?: string }>('/api/v1/voice/synthesize', { text })
}

export function voiceTextReply(text: string) {
  return post<{
    text: string
    reply: string
    ai_engine: string
    tts_audio?: string
    tts_mime_type?: string
    tts_provider?: string
  }>('/api/v1/voice/reply', { text })
}

export interface DocumentReadParseResponse {
  id?: number
  contract_text: string
  contract_html?: string
  file_url: string
  file_name: string
  text_file_id?: string | null
}

export function parseReadDocument(file: File): Promise<DocumentReadParseResponse> {
  const form = new FormData()
  form.append('file', file)
  return fetch(`${BASE_URL}/api/v1/documents/read/parse`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${getToken()}` },
    body: form,
  }).then((r) => parseFetchJsonResponse<DocumentReadParseResponse>(r, '文档解析失败'))
}
