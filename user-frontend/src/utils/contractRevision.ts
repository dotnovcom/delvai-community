export type RevisionStatus = 'pending' | 'accepted' | 'rejected'

export interface ContractReviewAnnotation {
  id: string
  text: string
  suggestion: string
  explanation?: string
  result_type?: string | null
  revision_applicable?: boolean
  match_text?: string | null
  risk_level: string
  category: string
  page: number
  paragraph?: number
  start_offset?: number | null
  end_offset?: number | null
}

export function initRevisionStatuses(annotations: ContractReviewAnnotation[]): Record<string, RevisionStatus> {
  const map: Record<string, RevisionStatus> = {}
  for (const ann of annotations) {
    map[ann.id] = 'pending'
  }
  return map
}

/** 合同正文展示：统一换行，合并 docx 碎片化单字行（仅在初次入库时调用） */
export function normalizeContractText(text: string | null | undefined): string {
  if (text == null) return ''
  let out = String(text).trim()
  if (!out || /^(null|undefined|none)$/i.test(out)) return ''

  out = out
    .replace(/\\r\\n/g, '\n')
    .replace(/\\n/g, '\n')
    .replace(/\\r/g, '\n')
    .replace(/\\t/g, '\t')
  out = out.replace(/\r\n/g, '\n').replace(/\r/g, '\n')
  out = out.replace(/^(?:null\s*)+/i, '')
  out = out.replace(/[ \t]+\n/g, '\n')
  out = mergeConsecutiveShortLines(out)
  out = out.replace(/\n{3,}/g, '\n\n')
  return out.trim()
}

/** 合并连续短行（docx 每字一行 / 每字一段 → 正常横排） */
function mergeConsecutiveShortLines(text: string): string {
  // docx 解析可能产生「短行\n\n短行」，先压成单换行再合并
  const normalizedBreaks = text.replace(
    /([^\n\r]{1,4})\n\n+(?=[^\n\r]{1,4}(?:\n|$))/g,
    '$1\n',
  )

  const lines = normalizedBreaks.split('\n')
  const merged: string[] = []
  let shortBuf = ''
  let blankRun = 0

  const flushShort = () => {
    if (shortBuf) {
      merged.push(shortBuf)
      shortBuf = ''
    }
  }

  const isShortFragment = (s: string) => {
    const t = s.trim()
    if (!t) return false
    if (FIELD_LABEL_RE.test(t)) return false
    if (SIGN_FOOTER_RE.test(t) && t.length <= 12) return false
    if (t.length <= 2) return true
    if (t.length <= 4 && !/[。！？；!?;:：]$/.test(t)) return true
    return false
  }

  for (const raw of lines) {
    const trimmed = raw.trim()
    if (!trimmed) {
      blankRun += 1
      // 单空行：若正在合并短行碎片，跳过不 flush
      if (blankRun >= 2 || !shortBuf) {
        flushShort()
        merged.push('')
      }
      continue
    }
    blankRun = 0
    if (isShortFragment(trimmed)) {
      shortBuf += trimmed
    } else {
      flushShort()
      merged.push(trimmed)
    }
  }
  flushShort()

  const paragraphs: string[] = []
  let block: string[] = []
  for (const line of merged) {
    if (!line) {
      if (block.length) {
        paragraphs.push(block.join('\n'))
        block = []
      }
    } else {
      block.push(line)
    }
  }
  if (block.length) paragraphs.push(block.join('\n'))
  return paragraphs.join('\n\n')
}

const CLAUSE_HEADING_RE = /^第[一二三四五六七八九十百零\d]+条\s/
const CONTRACT_TITLE_HINT_RE = /(协议|合同|平台|合作)/
const SIGN_BLOCK_RE = /^(甲方|乙方)[：:]/
const FIELD_LABEL_RE = /^(甲方|乙方|法定代表人|地址|电话|邮箱|联系人|统一社会信用代码|开户银行|账号|签订时间|签署时间|日期)[：:]/
const SIGN_FOOTER_RE = /(盖章|签字|签署|签订|日期|年月日)/
const CLAUSE_NUM_RE = /第([一二三四五六七八九十百零\d]+)条/

const CN_DIGIT: Record<string, number> = { 零: 0, 一: 1, 二: 2, 三: 3, 四: 4, 五: 5, 六: 6, 七: 7, 八: 8, 九: 9 }

