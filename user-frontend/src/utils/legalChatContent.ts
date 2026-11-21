import { marked } from 'marked'
import { sanitizeHtml } from './sanitizeHtml'

marked.setOptions({ breaks: true, gfm: true })

const REFER_PAREN_BLOCK = /<referInfo[^>]*>\s*\([\s\S]*?\)\s*<\/referInfo\w*>?/gi
const REFER_ARRAY_BLOCK = /<referInfo[^>]*>\s*\[[\s\S]*?\]\s*<\/referInfo\w*>?/gi
const REFER_ARRAY_OPEN = /<referInfo[^>]*>\s*\[[\s\S]*?(?:\]\s*(?:<\/referInfo\w*>?|$))/gi
const REFER_BLOCK = /<referInfo[^>]*>[\s\S]*?<\/referInfo\w*>?/gi
const REFER_BLOCK_LOOSE = /<referInfo[^>]*>[\s\S]*?<\/referInfo/gi
const REFER_OPEN_TAIL = /<referInfo[^>]*>[\s\S]*$/gi
const ORPHAN_REFER_TAG = /<\/?referInfo\w*>?/gi
const CITE_JSON_START = /\{\{?\s*\{?"type"\s*:\s*"(?:lawItem|case|law)"/gi
const CITE_JSON_ARRAY_START = /\[\s*\{\s*"type"\s*:\s*"(?:lawItem|case|law)"/gi
const JSON_FIELD_FRAGMENTS = [
  /,?\s*"(?:type|lawName|lawItemName|timeliness|lawItemId|caseNo|eContent|lawId|title|content)"\s*:\s*"[^"]*"/gi,
  /,?\s*"(?:type|lawName|lawItemName|timeliness|lawItemId|caseNo|eContent|lawId|title|content)"\s*:\s*[^,\s}]+/gi,
  /\w+":"[^"]*"(?=\s*[,，。)]|$)/gi,
]

function braceBlockEnd(text: string, openPos: number): number {
  if (openPos >= text.length || text[openPos] !== '{') return openPos
  let depth = 0
  let i = openPos
  let inStr: string | null = null
  let escape = false
  while (i < text.length) {
    const ch = text[i]
    if (inStr) {
      if (escape) escape = false
      else if (ch === '\\') escape = true
      else if (ch === inStr) inStr = null
      i++
      continue
    }
    if (ch === '"' || ch === "'") {
      inStr = ch
      i++
      continue
    }
    if (ch === '{') depth++
    else if (ch === '}') {
      depth--
      if (depth === 0) return i + 1
    }
    i++
  }
  return text.length
}

function stripCiteJsonArrayBlobs(text: string): string {
  let out = text
  CITE_JSON_ARRAY_START.lastIndex = 0
  let m = CITE_JSON_ARRAY_START.exec(out)
  while (m) {
    const start = m.index
    let depth = 0
    let end = start
    for (let i = start; i < out.length; i++) {
      if (out[i] === '[') depth++
      else if (out[i] === ']') {
        depth--
        if (depth === 0) {
          end = i + 1
          break
        }
      }
    }
    if (end <= start) {
      out = out.slice(0, m.index) + out.slice(m.index + m[0].length)
    } else {
      out = out.slice(0, start) + out.slice(end)
    }
    CITE_JSON_ARRAY_START.lastIndex = 0
    m = CITE_JSON_ARRAY_START.exec(out)
  }
  return out
}

function stripCiteJsonBlobs(text: string): string {
  let out = text
  CITE_JSON_START.lastIndex = 0
  let m = CITE_JSON_START.exec(out)
  while (m) {
    let start = m.index
    while (start > 0 && '({'.includes(out[start - 1])) start--
    const bracePos = out.indexOf('{', start)
    if (bracePos < 0) {
      out = out.slice(0, m.index) + out.slice(m.index + m[0].length)
      CITE_JSON_START.lastIndex = 0
      m = CITE_JSON_START.exec(out)
      continue
    }
    let end = braceBlockEnd(out, bracePos)
    while (end < out.length && /[)\s}]/.test(out[end])) {
      if (out[end] === ')') {
        end++
        break
      }
      if (out[end] === '}') {
        end++
        continue
      }
      if (/\s/.test(out[end])) {
        end++
        continue
      }
      break
    }
    out = out.slice(0, start) + out.slice(end)
    CITE_JSON_START.lastIndex = 0
    m = CITE_JSON_START.exec(out)
  }
  return out
}

function stripWikiLawCites(text: string, streaming = false): string {
  let out = text.replace(/\[\[([^\]]{1,200})\]\]\(\s*\{[\s\S]*?\}\s*\)/g, (_full, label: string) => `《${String(label).trim()}》`)
  if (streaming) {
    const open = out.lastIndexOf('[[')
    if (open >= 0 && !out.slice(open).includes(']]')) {
      out = out.slice(0, open)
    }
    const dangling = out.lastIndexOf('《')
    if (dangling >= 0 && !out.slice(dangling).includes('》') && out.length - dangling > 80) {
      out = out.slice(0, dangling)
    }
  }
  return out
}

