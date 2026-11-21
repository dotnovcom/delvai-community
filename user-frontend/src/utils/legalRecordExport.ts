import {
  documentPreviewHtml,
  documentPlainPreview,
  displayDocumentTitle,
  resolveDocumentTitle,
  stripLeadingDocumentTitle,
  downloadDocumentTxt,
  downloadDocumentWord,
  printDocumentPreview,
} from './documentExport'

export {
  downloadDocumentTxt,
  downloadDocumentWord,
  printDocumentPreview,
  documentPreviewHtml,
  documentPlainPreview,
  displayDocumentTitle,
  resolveDocumentTitle,
  stripLeadingDocumentTitle,
}

export function contractReviewToMarkdown(
  fileName: string,
  summary: string,
  annotations: {
    risk_level: string
    category: string
    text: string
    suggestion: string
  }[],
): string {
  const levelLabel: Record<string, string> = {
    high: '高风险',
    medium: '中风险',
    low: '低风险',
  }
  let md = `# 合同审查报告\n\n**文件**：${fileName}\n\n## 审查摘要\n\n${summary || '（无）'}\n\n## 风险明细\n\n`
  if (!annotations.length) {
    md += '暂无风险标注。\n'
    return md
  }
  annotations.forEach((a, i) => {
    md += `### ${i + 1}. ${levelLabel[a.risk_level] || a.risk_level} · ${a.category}\n\n`
    md += `**原文摘录**：${a.text}\n\n**修改建议**：${a.suggestion}\n\n`
  })
  return md
}

export function contractExtractToMarkdown(
  fileName: string,
  fields: Record<string, unknown>[],
): string {
  let md = `# 合同字段抽取\n\n**文件**：${fileName}\n\n| 字段 | 抽取值 |\n| --- | --- |\n`
  for (const row of fields) {
    const name = String(row.extractItem || row.extract_item || '—')
    const vals = (row.value as { data?: string }[]) || []
    const text = vals.map((v) => v?.data).filter(Boolean).join('；') || '—'
    md += `| ${name} | ${text} |\n`
  }
  return md
}

export function analysisReportToMarkdown(
  caseDescription: string,
  content: string,
  relatedCases: { title?: string; case_no?: string; summary?: string }[],
): string {
  let md = `# 类案分析报告\n\n## 案情描述\n\n${caseDescription}\n\n## 分析内容\n\n${content}\n\n`
  if (relatedCases.length) {
    md += `## 相关案例\n\n`
    relatedCases.forEach((c, i) => {
      md += `### ${i + 1}. ${c.title || '案例'}\n\n`
      if (c.case_no) md += `**案号**：${c.case_no}\n\n`
      if (c.summary) md += `${c.summary}\n\n`
    })
  }
  return md
}

export function searchHistoryToMarkdown(
  kindLabel: string,
  query: string,
  aiSummary: string | undefined,
  previews: { title?: string; snippet?: string }[],
): string {
  let md = `# ${kindLabel}检索记录\n\n**关键词**：${query}\n\n`
  if (aiSummary) {
    md += `## AI 摘要\n\n${aiSummary}\n\n`
  }
  if (previews.length) {
    md += `## 命中条目预览\n\n`
    previews.forEach((p, i) => {
      md += `### ${i + 1}. ${p.title || '条目'}\n\n${p.snippet || ''}\n\n`
    })
  }
  return md
}

export function exportMarkdownWord(title: string, markdown: string) {
  return downloadDocumentWord(title, markdown)
}

export function exportMarkdownPrint(title: string, markdown: string) {
  return printDocumentPreview(title, markdown)
}

export function exportMarkdownTxt(title: string, markdown: string) {
  downloadDocumentTxt(title, markdown)
}