function chineseNumToInt(token: string): number | null {
  if (!token) return null
  if (/^\d+$/.test(token)) return parseInt(token, 10)
  if (token === '十') return 10
  if (token.startsWith('十')) return 10 + (chineseNumToInt(token.slice(1)) ?? 0)
  if (token.includes('十')) {
    const [left, right] = token.split('十')
    const tens = left ? (chineseNumToInt(left) ?? 0) : 1
    const ones = right ? (chineseNumToInt(right) ?? 0) : 0
    return tens * 10 + ones
  }
  if (token.length === 1 && token in CN_DIGIT) return CN_DIGIT[token]
  return null
}

export function parseClauseIndex(text: string): number | null {
  const m = CLAUSE_NUM_RE.exec(text || '')
  if (!m) return null
  return chineseNumToInt(m[1])
}

function annotationPositionInText(contractText: string, needle: string): number | null {
  const raw = needle?.trim()
  if (!raw || !contractText) return null
  const idx = contractText.indexOf(raw)
  if (idx >= 0) return idx
  const collapsed = raw.replace(/\s+/g, ' ')
  if (collapsed.length >= 8) {
    const idx2 = contractText.indexOf(collapsed)
    if (idx2 >= 0) return idx2
  }
  return null
}

/** 按合同正文从前到后的顺序排列风险项 */
export function sortAnnotationsByDocumentOrder(
  annotations: ContractReviewAnnotation[],
  contractText: string,
): ContractReviewAnnotation[] {
  return [...annotations].sort((a, b) => {
    const key = (ann: ContractReviewAnnotation, index: number) => {
      const pos = annotationPositionInText(contractText, ann.text)
      if (pos != null) return [0, pos] as const
      const clause = parseClauseIndex(ann.category) ?? parseClauseIndex(ann.text)
      if (clause != null) return [1, clause] as const
      return [2, ann.page ?? 0, ann.paragraph ?? 0, index] as const
    }
    const ka = key(a, annotations.indexOf(a))
    const kb = key(b, annotations.indexOf(b))
    for (let i = 0; i < Math.max(ka.length, kb.length); i += 1) {
      const va = ka[i] ?? 0
      const vb = kb[i] ?? 0
      if (va !== vb) return va < vb ? -1 : 1
    }
    return 0
  })
}

function isContractTitleParagraph(para: string, index: number): boolean {
  const t = para.replace(/\n/g, '').trim()
  if (!t || index > 2) return false
  if (t.length > 40) return false
  return CONTRACT_TITLE_HINT_RE.test(t) || (t.length <= 20 && !SIGN_BLOCK_RE.test(t))
}

function isClauseHeadingParagraph(para: string): boolean {
  const firstLine = para.split('\n')[0]?.trim() || ''
  return CLAUSE_HEADING_RE.test(firstLine)
}

function isSignBlockParagraph(para: string): boolean {
  const t = para.trim()
  return SIGN_BLOCK_RE.test(t) && t.length < 280
}

function isSignFieldParagraph(para: string): boolean {
  const t = para.trim()
  return FIELD_LABEL_RE.test(t) && !SIGN_BLOCK_RE.test(t) && t.length < 120
}

function isSignFooterParagraph(para: string): boolean {
  const t = para.trim()
  if (SIGN_BLOCK_RE.test(t)) return false
  return SIGN_FOOTER_RE.test(t) && t.length < 80
}

/** 将段落拆为行：支持表格遗留 tab、段内换行、同行多标签 */
function expandParagraphLines(para: string): string[] {
  const lines: string[] = []
  for (const row of para.split('\n')) {
    const parts = row.includes('\t') ? row.split('\t') : [row]
    for (const part of parts) {
      for (const piece of splitInlineSignLabels(part)) {
        for (const sub of splitInlineSignFooter(piece)) {
          const t = sub.trim()
          if (t) lines.push(t)
        }
      }
    }
  }
  return lines.length ? lines : (para.trim() ? [para.trim()] : [])
}

/** 同行出现「甲方：…乙方：…」时拆成独立行 */
function splitInlineSignLabels(line: string): string[] {
  const trimmed = line.trim()
  if (!trimmed) return []
  const matches = trimmed.match(/(甲方|乙方)[：:]/g)
  if (!matches || matches.length <= 1) return [trimmed]
  return trimmed.split(/(?=(?:甲方|乙方)[：:])/).map((s) => s.trim()).filter(Boolean)
}

