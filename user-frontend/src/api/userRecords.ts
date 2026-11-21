import { get, patch, del } from '../utils/request'

export interface ContractReviewDetail {
  id: number
  file_name: string
  file_url: string
  status: string
  summary: string
  risk_count: { high: number; medium: number; low: number }
  contract_text?: string
  contract_html?: string
  rules?: Record<string, unknown>[]
  annotations: {
    id: string
    risk_level: string
    category: string
    text: string
    suggestion: string
    explanation?: string
    match_text?: string
    revision_applicable?: boolean
  }[]
  position?: string
}

export interface PaginatedRecords<T> {
  total: number
  items: T[]
}

export interface MyDocumentItem {
  id: number
  doc_type: string
  title: string
  content_preview: string
  file_url?: string
  created_at: string
}

export interface MyDocumentDetail extends MyDocumentItem {
  params?: Record<string, unknown>
  content: string
}

export interface MyContractReviewItem {
  id: number
  file_name: string
  file_type: string
  status: string
  summary_preview: string
  risk_high: number
  risk_medium: number
  risk_low: number
  created_at: string
}

export interface MyContractExtractItem {
  id: number
  file_name: string
  field_count: number
  preview_field: string
  created_at: string
}

export interface MyContractExtractDetail {
  id: number
  file_name: string
  file_url?: string
  extract_result: Record<string, unknown>[]
  contract_text: string
  created_at: string
}

export interface MySearchHistoryItem {
  id: number
  kind: string
  kind_label: string
  query: string
  total: number
  ai_summary_preview?: string
  created_at: string
}

export interface MySearchHistoryDetail extends MySearchHistoryItem {
  filters?: Record<string, unknown>
  ai_summary?: string
  result_preview: { id?: string; title?: string; snippet?: string }[]
}

export function listMyDocuments(params?: { page?: number; size?: number; doc_type?: string }) {
  const qs = new URLSearchParams()
  if (params?.page) qs.set('page', String(params.page))
  if (params?.size) qs.set('size', String(params.size))
  if (params?.doc_type) qs.set('doc_type', params.doc_type)
  const q = qs.toString()
  return get<PaginatedRecords<MyDocumentItem>>(`/api/v1/documents/mine${q ? `?${q}` : ''}`)
}

export function getMyDocument(id: number) {
  return get<MyDocumentDetail>(`/api/v1/documents/mine/${id}`)
}

export function updateMyDocument(id: number, data: { title?: string; content?: string; params?: Record<string, unknown> }) {
  return patch<MyDocumentDetail>(`/api/v1/documents/mine/${id}`, data)
}

export function deleteMyDocument(id: number) {
  return del(`/api/v1/documents/mine/${id}`)
}

export interface MyDocumentReadItem {
  id: number
  file_name: string
  text_preview: string
  file_url?: string
  created_at: string
}

export interface MyDocumentReadDetail {
  id: number
  file_name: string
  file_url?: string
  contract_text: string
  contract_html?: string
  notes_html?: string
  conversation_id?: number | null
  created_at: string
}

export function listMyDocumentReads(params?: { page?: number; size?: number }) {
  const qs = new URLSearchParams()
  if (params?.page) qs.set('page', String(params.page))
  if (params?.size) qs.set('size', String(params.size))
  const q = qs.toString()
  return get<PaginatedRecords<MyDocumentReadItem>>(
    `/api/v1/documents/read/mine${q ? `?${q}` : ''}`,
  )
}

export function getMyDocumentRead(id: number) {
  return get<MyDocumentReadDetail>(`/api/v1/documents/read/mine/${id}`)
}

export function updateMyDocumentRead(
  id: number,
  data: { notes_html?: string; conversation_id?: number | null },
) {
  return patch<MyDocumentReadDetail>(`/api/v1/documents/read/mine/${id}`, data)
}

export function deleteMyDocumentRead(id: number) {
  return del(`/api/v1/documents/read/mine/${id}`)
}

export function listMyContractReviews(params?: { page?: number; size?: number }) {
  const qs = new URLSearchParams()
  if (params?.page) qs.set('page', String(params.page))
  if (params?.size) qs.set('size', String(params.size))
  const q = qs.toString()
  return get<PaginatedRecords<MyContractReviewItem>>(
    `/api/v1/contracts/reviews/mine${q ? `?${q}` : ''}`,
  )
}

export function getMyContractReview(id: number) {
  return get<ContractReviewDetail>(`/api/v1/contracts/reviews/mine/${id}`)
}

export function deleteMyContractReview(id: number) {
  return del(`/api/v1/contracts/reviews/mine/${id}`)
}

export function listMyContractExtracts(params?: { page?: number; size?: number }) {
  const qs = new URLSearchParams()
  if (params?.page) qs.set('page', String(params.page))
  if (params?.size) qs.set('size', String(params.size))
  const q = qs.toString()
  return get<PaginatedRecords<MyContractExtractItem>>(
    `/api/v1/contracts/extracts/mine${q ? `?${q}` : ''}`,
  )
}

export function getMyContractExtract(id: number) {
  return get<MyContractExtractDetail>(`/api/v1/contracts/extracts/mine/${id}`)
}

export function deleteMyContractExtract(id: number) {
  return del(`/api/v1/contracts/extracts/mine/${id}`)
}

export function listMySearchHistory(params?: {
  page?: number
  size?: number
  kind?: 'law' | 'case'
}) {
  const qs = new URLSearchParams()
  if (params?.page) qs.set('page', String(params.page))
  if (params?.size) qs.set('size', String(params.size))
  if (params?.kind) qs.set('kind', params.kind)
  const q = qs.toString()
  return get<PaginatedRecords<MySearchHistoryItem>>(
    `/api/v1/search/history/mine${q ? `?${q}` : ''}`,
  )
}

export function getMySearchHistory(id: number) {
  return get<MySearchHistoryDetail>(`/api/v1/search/history/mine/${id}`)
}

export interface MyAnalysisReportItem {
  id: number
  case_description_preview: string
  content_preview: string
  pdf_url?: string
  related_case_count: number
  created_at: string
}

export interface MyAnalysisReportDetail {
  id: number
  case_description: string
  content: string
  related_cases: Record<string, unknown>[]
  pdf_url?: string
  created_at: string
}

export function listMyAnalysisReports(params?: { page?: number; size?: number }) {
  const qs = new URLSearchParams()
  if (params?.page) qs.set('page', String(params.page))
  if (params?.size) qs.set('size', String(params.size))
  const q = qs.toString()
  return get<PaginatedRecords<MyAnalysisReportItem>>(
    `/api/v1/analysis/reports/mine${q ? `?${q}` : ''}`,
  )
}

export function getMyAnalysisReport(id: number) {
  return get<MyAnalysisReportDetail>(`/api/v1/analysis/reports/mine/${id}`)
}

export type UserRecordKind = 'documents' | 'reviews' | 'extracts' | 'read' | 'search' | 'analysis'
