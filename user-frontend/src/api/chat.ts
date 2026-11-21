import { get, post, del, getToken, BASE_URL } from '../utils/request'
import { readSseStream } from '../utils/sseClient'

export interface Conversation {
  id: number
  user_id: number
  title: string
  interaction_type: string
  status: string
  created_at: string
  updated_at: string
  last_message?: string
}

export interface ChatMessage {
  id: number
  conversation_id: number
  role: string
  content_type: string
  content: string
  tokens_used: number
  ai_engine?: string
  metadata?: { suggestions?: string[]; image_url?: string; file_name?: string; generating?: boolean }
  my_feedback?: 'like' | 'dislike' | null
  created_at: string
}

export interface AiChatUi {
  avatar: string
  copy: boolean
  regenerate: boolean
  like: boolean
  dislike: boolean
  speak: boolean
  share: boolean
}

export interface StreamEvent {
  type: 'start' | 'token' | 'replace' | 'status' | 'done' | 'error'
  content?: string
  engine?: string
  message_id?: number
  ai_engine?: string
  tokens_used?: number
  suggestions?: string[]
  conversation_title?: string
  message?: string
}

export function createConversation(data: { title?: string } = {}) {
  return post<Conversation>('/api/v1/conversations', { interaction_type: 'text', ...data })
}

export function listConversations(skip = 0, limit = 20, types?: string) {
  const qs = new URLSearchParams({ skip: String(skip), limit: String(limit) })
  if (types) qs.set('types', types)
  return get<Conversation[]>(`/api/v1/conversations?${qs.toString()}`, {
    skipGlobalErrorHandler: true,
  })
}

export function getMessages(conversationId: number) {
  return get<ChatMessage[]>(`/api/v1/conversations/${conversationId}/messages`)
}

export function deleteConversation(conversationId: number) {
  return del(`/api/v1/conversations/${conversationId}`)
}

function parseStreamEvent(payload: string): StreamEvent | null {
  try {
    return JSON.parse(payload) as StreamEvent
  } catch {
    return null
  }
}

export async function streamMessage(
  conversationId: number,
  data: {
    content: string
    content_type?: string
    image_url?: string
    file_url?: string
    file_name?: string
    deep_think?: boolean
    online_search?: boolean
  },
  callbacks: {
    onStart?: (e: StreamEvent) => void
    onToken?: (chunk: string) => void
    onReplace?: (content: string) => void
    onDetail?: (content: string) => void
    onStatus?: (text: string) => void
    onDone?: (e: StreamEvent) => void
    onError?: (msg: string) => void
  },
  options?: { signal?: AbortSignal },
) {
  const token = getToken()
  const url = `${BASE_URL}/api/v1/conversations/${conversationId}/messages`

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'text/event-stream',
        Authorization: `Bearer ${token}`,
        'Cache-Control': 'no-cache',
      },
      body: JSON.stringify(data),
      signal: options?.signal,
    })

    await readSseStream<StreamEvent, StreamEvent>(
      response,
      {
        onStart: callbacks.onStart,
        onToken: callbacks.onToken,
        onReplace: callbacks.onReplace,
        onDetail: callbacks.onDetail,
        onStatus: callbacks.onStatus,
        onDone: callbacks.onDone,
        onError: callbacks.onError,
      },
      parseStreamEvent,
    )
  } catch (e) {
    if ((e as Error).name === 'AbortError') return
    callbacks.onError?.((e as Error).message || '网络错误')
  }
}

export function getAiChatUi() {
  return get<AiChatUi>('/api/v1/conversations/ai-ui')
}

export function setMessageFeedback(conversationId: number, messageId: number, vote: 'like' | 'dislike' | 'none') {
  return post<{ vote: 'like' | 'dislike' | null }>(
    `/api/v1/conversations/${conversationId}/messages/${messageId}/feedback`,
    { vote },
  )
}

export function createMessageShare(conversationId: number, messageId: number) {
  return post<{ token: string; path: string }>(
    `/api/v1/conversations/${conversationId}/messages/${messageId}/share`,
  )
}

export function getSharedMessage(token: string) {
  return get<{ question: string; answer: string; created_at: string }>(
    `/api/v1/conversations/shares/${token}`,
  )
}

export async function streamRegenerate(
  conversationId: number,
  messageId: number,
  data: { deep_think?: boolean; online_search?: boolean },
  callbacks: {
    onToken?: (chunk: string) => void
    onReplace?: (content: string) => void
    onDetail?: (content: string) => void
    onStatus?: (text: string) => void
    onDone?: (e: StreamEvent) => void
    onError?: (msg: string) => void
  },
  options?: { signal?: AbortSignal },
) {
  const token = getToken()
  const url = `${BASE_URL}/api/v1/conversations/${conversationId}/messages/${messageId}/regenerate`
  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'text/event-stream',
        Authorization: `Bearer ${token}`,
        'Cache-Control': 'no-cache',
      },
      body: JSON.stringify(data),
      signal: options?.signal,
    })
    await readSseStream<StreamEvent, StreamEvent>(
      response,
      {
        onToken: callbacks.onToken,
        onReplace: callbacks.onReplace,
        onDetail: callbacks.onDetail,
        onStatus: callbacks.onStatus,
        onDone: callbacks.onDone,
        onError: callbacks.onError,
      },
      parseStreamEvent,
    )
  } catch (e) {
    if ((e as Error).name === 'AbortError') return
    callbacks.onError?.((e as Error).message || '网络错误')
  }
}