/** 同行重复签章标签时拆分 */
function splitInlineSignFooter(line: string): string[] {
  const trimmed = line.trim()
  if (!trimmed) return []
  const re = /(签订时间|签订地点|签署时间|代表签字|法定代表人)[：:]/g
  const matches = trimmed.match(re)
  if (!matches || matches.length <= 1) return [trimmed]
  return trimmed.split(/(?=(?:签订时间|签订地点|签署时间|代表签字|法定代表人)[：:])/).map((s) => s.trim()).filter(Boolean)
}

function paragraphClass(line: string): string {
  if (isSignBlockParagraph(line)) return 'contract-sign-block'
  if (isSignFieldParagraph(line)) return 'contract-sign-field'
  if (isSignFooterParagraph(line)) return 'contract-sign-footer'
  if (isClauseHeadingParagraph(line)) return 'contract-clause-heading'
  return ''
}

function renderSignRow(left: string, right: string, escape: (s: string) => string): string {
  return (
    `<div class="contract-sign-row">`
    + `<span class="contract-sign-col">${escape(left).replace(/\n/g, '<br>')}</span>`
    + `<span class="contract-sign-col">${escape(right).replace(/\n/g, '<br>')}</span>`
    + `</div>`
  )
}

/** 合同纯文本 → HTML（输入应已 normalize，修订后不再二次 normalize） */
export function contractPlainToHtml(text: string): string {
  if (!text?.trim()) return ''
  const escape = (s: string) =>
    s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')

  const htmlParts: string[] = []
  const blocks = text.split(/\n\n+/).filter((p) => p.trim())

  for (let blockIndex = 0; blockIndex < blocks.length; blockIndex += 1) {
    const block = blocks[blockIndex]
    const lines = expandParagraphLines(block)

    if (lines.length === 1) {
      const line = lines[0]
      const inner = escape(line).replace(/\n/g, '<br>')
      if (isContractTitleParagraph(line, blockIndex)) {
        htmlParts.push(`<p class="contract-doc-title">${inner}</p>`)
        continue
      }
      const cls = paragraphClass(line)
      htmlParts.push(cls ? `<p class="${cls}">${inner}</p>` : `<p>${inner}</p>`)
      continue
    }

    for (let i = 0; i < lines.length; i += 1) {
      const line = lines[i]
      const next = lines[i + 1]
      const pairable =
        next
        && (
          (SIGN_BLOCK_RE.test(line) && SIGN_BLOCK_RE.test(next))
          || (
            isSignFooterParagraph(line)
            && isSignFooterParagraph(next)
            && line.replace(/[：:].*$/, '') === next.replace(/[：:].*$/, '')
          )
        )
      if (pairable) {
        htmlParts.push(renderSignRow(line, next, escape))
        i += 1
        continue
      }
      const inner = escape(line).replace(/\n/g, '<br>')
      const cls = paragraphClass(line)
      htmlParts.push(cls ? `<p class="${cls}">${inner}</p>` : `<p>${inner}</p>`)
    }
  }

  return htmlParts.join('')
}

const MIN_REVISION_MATCH_LEN = 8
const PARTY_INFO_RE = /^(甲方|乙方)[：:]|法定代表人|地址[：:]|电话[：:]|邮箱[：:]/
const CLAUSE_NUM_PREFIX_RE = /^(\d+(?:\.\d+)*)/

export function revisionNeedle(ann: ContractReviewAnnotation): string {
  return (ann.match_text || ann.text || '').trim()
}

function extractClausePrefix(text: string): string | null {
  const m = CLAUSE_NUM_PREFIX_RE.exec(text.trim())
  return m ? m[1] : null
}

/** 原文与修订文本是否成对（防止 1.4 原文配 1.5 建议、乙方信息配 2.5 条款） */
export function isRevisionPairConsistent(original: string, suggestion: string): boolean {
  const orig = original.trim()
  const next = suggestion.trim()
  if (!orig || !next) return false

  const oPrefix = extractClausePrefix(orig)
  const sPrefix = extractClausePrefix(next)
  if (oPrefix && sPrefix && oPrefix !== sPrefix) {
    const origIsHeadingOnly = /^[\d.]+\s*[\u4e00-\u9fa5]{0,8}[：:]\s*$/.test(orig)
    if (!origIsHeadingOnly) return false
  }

  if (PARTY_INFO_RE.test(orig) && CLAUSE_NUM_PREFIX_RE.test(next)) {
    return false
  }

  return true
}

