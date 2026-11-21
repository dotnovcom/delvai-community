import { legalChatHtml } from './legalChatContent'
import { sanitizeDocumentHtml } from './sanitizeHtml'

const QUILL_ALIGN_CSS = `
.ql-align-center { text-align: center; }
.ql-align-right { text-align: right; }
.ql-align-justify { text-align: justify; }
`

const PREVIEW_CSS = `
body { margin: 0; padding: 24px 32px; background: #fff; color: #1e293b;
  font-family: 'PingFang SC', 'Microsoft YaHei', 'Songti SC', serif; }
.doc-title { text-align: center; font-size: 22px; font-weight: 700; color: #1a365d;
  margin: 0 0 24px; letter-spacing: 0.02em; }
.doc-preview-markdown { font-size: 16px; line-height: 1.85; word-break: break-word; }
.doc-preview-markdown h1, .doc-preview-markdown h2, .doc-preview-markdown h3 {
  color: #1a365d; font-weight: 700; }
.doc-preview-markdown h1 { text-align: center; font-size: 22px; margin-top: 0; }
.doc-preview-markdown p { margin: 0.5em 0; text-indent: 2em; }
.doc-preview-markdown p:first-child { text-indent: 0; }
.doc-preview-markdown ul, .doc-preview-markdown ol { padding-left: 1.6em; }
.doc-preview-markdown li p { text-indent: 0; }
.doc-preview-markdown strong { font-weight: 700; }
.doc-preview-markdown blockquote { margin: 0.75em 0; padding: 0.5em 1em;
  border-left: 3px solid #d69e2e; background: #fffbeb; }
.doc-preview-markdown blockquote p { text-indent: 0; }
.doc-preview-markdown .doc-sign-block,
.doc-preview-markdown .doc-sign-line,
.doc-preview-markdown .ql-align-right {
  text-align: right !important;
  text-indent: 0 !important;
  margin-top: 0.35em;
  margin-bottom: 0.35em;
}
.doc-preview-markdown .doc-sign-block {
  margin-top: 2.5em;
  margin-bottom: 0.5em;
}
.doc-preview-markdown table { width: 100%; border-collapse: collapse; }
.doc-preview-markdown th, .doc-preview-markdown td {
  border: 1px solid #e2e8f0; padding: 8px 10px; }
${QUILL_ALIGN_CSS}
@media print {
  body { padding: 12mm 15mm; }
  .doc-title { page-break-after: avoid; }
}
`

