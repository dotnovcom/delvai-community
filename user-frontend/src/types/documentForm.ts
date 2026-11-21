/** 文书录入字段定义（与后端 document_field_meta 一致） */

export type DocumentFieldWidget = 'text' | 'textarea' | 'date' | 'select' | 'number' | 'autocomplete'

export type DocumentFieldSpan = 'full' | 'half' | 'third'

export interface DocumentFieldDef {
  key: string
  label: string
  widget: DocumentFieldWidget
  span: DocumentFieldSpan
  options?: string[]
  allow_custom?: boolean
  placeholder?: string
  suffix?: string
  option_extras?: Record<string, {
    param_key: string
    label: string
    placeholder?: string
    suffix?: string
    span?: DocumentFieldSpan
  }>
}

export const SPAN_WIDTH: Record<DocumentFieldSpan, number> = {
  full: 12,
  half: 6,
  third: 4,
}

const TEXTAREA_KEYS = new Set([
  'claims', 'facts', 'content', 'clauses', 'defense', 'background',
  'property', 'children', 'support', 'evidence', 'request', 'opinion',
])

export function buildFormRows(
  fieldKeys: string[],
  fieldDefs: Record<string, DocumentFieldDef>,
): string[][] {
  const rows: string[][] = []
  let row: string[] = []
  let rowWidth = 0

  for (const key of fieldKeys) {
    const meta = fieldDefs[key]
    if (!meta) continue
    const w = SPAN_WIDTH[meta.span] ?? 12
    if (meta.widget === 'textarea') {
      if (row.length) rows.push(row)
      row = []
      rowWidth = 0
      rows.push([key])
      continue
    }
    if (rowWidth + w > 12) {
      if (row.length) rows.push(row)
      row = [key]
      rowWidth = w
    } else {
      row.push(key)
      rowWidth += w
    }
    if (rowWidth >= 12) {
      rows.push(row)
      row = []
      rowWidth = 0
    }
  }
  if (row.length) rows.push(row)
  return rows
}

export function fallbackFieldDef(key: string, label: string): DocumentFieldDef {
  const widget = TEXTAREA_KEYS.has(key) ? 'textarea' : 'text'
  return {
    key,
    label,
    widget,
    span: widget === 'textarea' ? 'full' : 'full',
  }
}