/** 是否有足够信息展示 */
export function isDisplayableAnnotation(ann: ContractReviewAnnotation): boolean {
  const text = ann.text?.trim() || ''
  const suggestion = ann.suggestion?.trim() || ''
  const explanation = ann.explanation?.trim() || ''
  return Boolean(text || suggestion || explanation)
}

/** 是否可安全自动修订 */
export function isApplicableRevision(ann: ContractReviewAnnotation): boolean {
  if (ann.revision_applicable === false) return false
  const text = revisionNeedle(ann)
  const suggestion = ann.suggestion?.trim() || ''
  if (!suggestion || suggestion === text) return false
  if (text.length < MIN_REVISION_MATCH_LEN) return false
  if (ann.result_type && ['通过', '需删除'].includes(ann.result_type)) return false
  if (!isRevisionPairConsistent(text, suggestion)) return false
  return true
}

function escapeRegExp(text: string): string {
  return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

function normalizePunctuation(text: string): string {
  return text
    .replace(/[""]/g, '"')
    .replace(/['']/g, "'")
    .replace(/[（]/g, '(')
    .replace(/[）]/g, ')')
    .replace(/[：]/g, ':')
    .replace(/[；]/g, ';')
    .replace(/[，]/g, ',')
    .replace(/[。]/g, '.')
}

function collapseSpaces(text: string): string {
  return text.replace(/\s+/g, ' ').trim()
}

function normalizeForCompare(text: string): string {
  return collapseSpaces(normalizePunctuation(text))
}

/** 仅使用完整原文变体，禁止截断前缀匹配 */
function needleCandidates(needle: string): string[] {
  const raw = needle?.trim()
  if (!raw || raw.length < MIN_REVISION_MATCH_LEN) return []
  const set = new Set<string>()
  const add = (v?: string) => {
    const t = v?.trim()
    if (t && t.length >= MIN_REVISION_MATCH_LEN) set.add(t)
  }
  add(raw)
  add(normalizePunctuation(raw))
  add(collapseSpaces(raw))
  add(collapseSpaces(normalizePunctuation(raw)))
  return [...set]
}

function hasTrustedOffset(startOffset?: number | null, endOffset?: number | null): boolean {
  return (
    startOffset != null
    && endOffset != null
    && startOffset > 0
    && endOffset > startOffset
  )
}

/** 校验匹配区间与待替换原文一致，防止误删/错位 */
export function verifyTextSpan(
  haystack: string,
  span: { start: number; end: number },
  needle: string,
): boolean {
  if (span.start < 0 || span.end <= span.start || span.end > haystack.length) return false
  const slice = haystack.slice(span.start, span.end)
  if (!slice.trim()) return false
  const normSlice = normalizeForCompare(slice)
  const normNeedle = normalizeForCompare(needle)
  if (!normNeedle) return false
  if (normSlice === normNeedle) return true
  if (normSlice.includes(normNeedle) || normNeedle.includes(normSlice)) {
    const shorter = Math.min(normSlice.length, normNeedle.length)
    const longer = Math.max(normSlice.length, normNeedle.length)
    return shorter / longer >= 0.85
  }
  return false
}

function findExactMatches(haystack: string, candidate: string): { start: number; end: number }[] {
  const matches: { start: number; end: number }[] = []
  let from = 0
  while (from < haystack.length) {
    const idx = haystack.indexOf(candidate, from)
    if (idx < 0) break
    matches.push({ start: idx, end: idx + candidate.length })
    from = idx + 1
  }
  return matches
}

function findRegexMatches(haystack: string, candidate: string): { start: number; end: number }[] {
  const pattern = escapeRegExp(candidate).replace(/\s+/g, '\\s+')
  const re = new RegExp(pattern, 'g')
  const matches: { start: number; end: number }[] = []
  let match: RegExpExecArray | null
  while ((match = re.exec(haystack)) !== null) {
    matches.push({ start: match.index, end: match.index + match[0].length })
  }
  return matches
}

function pickUniqueVerifiedSpan(
  haystack: string,
  matches: { start: number; end: number }[],
  needle: string,
): { start: number; end: number } | null {
  const verified = matches.filter((span) => verifyTextSpan(haystack, span, needle))
  if (verified.length === 1) return verified[0]
  return null
}

/**
 * 在正文中定位待替换片段。
 * 原则：唯一匹配 + 替换前后校验；禁止偏移量兜底与模糊归一化索引。
 */
export function locateTextSpan(
  haystack: string,
  needle: string,
  startOffset?: number | null,
  endOffset?: number | null,
): { start: number; end: number } | null {
  if (!haystack || !needle?.trim()) return null
  const raw = needle.trim()
  if (raw.length < MIN_REVISION_MATCH_LEN) return null

  if (hasTrustedOffset(startOffset, endOffset)) {
    const span = { start: startOffset as number, end: endOffset as number }
    if (endOffset! <= haystack.length && verifyTextSpan(haystack, span, raw)) {
      return span
    }
  }

  for (const candidate of needleCandidates(raw)) {
    const exact = pickUniqueVerifiedSpan(haystack, findExactMatches(haystack, candidate), raw)
    if (exact) return exact

    const regex = pickUniqueVerifiedSpan(haystack, findRegexMatches(haystack, candidate), raw)
    if (regex) return regex
  }

  return null
}

export function applySingleRevision(
  source: string,
  original: string,
  replacement: string,
  startOffset?: number | null,
  endOffset?: number | null,
): { text: string; applied: boolean } {
  const span = locateTextSpan(source, original, startOffset, endOffset)
  const next = replacement?.trim()
  if (!span || !next) return { text: source, applied: false }
  if (!verifyTextSpan(source, span, original)) return { text: source, applied: false }
  const text = source.slice(0, span.start) + next + source.slice(span.end)
  return { text, applied: true }
}

/** 基于原始正文一次性重建修订稿，仅替换唯一且已校验的区间 */
export function buildRevisedText(
  original: string,
  annotations: ContractReviewAnnotation[],
  statuses: Record<string, RevisionStatus>,
): { text: string; appliedIds: string[]; skippedIds: string[] } {
  const toApply = annotations.filter(
    (ann) => statuses[ann.id] === 'accepted' && isApplicableRevision(ann),
  )
  if (!toApply.length || !original.trim()) {
    return { text: original, appliedIds: [], skippedIds: [] }
  }

  const matched: { ann: ContractReviewAnnotation; span: { start: number; end: number } }[] = []
  const skippedIds: string[] = []

  for (const ann of toApply) {
    const needle = revisionNeedle(ann)
    const span = locateTextSpan(original, needle, ann.start_offset, ann.end_offset)
    if (span && verifyTextSpan(original, span, needle)) {
      matched.push({ ann, span })
    } else {
      skippedIds.push(ann.id)
    }
  }

  matched.sort((a, b) => b.span.start - a.span.start)

  const overlaps = (a: { start: number; end: number }, b: { start: number; end: number }) =>
    a.start < b.end && b.start < a.end

  let text = original
  const appliedIds: string[] = []
  const usedSpans: { start: number; end: number }[] = []
  for (const { ann, span } of matched) {
    if (usedSpans.some((r) => overlaps(r, span))) {
      skippedIds.push(ann.id)
      continue
    }
    const next = ann.suggestion.trim()
    text = text.slice(0, span.start) + next + text.slice(span.end)
    appliedIds.push(ann.id)
    usedSpans.push(span)
  }

  return { text, appliedIds, skippedIds }
}

/** 批量接受待处理建议：始终从原始正文重建 */
export function applyAllPendingRevisions(
  original: string,
  annotations: ContractReviewAnnotation[],
  statuses: Record<string, RevisionStatus>,
): { text: string; appliedCount: number; skipped: string[]; nextStatuses: Record<string, RevisionStatus> } {
  const nextStatuses = { ...statuses }
  for (const ann of annotations) {
    if (nextStatuses[ann.id] === 'pending' && isApplicableRevision(ann)) {
      nextStatuses[ann.id] = 'accepted'
    }
  }
  const { text, appliedIds, skippedIds } = buildRevisedText(original, annotations, nextStatuses)
  for (const ann of annotations) {
    if (nextStatuses[ann.id] === 'accepted' && !appliedIds.includes(ann.id)) {
      nextStatuses[ann.id] = 'pending'
    }
  }
  return {
    text,
    appliedCount: appliedIds.length,
    skipped: skippedIds,
    nextStatuses,
  }
}

export function revisionStatusLabel(status: RevisionStatus): string {
  return ({ pending: '待处理', accepted: '已修订', rejected: '已忽略' } as const)[status]
}

export function hasAcceptedRevisions(statuses: Record<string, RevisionStatus>): boolean {
  return Object.values(statuses).some((s) => s === 'accepted')
}

export function pendingRevisionCount(
  annotations: ContractReviewAnnotation[],
  statuses: Record<string, RevisionStatus>,
): number {
  return annotations.filter((ann) => statuses[ann.id] === 'pending' && isApplicableRevision(ann)).length
}

function textOverlapRatio(a: string, b: string): number {
  if (!a || !b) return 0
  const shorter = a.length <= b.length ? a : b
  const longer = a.length <= b.length ? b : a
  if (longer.includes(shorter)) return shorter.length / longer.length
  let common = 0
  const minLen = Math.min(a.length, b.length)
  for (let i = 0; i < minLen; i += 1) {
    if (a[i] !== b[i]) break
    common += 1
  }
  return common / Math.max(a.length, b.length)
}

function normalizeForDedup(text: string): string {
  return normalizeForCompare(text)
}

/**
 * 去除重复/包含关系的风险项：保留更精确的子条款，去掉涵盖它的宽泛条目。
 * 例：已有 3.1.7 时，去掉原文包含 3.1.7 的「第三条 双方的权利和义务」重复项。
 */
export function deduplicateAnnotations(
  annotations: ContractReviewAnnotation[],
  contractText: string,
): ContractReviewAnnotation[] {
  const sorted = sortAnnotationsByDocumentOrder(annotations, contractText)
  const kept: ContractReviewAnnotation[] = []

  for (const ann of sorted) {
    const needle = normalizeForDedup(revisionNeedle(ann))
    if (needle.length < 8) {
      kept.push(ann)
      continue
    }

    let dominated = false
    for (let i = kept.length - 1; i >= 0; i -= 1) {
      const existing = kept[i]
      const existNeedle = normalizeForDedup(revisionNeedle(existing))
      if (!existNeedle || existNeedle.length < 8) continue

      if (needle.length > existNeedle.length && needle.includes(existNeedle)) {
        dominated = true
        break
      }
      if (needle.length < existNeedle.length && existNeedle.includes(needle)) {
        kept.splice(i, 1)
        continue
      }

      const overlap = textOverlapRatio(needle, existNeedle)
      if (overlap >= 0.65) {
        if (needle.length > existNeedle.length) {
          dominated = true
          break
        }
        if (needle.length < existNeedle.length) {
          kept.splice(i, 1)
        } else if (isApplicableRevision(existing) && !isApplicableRevision(ann)) {
          dominated = true
          break
        } else if (!isApplicableRevision(existing) && isApplicableRevision(ann)) {
          kept.splice(i, 1)
        } else {
          dominated = true
          break
        }
      }
    }

    if (!dominated) kept.push(ann)
  }

  return kept
}

export function countRiskLevels(annotations: ContractReviewAnnotation[]): Record<'high' | 'medium' | 'low', number> {
  const rc = { high: 0, medium: 0, low: 0 }
  for (const ann of annotations) {
    const level = ann.risk_level as keyof typeof rc
    if (level in rc) rc[level] += 1
  }
  return rc
}

/** 去除用户可见文案中的第三方品牌词 */
export function sanitizeUserBrandText(text: string): string {
  if (!text) return text
  return text
    .replace(/法睿审查完成/g, '审查完成')
    .replace(/通义法睿/g, '智能法律引擎')
    .replace(/法睿/g, '')
}

/** 在已渲染 DOM 中替换首个匹配文本片段（保留标签结构） */
export function replaceFirstTextInElement(root: HTMLElement, search: string, replacement: string): boolean {
  if (!root || !search?.trim() || !replacement?.trim()) return false
  if (typeof document === 'undefined') return false

  for (const candidate of needleCandidates(search)) {
    const fullText = root.innerText || ''
    const idx = fullText.indexOf(candidate)
    if (idx < 0) continue

    let charCount = 0
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT)
    let startNode: Text | null = null
    let startOffset = 0
    let endNode: Text | null = null
    let endOffset = 0
    const endIdx = idx + candidate.length

    while (walker.nextNode()) {
      const node = walker.currentNode as Text
      const len = node.length
      if (!startNode && charCount + len > idx) {
        startNode = node
        startOffset = idx - charCount
      }
      if (charCount + len >= endIdx) {
        endNode = node
        endOffset = endIdx - charCount
        break
      }
      charCount += len
    }

    if (!startNode || !endNode) continue

    if (startNode === endNode) {
      startNode.replaceWith(
        startNode.textContent!.slice(0, startOffset),
        document.createTextNode(replacement),
        startNode.textContent!.slice(endOffset),
      )
    } else {
      const after = endNode.splitText(endOffset)
      endNode.textContent = ''
      startNode.textContent = startNode.textContent!.slice(0, startOffset)
      startNode.after(document.createTextNode(replacement))
      after.remove()
    }
    root.normalize()
    return true
  }
  return false
}