function safeFilename(name: string) {
  return (name || '文书').replace(/[\\/:*?"<>|]/g, '_').slice(0, 80)
}

function isHtmlContent(content: string) {
  const t = content.trim()
  return t.startsWith('<') && /<\/\w+>/.test(t)
}

function normalizeTitleCompare(text: string): string {
  return text.replace(/\s+/g, '').replace(/[：:]/g, '').trim()
}

/** 两个标题是否指同一文书（如「起诉状」与「民事起诉状」） */
export function titlesMatch(a: string, b: string): boolean {
  const na = normalizeTitleCompare(a)
  const nb = normalizeTitleCompare(b)
  if (!na || !nb) return false
  if (na === nb) return true
  return na.includes(nb) || nb.includes(na)
}

function looksLikeDocumentHeading(line: string, docType?: string): boolean {
  const t = line.trim().replace(/^#+\s*/, '')
  if (!t || t.length > 24) return false
  if (/[：:（(]/.test(t)) return false
  if (/[状书条款函]$/.test(t) || /协议|合同|欠条|借条|声明|遗嘱|函/.test(t)) return true
  if (docType && titlesMatch(t, docType)) return true
  return t.length <= 8
}

/** 从正文首行提取文书名称（如「借条」「民事起诉状」） */
export function extractLeadingDocumentTitle(content: string, docType?: string): string {
  if (!content?.trim()) return ''

  if (isHtmlContent(content)) {
    const div = document.createElement('div')
    div.innerHTML = sanitizeDocumentHtml(content)
    for (const el of Array.from(div.children)) {
      const raw = (el.textContent || '').trim()
      if (!raw) continue
      const firstLine = raw.split(/\r?\n/)[0]?.trim() || ''
      if (firstLine && looksLikeDocumentHeading(firstLine, docType)) return firstLine
      break
    }
    return ''
  }

  for (const line of content.split(/\r?\n/)) {
    const t = line.trim()
    if (!t) continue
    if (looksLikeDocumentHeading(t, docType)) return t.replace(/^#+\s*/, '')
    break
  }
  return ''
}

/** 展示/导出用标题：去掉「借条-（请填写）」类后缀 */
export function displayDocumentTitle(title: string, docType?: string): string {
  const t = (title || '').trim()
  if (!t) return docType?.trim() || '文书'
  const dash = t.indexOf('-')
  if (dash > 0) {
    const head = t.slice(0, dash).trim()
    if (head) return head
  }
  return t
}

/** 解析最终展示标题：界面统一使用文书类型名，不从正文首行提取以免与 AI 标题冲突 */
export function resolveDocumentTitle(title: string, docType?: string, _content?: string): string {
  if (docType?.trim()) return docType.trim()
  const fromStored = displayDocumentTitle(title, docType)
  if (fromStored) return fromStored
  return '文书'
}

function titleCandidates(docTitle: string, docType?: string): string[] {
  const out: string[] = []
  const add = (v?: string) => {
    const t = v?.trim()
    if (t && !out.includes(t)) out.push(t)
  }
  add(docTitle)
  add(docType)
  add(displayDocumentTitle(docTitle, docType))
  return out
}

function shouldStripLeadingTitle(text: string, candidates: string[]): boolean {
  const norm = normalizeTitleCompare(text.replace(/^#+\s*/, ''))
  if (!norm) return false
  return candidates.some((c) => titlesMatch(norm, normalizeTitleCompare(c)))
}

function isParentheticalSubtitle(line: string): boolean {
  return /^（[^）]+）$/.test(line.trim())
}

const GENERIC_LITIGATION_HEADERS = new Set([
  '民事起诉状',
  '民事答辩状',
  '民事上诉状',
  '民事反诉状',
  '行政起诉状',
  '行政答辩状',
  '国家赔偿答辩状',
  '起诉状',
  '答辩状',
  '上诉状',
  '反诉状',
])

function isGenericLitigationHeader(line: string, docType?: string): boolean {
  const t = line.trim()
  if (!t) return false
  if (GENERIC_LITIGATION_HEADERS.has(t)) return true
  if (/^民事.+状$/.test(t)) return true
  if (docType?.endsWith('状') && t.endsWith('状') && t !== docType && (t.startsWith('民事') || t.startsWith('行政'))) {
    return true
  }
  return false
}

function shouldStripLeadingLine(line: string, candidates: string[], docType?: string): boolean {
  if (shouldStripLeadingTitle(line, candidates)) return true
  if (isParentheticalSubtitle(line)) return true
  if (isGenericLitigationHeader(line, docType)) return true
  if (docType && line.trim() === docType.trim()) return true
  return false
}

/** 去掉正文开头与文书名重复的标题行（编辑/导出/打印共用） */
export function stripLeadingDocumentTitle(content: string, docTitle: string, docType?: string): string {
  if (!content?.trim()) return content
  const candidates = titleCandidates(docTitle, docType)
  if (!candidates.length) return content

  if (isHtmlContent(content)) {
    const div = document.createElement('div')
    div.innerHTML = sanitizeDocumentHtml(content)
    let changed = true
    while (changed && div.firstElementChild) {
      changed = false
      const el = div.firstElementChild
      const tag = el.tagName.toLowerCase()
      const raw = (el.textContent || '').trim()
      if (!raw) {
        el.remove()
        changed = true
        continue
      }
      if (['h1', 'h2', 'h3', 'h4', 'p', 'div'].includes(tag)) {
        const lines = raw.split(/\r?\n/)
        let removeWhole = false
        while (lines.length) {
          const line = lines[0]?.trim() || ''
          if (!line) {
            lines.shift()
            continue
          }
          if (shouldStripLeadingLine(line, candidates, docType)) {
            lines.shift()
            removeWhole = true
            changed = true
            continue
          }
          break
        }
        if (removeWhole && lines.length === 0) {
          el.remove()
          continue
        }
        if (removeWhole && lines.length > 0) {
          el.textContent = lines.join('\n')
        }
      }
      break
    }
    return div.innerHTML.trim()
  }

  const lines = content.split(/\r?\n/)
  while (lines.length) {
    const line = lines[0]?.trim() || ''
    if (!line) {
      lines.shift()
      continue
    }
    if (shouldStripLeadingLine(line, candidates, docType)) {
      lines.shift()
      continue
    }
    break
  }
  return lines.join('\n').trimStart()
}

function prepareDocumentExport(title: string, content: string, docType?: string) {
  const displayTitle = resolveDocumentTitle(title, docType, content)
  const bodySource = stripLeadingDocumentTitle(content, displayTitle, docType)
  const bodyHtml = isHtmlContent(bodySource)
    ? sanitizeDocumentHtml(bodySource)
    : documentBodyHtml(bodySource)
  return { displayTitle, bodyHtml, bodySource }
}

/** 正文 HTML（不含标题） */
export function documentBodyHtml(content: string): string {
  if (!content?.trim()) return ''
  if (isHtmlContent(content)) return sanitizeDocumentHtml(content)
  return legalChatHtml(content)
}

/** Markdown/纯文本/HTML → 预览 HTML（可选含标题） */
export function documentPreviewHtml(content: string, title?: string, docType?: string): string {
  const displayTitle = title ? resolveDocumentTitle(title, docType, content) : ''
  const body = documentBodyHtml(stripLeadingDocumentTitle(content, displayTitle, docType))
  if (!body && !displayTitle) return ''
  if (displayTitle) {
    const t = displayTitle.replace(/</g, '&lt;').replace(/>/g, '&gt;')
    return `<h1 class="doc-title">${t}</h1>${body}`
  }
  return body
}

/** 列表摘要：去掉 HTML 标签 */
export function documentPlainPreview(content: string, limit = 160): string {
  if (!content?.trim()) return ''
  if (isHtmlContent(content)) return htmlToPlainText(content).slice(0, limit)
  return content.slice(0, limit)
}

function buildExportHtml(title: string, bodyHtml: string): string {
  const t = title.replace(/</g, '&lt;').replace(/>/g, '&gt;')
  return `<!DOCTYPE html>
<html xmlns:o="urn:schemas-microsoft-com:office:office"
 xmlns:w="urn:schemas-microsoft-com:office:word"
 xmlns="http://www.w3.org/TR/REC-html40">
<head><meta charset="utf-8"><title>${t}</title>
<!--[if gte mso 9]><xml><w:WordDocument><w:View>Print</w:View></w:WordDocument></xml><![endif]-->
<style>${PREVIEW_CSS}</style></head>
<body>
<h1 class="doc-title">${t}</h1>
<article class="doc-preview-markdown">${bodyHtml}</article>
</body></html>`
}

function triggerDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

function htmlToPlainText(content: string) {
  if (!content?.trim()) return ''
  if (!isHtmlContent(content)) return content
  const tmp = document.createElement('div')
  tmp.innerHTML = sanitizeDocumentHtml(content)
  return tmp.innerText || tmp.textContent || ''
}

/** 下载 TXT（原文；HTML 自动转纯文本，标题仅出现一次） */
export function downloadDocumentTxt(title: string, content: string, docType?: string) {
  const { displayTitle, bodySource } = prepareDocumentExport(title, content, docType)
  const text = htmlToPlainText(bodySource)
  const blob = new Blob([text ? `${displayTitle}\n\n${text}` : displayTitle], {
    type: 'text/plain;charset=utf-8',
  })
  triggerDownload(blob, `${safeFilename(displayTitle)}.txt`)
}

/** 导出 Word（.doc） */
export function downloadDocumentWord(title: string, content: string, docType?: string) {
  const { displayTitle, bodyHtml } = prepareDocumentExport(title, content, docType)
  if (!bodyHtml && !displayTitle.trim()) return false
  const html = buildExportHtml(displayTitle, bodyHtml)
  const blob = new Blob(['\ufeff', html], {
    type: 'application/msword;charset=utf-8',
  })
  triggerDownload(blob, `${safeFilename(displayTitle)}.doc`)
  return true
}

/** 浏览器打印（iframe，避免 popup 空白） */
export function printDocumentPreview(title: string, content: string, docType?: string) {
  const { displayTitle, bodyHtml } = prepareDocumentExport(title, content, docType)
  if (!bodyHtml && !displayTitle.trim()) return false
  const html = buildExportHtml(displayTitle || '文书', bodyHtml || '<p></p>')

  const iframe = document.createElement('iframe')
  iframe.setAttribute('title', 'print')
  Object.assign(iframe.style, {
    position: 'fixed',
    right: '0',
    bottom: '0',
    width: '0',
    height: '0',
    border: 'none',
    visibility: 'hidden',
  })
  document.body.appendChild(iframe)

  const win = iframe.contentWindow
  const doc = iframe.contentDocument || win?.document
  if (!doc || !win) {
    iframe.remove()
    return false
  }

  doc.open()
  doc.write(html)
  doc.close()

  const cleanup = () => {
    setTimeout(() => iframe.remove(), 500)
  }

  const doPrint = () => {
    try {
      win.focus()
      win.print()
    } finally {
      cleanup()
    }
  }

  if (doc.readyState === 'complete') {
    setTimeout(doPrint, 300)
  } else {
    iframe.onload = () => setTimeout(doPrint, 300)
    setTimeout(doPrint, 800)
  }
  return true
}
