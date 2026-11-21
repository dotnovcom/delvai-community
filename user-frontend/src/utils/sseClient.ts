import { handleFetchSessionReplaced } from './request'

export interface SseHandlers<TStart = unknown, TDone = unknown> {
  onStart?: (event: TStart) => void
  onToken?: (chunk: string) => void
  onReplace?: (content: string) => void
  onDetail?: (content: string) => void
  onStatus?: (text: string) => void
  onDone?: (event: TDone) => void
  onError?: (message: string) => void
}

type ParsedEvent = { type: string; content?: string; message?: string } | null

function parseSseErrorDetail(err: unknown): string {
  const detail = (err as { detail?: string | { message?: string } }).detail
  if (typeof detail === 'string') return detail
  if (detail && typeof detail === 'object' && detail.message) return detail.message
  return '请求失败'
}

function dispatchSseBlock<TStart, TDone>(
  block: string,
  handlers: SseHandlers<TStart, TDone>,
  parseEvent: (payload: string) => ParsedEvent,
) {
  const dataLines: string[] = []
  for (const line of block.split('\n')) {
    if (!line.startsWith('data:')) continue
    dataLines.push(line.slice(5).trimStart())
  }
  if (!dataLines.length) return

  const payload = dataLines.join('\n').trim()
  if (!payload || payload === '[DONE]') return

  const event = parseEvent(payload)
  if (!event) return
  if (event.type === 'start') handlers.onStart?.(event as TStart)
  else if (event.type === 'token') handlers.onToken?.(event.content || '')
  else if (event.type === 'replace') handlers.onReplace?.(event.content || '')
  else if (event.type === 'detail') handlers.onDetail?.(event.content || '')
  else if (event.type === 'status') handlers.onStatus?.(event.content || '')
  else if (event.type === 'done') handlers.onDone?.(event as TDone)
  else if (event.type === 'error') handlers.onError?.(event.message || '流式请求失败')
}

/** 按 SSE 规范（空行分隔 event）解析流式响应，参考阿里云流式输出文档 */
export async function readSseStream<TStart = unknown, TDone = unknown>(
  response: Response,
  handlers: SseHandlers<TStart, TDone>,
  parseEvent: (payload: string) => ParsedEvent,
) {
  if (!response.ok) {
    if (await handleFetchSessionReplaced(response)) return
    const err = await response.json().catch(() => ({}))
    handlers.onError?.(parseSseErrorDetail(err))
    return
  }

  const reader = response.body?.getReader()
  if (!reader) {
    handlers.onError?.('浏览器不支持流式响应')
    return
  }

  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, '\n')

    let boundary = buffer.indexOf('\n\n')
    while (boundary !== -1) {
      const block = buffer.slice(0, boundary)
      buffer = buffer.slice(boundary + 2)
      dispatchSseBlock(block, handlers, parseEvent)
      boundary = buffer.indexOf('\n\n')
    }
  }

  if (buffer.trim()) {
    dispatchSseBlock(buffer, handlers, parseEvent)
  }
}