/** 在 HTML 正文中替换首个匹配片段（保留标签结构）；成功时返回新 HTML，失败返回 null */
export function replaceFirstTextInHtml(html: string, search: string, replacement: string): string | null {
  if (!html?.trim() || !search?.trim() || !replacement?.trim()) return null
  if (typeof document === 'undefined') return null

  const root = document.createElement('div')
  root.innerHTML = html
  if (replaceFirstTextInElement(root, search, replacement)) {
    return root.innerHTML
  }
  return null
}

/** 在 docx-preview 等已渲染 DOM 上按纯文本规则应用修订（先重渲染原文件再调用） */
export function applyRevisionsToElement(
  root: HTMLElement,
  originalPlain: string,
  annotations: ContractReviewAnnotation[],
  statuses: Record<string, RevisionStatus>,
): { appliedIds: string[]; skippedIds: string[] } {
  const { appliedIds, skippedIds } = buildRevisedText(originalPlain, annotations, statuses)
  if (!appliedIds.length || !root) {
    return { appliedIds, skippedIds }
  }

  const toApply = annotations
    .filter((ann) => appliedIds.includes(ann.id))
    .sort((a, b) => {
      const sa = locateTextSpan(originalPlain, revisionNeedle(a), a.start_offset, a.end_offset)
      const sb = locateTextSpan(originalPlain, revisionNeedle(b), b.start_offset, b.end_offset)
      return (sb?.start ?? 0) - (sa?.start ?? 0)
    })

  const applied: string[] = []
  const skipped = [...skippedIds]
  for (const ann of toApply) {
    const needle = revisionNeedle(ann)
    const next = ann.suggestion?.trim()
    if (!needle || !next) continue
    if (replaceFirstTextInElement(root, needle, next)) {
      applied.push(ann.id)
    } else {
      skipped.push(ann.id)
    }
  }
  return { appliedIds: applied, skippedIds: skipped }
}