/** 先展示结论，详细分析和法条原文放在可展开区域 */
export function splitLegalAnswer(text: string): { summary: string; detail: string } {
  const marker = '<<<DETAIL>>>'
  const raw = text || ''
  const mark = raw.indexOf(marker)
  let body = mark >= 0 ? raw.slice(0, mark).trim() : raw
  let appendix = mark >= 0 ? raw.slice(mark + marker.length).trim() : ''
  body = stripReferInfo(body, false)
  appendix = stripReferInfo(appendix, false)
  const cleaned = body
  if (!cleaned && !appendix) return { summary: '', detail: '' }
  const heading = cleaned.search(/\n(?:#{1,3}[ \t]*)?二、/)
  let summary = cleaned
  let detail = appendix
  if (heading >= 180) {
    summary = cleaned.slice(0, heading).trim()
    detail = [cleaned.slice(heading).trim(), appendix].filter(Boolean).join('\n\n')
  }
  if (!summary) summary = body || appendix
  if (detail.trim() === summary.trim()) detail = ''
  return { summary, detail }
}

export function readableLegalAnswer(text: string): string {
  const parts = splitLegalAnswer(text)
  return [parts.summary, parts.detail].filter(Boolean).join('\n\n')
}

function stripJsonFieldFragments(text: string): string {
  let out = text
  for (const pat of JSON_FIELD_FRAGMENTS) {
    out = out.replace(pat, '')
  }
  return out
}

/**
 * 去掉法睿 referInfo / 引用 JSON。
 * @param stripTrailingOpen 流式时为 true，去掉末尾未闭合 referInfo
 */
export function stripReferInfo(text: string, stripTrailingOpen = false): string {
  if (!text) return ''
  let out = text
  for (const pat of [REFER_PAREN_BLOCK, REFER_ARRAY_BLOCK, REFER_ARRAY_OPEN, REFER_BLOCK, REFER_BLOCK_LOOSE]) {
    out = out.replace(pat, '')
  }
  out = out.replace(ORPHAN_REFER_TAG, '')
  out = stripWikiLawCites(out, stripTrailingOpen)
  out = stripCiteJsonArrayBlobs(out)
  out = stripCiteJsonBlobs(out)
  out = stripJsonFieldFragments(out)
  if (stripTrailingOpen) {
    out = out.replace(REFER_OPEN_TAIL, '')
    out = stripCiteJsonArrayBlobs(out)
    out = stripCiteJsonBlobs(out)
    out = stripJsonFieldFragments(out)
  }
  out = out.replace(/\(\s*\)/g, '')
  out = out.replace(/\n{3,}/g, '\n\n')
  return out.trim()
}

function isTableRow(line: string): boolean {
  const t = line.trim()
  return t.startsWith('|') && t.includes('|', 1)
}

function isTableSeparator(line: string): boolean {
  return /^\|[\s\-:|]+\|$/.test(line.trim())
}

function tableColCount(row: string): number {
  const parts = row.trim().split('|')
  return Math.max(parts.length - 2, 0)
}

function makeTableSeparator(cols: number): string {
  return `|${Array(cols).fill(' --- ').join('|')}|`
}

/** 法睿常返回缺分隔行的 pipe 表格，补全为 GFM 表格以便 marked 解析 */
function normalizeMarkdownTables(text: string): string {
  const lines = text.split('\n')
  const out: string[] = []
  let i = 0
  while (i < lines.length) {
    if (!isTableRow(lines[i])) {
      out.push(lines[i])
      i++
      continue
    }
    const block: string[] = []
    while (i < lines.length && isTableRow(lines[i])) {
      block.push(lines[i])
      i++
    }
    if (block.length >= 2 && !isTableSeparator(block[1])) {
      const cols = tableColCount(block[0])
      if (cols > 0) block.splice(1, 0, makeTableSeparator(cols))
    }
    if (out.length && out[out.length - 1].trim() !== '') out.push('')
    out.push(...block)
    out.push('')
  }
  return out.join('\n')
}

/** 规范化法睿 Markdown：标题/分隔线/表格，避免完成后仍显示 ### 或 | 源码 */
export function normalizeLegalMarkdown(text: string): string {
  if (!text) return ''
  let out = text.replace(/\r\n/g, '\n')
  out = out.replace(/^(#{1,6})([^\s#])/gm, '$1 $2')
  out = out.replace(/([^\n])\n(#{1,6}\s)/g, '$1\n\n$2')
  out = out.replace(/([^\n])\n(\|[^\n]+\|)/g, '$1\n\n$2')
  out = out.replace(/\n-{3,}\n/g, '\n\n---\n\n')
  out = normalizeMarkdownTables(out)
  return out.replace(/\n{3,}/g, '\n\n').trim()
}

function normalizeLegalPlainText(text: string | null | undefined): string {
  if (text == null || text === undefined) return ''
  let out = String(text).trim()
  if (/^(null|undefined|none)$/i.test(out)) return ''
  out = out.replace(/\\r\\n/g, '\n').replace(/\\n/g, '\n').replace(/\\r/g, '\n').replace(/\\t/g, ' ')
  out = out.replace(/\r\n/g, '\n').replace(/\r/g, '\n')
  out = out.replace(/^(?:null\s*)+/i, '')
  out = out.replace(/[ \t]+\n/g, '\n')
  out = out.replace(/\n{3,}/g, '\n\n')
  return out.trim()
}

/** 法律检索摘要/条文展示：去除法睿 referInfo 与引用 JSON，并还原换行 */
export function formatLegalSearchText(text: string): string {
  const normalized = normalizeLegalPlainText(text)
  const cleaned = stripReferInfo(normalized, false)
  return cleaned.replace(/\n{3,}/g, '\n\n').trim()
}

/** Markdown → 安全 HTML，用于法律咨询气泡（流式/完成共用同一渲染链路） */
export function legalChatHtml(markdown: string, streaming = false): string {
  const cleaned = normalizeLegalMarkdown(stripReferInfo(markdown, streaming))
  if (!cleaned) return ''
  const html = marked.parse(cleaned, { async: false }) as string
  return sanitizeHtml(html)
}

/** 流式结论：补上未闭合的标记后再渲染，避免把 ###、** 当成正文 */
export function streamingLegalHtml(markdown: string): string {
  let text = markdown || ''
  const fences = text.match(/```/g)
  if (fences && fences.length % 2 === 1) text += '\n```'
  const bolds = text.match(/\*\*/g)
  if (bolds && bolds.length % 2 === 1) text += '**'
  return legalChatHtml(text, true)
}

const LAW_CITE_RE = /《([^《》\n]{2,120})》(第[一二三四五六七八九十百零\d]+条)?/g

function escapeHtmlText(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

function escapeHtmlAttr(text: string): string {
  return escapeHtmlText(text).replace(/'/g, '&#39;')
}

/** 将《法规名称》第X条 转为可点击引用（title 存 law::article，兼容 sanitizeHtml） */
function linkLawCitations(text: string): string {
  return text.replace(LAW_CITE_RE, (full, lawName: string, article?: string) => {
    const law = String(lawName || '').trim()
    const art = String(article || '').trim()
    const title = `${law}::${art}`
    return `<a href="#" class="ss-law-cite" title="${escapeHtmlAttr(title)}">${escapeHtmlText(full)}</a>`
  })
}

/** 法规/案例检索「智能回答」：Markdown + 法条引用链接 */
export function legalSearchInsightHtml(text: string, streaming = false): string {
  const cleaned = normalizeLegalMarkdown(stripReferInfo(text, streaming))
  if (!cleaned) return ''
  const linked = linkLawCitations(cleaned)
  const html = marked.parse(linked, { async: false }) as string
  return sanitizeHtml(html)
}
