import DOMPurify from 'dompurify'

const DOCUMENT_TAGS = [
  'p', 'br', 'strong', 'em', 'u', 's', 'b', 'i', 'strike', 'span', 'div',
  'h1', 'h2', 'h3', 'h4',
  'ul', 'ol', 'li', 'a', 'img', 'blockquote',
  'table', 'thead', 'tbody', 'tr', 'th', 'td', 'hr',
]

const DOCUMENT_ATTR = [
  'href', 'src', 'alt', 'title', 'class', 'target', 'rel', 'colspan', 'rowspan', 'style',
]

let documentHookInstalled = false

function ensureDocumentHook() {
  if (documentHookInstalled) return
  documentHookInstalled = true
  DOMPurify.addHook('uponSanitizeAttribute', (_node, data) => {
    if (data.attrName !== 'style') return
    const style = String(data.attrValue || '')
    const allowed = style
      .split(';')
      .map((s) => s.trim())
      .filter((s) =>
        /^text-align\s*:\s*(left|center|right|justify)$/i.test(s)
        || /^text-indent\s*:\s*-?\d+(\.\d+)?em$/i.test(s)
        || /^margin(?:-(?:top|bottom))?\s*:\s*-?\d+(\.\d+)?(?:em|px)$/i.test(s),
      )
      .join('; ')
    if (allowed) data.attrValue = allowed
    else data.keepAttr = false
  })
}

/** 通用 CMS 富文本 */
export function sanitizeHtml(dirty: string | undefined | null): string {
  if (!dirty) return ''
  return DOMPurify.sanitize(dirty, {
    ALLOWED_TAGS: ['p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'h4', 'ul', 'ol', 'li', 'a', 'img', 'blockquote', 'table', 'thead', 'tbody', 'tr', 'th', 'td', 'hr'],
    ALLOWED_ATTR: ['href', 'src', 'alt', 'title', 'class', 'target', 'rel', 'colspan', 'rowspan'],
    ALLOW_DATA_ATTR: false,
    FORBID_TAGS: ['script', 'iframe', 'object', 'embed', 'form'],
  })
}

/** 文书编辑器/导出：保留 Quill 对齐 class 与 text-align */
export function sanitizeDocumentHtml(dirty: string | undefined | null): string {
  if (!dirty) return ''
  ensureDocumentHook()
  return DOMPurify.sanitize(dirty, {
    ALLOWED_TAGS: DOCUMENT_TAGS,
    ALLOWED_ATTR: DOCUMENT_ATTR,
    ALLOW_DATA_ATTR: false,
    FORBID_TAGS: ['script', 'iframe', 'object', 'embed', 'form'],
  })
}