/** 在原始 HTML 上按与纯文本相同的规则应用修订 */
export function buildRevisedHtml(
  sourceHtml: string,
  originalPlain: string,
  annotations: ContractReviewAnnotation[],
  statuses: Record<string, RevisionStatus>,
): { html: string; appliedIds: string[]; skippedIds: string[] } {
  const { appliedIds, skippedIds } = buildRevisedText(originalPlain, annotations, statuses)
  if (!appliedIds.length || !sourceHtml.trim()) {
    return { html: sourceHtml, appliedIds, skippedIds }
  }

  let html = sourceHtml
  const toApply = annotations
    .filter((ann) => appliedIds.includes(ann.id))
    .sort((a, b) => {
      const sa = locateTextSpan(originalPlain, revisionNeedle(a), a.start_offset, a.end_offset)
      const sb = locateTextSpan(originalPlain, revisionNeedle(b), b.start_offset, b.end_offset)
      return (sb?.start ?? 0) - (sa?.start ?? 0)
    })

  for (const ann of toApply) {
    const needle = revisionNeedle(ann)
    const next = ann.suggestion?.trim()
    if (!needle || !next) continue
    const nextHtml = replaceFirstTextInHtml(html, needle, next)
    if (nextHtml === null) {
      skippedIds.push(ann.id)
      continue
    }
    html = nextHtml
  }

  return { html, appliedIds, skippedIds }
}
