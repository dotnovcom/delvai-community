<script setup lang="ts">

import { ref, computed, nextTick, onMounted, onBeforeUnmount } from 'vue'
import { useRoute } from 'vue-router'

import { ElMessage } from 'element-plus'

import {

  createConversation,

  listConversations,

  getMessages,

  deleteConversation,

  streamMessage,

  streamRegenerate,

  getAiChatUi,

  setMessageFeedback,

  createMessageShare,

  type Conversation,

  type ChatMessage,

  type AiChatUi,

} from '../../../api/chat'
import { synthesizeSpeech } from '../../../api/legal'
import { useVoiceRecorder } from '../../../composables/useVoiceRecorder'
import { ensureSpeechAccess } from '../../../composables/ensureSpeechAccess'
import { BASE_URL, getToken } from '../../../utils/request'
import { ensureLoggedIn } from '../../../composables/useLoginDialog'
import { legalChatHtml, readableLegalAnswer, splitLegalAnswer, streamingLegalHtml } from '../../../utils/legalChatContent'
import { qrCodeDataUrl } from '../../../utils/qrCodeDataUrl'
import { useUserStore } from '../../../store/user'
import { AI_DISCLAIMER } from '../../../constants/aiDisclaimer'
import { useBrandLabels } from '../../../composables/useBrandLabels'
import WorkspaceQuotaHint from '../../../components/legal/WorkspaceQuotaHint.vue'
import FaIcon from '../../../components/FaIcon.vue'
import ChatReplyActions from '../../../components/legal/ChatReplyActions.vue'



const route = useRoute()
const userStore = useUserStore()
const { platformName, aiNavLabel, load: loadBrand } = useBrandLabels()

const aiUi = ref<AiChatUi>({
  avatar: '',
  copy: true,
  regenerate: true,
  like: true,
  dislike: true,
  speak: true,
  share: true,
})
const speakingId = ref<number | null>(null)
const detailOpen = ref<Record<number, boolean>>({})
const shareVisible = ref(false)
const shareLink = ref('')
const shareQr = ref('')
const shareCopied = ref(false)
const hasReplyActions = computed(() =>
  aiUi.value.copy || aiUi.value.regenerate || aiUi.value.like
  || aiUi.value.dislike || aiUi.value.speak || aiUi.value.share,
)

const welcomeTitle = computed(() => {
  if (aiNavLabel.value) return `嗨～我是${aiNavLabel.value}`
  if (platformName.value) return `嗨～我是${platformName.value}`
  return '嗨～我是您的法律助手'
})

const welcomeDesc = computed(() => {
  const name = platformName.value
  const prefix = name ? `${name}智能法律咨询` : '智能法律咨询'
  return `${prefix}。默认关闭「联网检索」与「深度思考」以加快流式回复；需要时可手动开启。复杂案情将自动选用更合适的模型。`
})

const conversations = ref<Conversation[]>([])

const currentConvId = ref<number | null>(null)

const messages = ref<ChatMessage[]>([])

const inputText = ref('')

const streaming = ref(false)

const streamRaw = ref('')
const streamStatus = ref('')
const streamBlocks = ref<string[]>([])
const streamTailHtml = ref('')
const conclusionSettled = ref(false)
const streamDetail = ref('')
const streamDetailHtml = ref('')
const streamDetailOpen = ref(false)
const detailHtml = ref<Record<number, string>>({})
const detailShown = ref<Record<number, string>>({})

const suggestions = ref<string[]>([])

const showPanel = ref(false)

const deepThink = ref(false)
const onlineSearch = ref(false)
const pendingImageUrl = ref('')

const messageListRef = ref<HTMLElement | null>(null)

let streamAbort: AbortController | null = null
let streamFlushRaf = 0
let conclusionTarget = ''
let conclusionShown = ''
let typeTimer = 0
let pendingFinish: (() => Promise<void>) | null = null
let generatingWatch = 0
let liveDetailTimer = 0
let openDetailWhenReady = false
let lastHtmlPaint = 0
let scrollTimer = 0
let stableSource = ''
const detailTimers = new Map<number, number>()
const CONV_KEY = 'legal-chat-current'



const QUICK_ENTRIES = [

  { icon: 'clipboard', label: '合同服务', text: '请帮我审查一份劳动合同的风险点' },

  { icon: 'scale-balanced', label: '法律咨询', text: '员工被违法辞退，应该如何维权？' },

  { icon: 'file-lines', label: '文书生成', text: '帮我起草一份律师函' },

  { icon: 'magnifying-glass', label: '法律检索', text: '劳动合同法关于试用期的规定有哪些？' },

]

const WELCOME_PROMPT_SETS = [
  [
    '员工被违法辞退应该如何维权？',
    '劳动合同未签书面合同有什么后果？',
    '公司拖欠工资可以向哪些部门投诉？',
    '试用期最长可以约定多久？',
    '经济补偿金如何计算？',
    '竞业限制条款是否有效？',
    '工伤认定需要哪些材料？',
    '租房合同押金不退怎么办？',
    '个人信息被泄露如何维权？',
    '加班费计算标准是什么？',
    '公司单方调岗是否合法？',
    '离职证明不开怎么办？',
  ],
  [
    '民间借贷利息最高可以约定多少？',
    '网购商品存在质量问题如何索赔？',
    '交通事故责任如何划分？',
    '离婚时财产如何分割？',
    '子女抚养费标准是多少？',
    '房屋买卖卖方违约怎么办？',
    '建设工程款拖欠如何追讨？',
    '知识产权被侵权如何应对？',
    '公司股东分红争议如何处理？',
    '借款没有借条如何举证？',
    '装修合同增项费用谁承担？',
    '宠物伤人主人如何担责？',
  ],
  [
    '劳动合同解除通知期是多久？',
    '未休年假可以折现吗？',
    '调岗降薪是否合法？',
    '保密协议违约有何责任？',
    '涉外合同适用哪国法律？',
    '商标近似是否构成侵权？',
    '行政复议与诉讼如何选择？',
    '法定代表人变更如何办理？',
    '电子劳动合同是否具有效力？',
    '网络诽谤如何取证维权？',
    '加盟合同纠纷如何处理？',
    '执行异议怎样提出？',
  ],
]

const welcomePromptIndex = ref(0)

const welcomePrompts = computed(() => {
  const set = WELCOME_PROMPT_SETS[welcomePromptIndex.value % WELCOME_PROMPT_SETS.length]
  return set.slice(0, 6)
})

const inputCharCount = computed(() => inputText.value.length)

function refreshWelcomePrompts() {
  if (WELCOME_PROMPT_SETS.length <= 1) return
  let next = welcomePromptIndex.value
  while (next === welcomePromptIndex.value) {
    next = Math.floor(Math.random() * WELCOME_PROMPT_SETS.length)
  }
  welcomePromptIndex.value = next
}

function applyWelcomePrompt(text: string) {
  inputText.value = text
}



const showResultDisclaimer = computed(
  () =>
    messages.value.some((m) => m.role === 'assistant')
    || (!!streamRaw.value && streaming.value),
)



onMounted(async () => {
  await loadBrand()
  getAiChatUi().then((ui) => { aiUi.value = ui }).catch(() => null)
  if (userStore.isLoggedIn) userStore.fetchUserInfo().catch(() => null)
  await loadConversations()

  const q = route.query.q as string
  if (q) {
    inputText.value = q
    if (await ensureLoggedIn()) await handleSend()
  }
})

function rememberConversation(id: number | null) {
  if (id) sessionStorage.setItem(CONV_KEY, String(id))
  else sessionStorage.removeItem(CONV_KEY)
}

function previewText(content: string) {
  return content.replace(/\s+/g, ' ').trim().slice(0, 80)
}

function watchGeneratingReply(id: number) {
  if (generatingWatch) window.clearInterval(generatingWatch)
  generatingWatch = 0
  const latest = [...messages.value].reverse().find((item) => item.role === 'assistant')
  if (!latest?.metadata?.generating) return
  let tries = 0
  generatingWatch = window.setInterval(async () => {
    tries += 1
    if (currentConvId.value !== id || tries > 45) {
      window.clearInterval(generatingWatch)
      generatingWatch = 0
      return
    }
    try {
      const rows = await getMessages(id)
      if (currentConvId.value !== id) return
      messages.value = rows
      const assistant = [...rows].reverse().find((item) => item.role === 'assistant')
      const conv = conversations.value.find((item) => item.id === id)
      if (conv && assistant?.content) conv.last_message = previewText(assistant.content)
      suggestions.value = assistant?.metadata?.suggestions || []
      if (!assistant?.metadata?.generating) {
        window.clearInterval(generatingWatch)
        generatingWatch = 0
        scrollToBottom()
      }
    } catch {
      window.clearInterval(generatingWatch)
      generatingWatch = 0
    }
  }, 1000)
}

async function loadConversations() {
  if (!getToken()) return
  try {
    conversations.value = await listConversations()
  } catch {
    conversations.value = []
    return
  }

  if (conversations.value.length && !currentConvId.value) {
    const fromQuery = Number(route.query.cid || 0)
    const saved = Number(sessionStorage.getItem(CONV_KEY) || 0)
    const pick = conversations.value.find((item) => item.id === fromQuery)?.id
      || conversations.value.find((item) => item.id === saved)?.id
      || conversations.value[0].id
    await selectConversation(pick)
  }
}



async function selectConversation(id: number) {
  abortActiveStream()
  currentConvId.value = id

  messages.value = await getMessages(id)
  rememberConversation(id)

  const last = [...messages.value].reverse().find((m) => m.role === 'assistant')

  suggestions.value = last?.metadata?.suggestions || []

  scrollToBottom()
  watchGeneratingReply(id)
}



async function newConversation() {
  if (!await ensureLoggedIn()) return
  abortActiveStream()
  const conv = await createConversation()

  conversations.value.unshift(conv)

  currentConvId.value = conv.id
  rememberConversation(conv.id)

  messages.value = []

  suggestions.value = []

}



async function removeConversation(id: number) {
  if (!await ensureLoggedIn()) return

  await deleteConversation(id)

  conversations.value = conversations.value.filter((c) => c.id !== id)

  if (currentConvId.value === id) {

    currentConvId.value = conversations.value[0]?.id ?? null

    if (currentConvId.value) await selectConversation(currentConvId.value)

    else {

      messages.value = []

      suggestions.value = []

    }

  }

}



function abortStreamRequest() {
  if (streamAbort) {
    streamAbort.abort()
    streamAbort = null
  }
}

function stopDetailStream(id?: number) {
  const ids = id == null ? [...detailTimers.keys()] : [id]
  for (const key of ids) {
    const timer = detailTimers.get(key)
    if (timer) window.clearInterval(timer)
    detailTimers.delete(key)
  }
}

function resetConclusionTypewriter() {
  conclusionTarget = ''
  conclusionShown = ''
  pendingFinish = null
  openDetailWhenReady = false
  lastHtmlPaint = 0
  stableSource = ''
  if (scrollTimer) window.clearTimeout(scrollTimer)
  scrollTimer = 0
  if (typeTimer) cancelAnimationFrame(typeTimer)
  typeTimer = 0
  if (liveDetailTimer) window.clearInterval(liveDetailTimer)
  liveDetailTimer = 0
  streamRaw.value = ''
  streamBlocks.value = []
  streamTailHtml.value = ''
  streamDetail.value = ''
  streamDetailHtml.value = ''
  streamDetailOpen.value = false
  conclusionSettled.value = false
}

function paintStreamMarkdown(flushTail = false) {
  const text = conclusionShown
  let cut = text.lastIndexOf('\n\n')
  if (cut < 24) {
    const sentence = text.lastIndexOf('。')
    cut = sentence >= 24 ? sentence + 1 : 0
  }
  const stable = cut > 0 ? text.slice(0, cut).trimEnd() : ''
  const tail = (cut > 0 ? text.slice(cut) : text).replace(/^\n+/, '')
  if (stable.startsWith(stableSource) && stable.length > stableSource.length) {
    const extra = stable.slice(stableSource.length).trim()
    stableSource = stable
    if (extra) streamBlocks.value = [...streamBlocks.value, streamingLegalHtml(extra)]
  }
  const now = performance.now()
  if (flushTail || now - lastHtmlPaint >= 120) {
    lastHtmlPaint = now
    streamTailHtml.value = tail ? streamingLegalHtml(tail) : ''
  }
}

function noteSidebarPreview() {
  const id = currentConvId.value
  if (!id || !conclusionShown) return
  const conv = conversations.value.find((item) => item.id === id)
  if (conv) conv.last_message = previewText(conclusionShown)
}

function pumpConclusion() {
  if (typeTimer) return
  let lastPaint = 0
  const tick = (now: number) => {
    if (conclusionShown.length < conclusionTarget.length) {
      if (!lastPaint || now - lastPaint >= 16) {
        conclusionShown = conclusionTarget.slice(0, conclusionShown.length + 1)
        streamRaw.value = conclusionShown
        lastPaint = now
        paintStreamMarkdown()
        if (conclusionShown.length % 12 === 0) scrollToBottom()
      }
      typeTimer = requestAnimationFrame(tick)
      return
    }
    typeTimer = 0
    conclusionSettled.value = true
    paintStreamMarkdown(true)
    noteSidebarPreview()
    scrollToBottom()
    const finish = pendingFinish
    if (finish) {
      pendingFinish = null
      void finish()
    }
  }
  typeTimer = requestAnimationFrame(tick)
}

function pushConclusion(chunk: string, replace = false) {
  streamStatus.value = ''
  const next = replace ? chunk : conclusionTarget + chunk
  if (!conclusionShown || next.startsWith(conclusionShown)) {
    conclusionTarget = next
    pumpConclusion()
    return
  }
  let index = 0
  const limit = Math.min(conclusionShown.length, next.length)
  while (index < limit && conclusionShown[index] === next[index]) index++
  if (conclusionShown.length - index <= 2) {
    conclusionTarget = next
    pumpConclusion()
  }
}

function acceptStreamDetail(content: string) {
  if (!content) return
  streamDetail.value = content
  if (!openDetailWhenReady) return
  openDetailWhenReady = false
  streamDetailOpen.value = true
  if (!liveDetailTimer) startLiveDetail(content)
}

function startLiveDetail(full: string) {
  if (liveDetailTimer) window.clearInterval(liveDetailTimer)
  let shown = ''
  const tick = () => {
    if (!streamDetailOpen.value) {
      if (liveDetailTimer) window.clearInterval(liveDetailTimer)
      liveDetailTimer = 0
      return
    }
    const target = streamDetail.value || full
    if (shown.length >= target.length) {
      streamDetailHtml.value = legalChatHtml(target)
      if (liveDetailTimer) window.clearInterval(liveDetailTimer)
      liveDetailTimer = 0
      scrollToBottom()
      return
    }
    shown = target.slice(0, shown.length + 24)
    streamDetailHtml.value = legalChatHtml(shown, true)
    scrollToBottom()
  }
  tick()
  liveDetailTimer = window.setInterval(tick, 36)
}

function toggleLiveDetail() {
  if (!streamDetail.value) {
    openDetailWhenReady = true
    return
  }
  if (streamDetailOpen.value) {
    streamDetailOpen.value = false
    if (liveDetailTimer) window.clearInterval(liveDetailTimer)
    liveDetailTimer = 0
    return
  }
  streamDetailOpen.value = true
  startLiveDetail(streamDetail.value)
}

function queueStreamFinish(task: () => Promise<void>) {
  if (conclusionShown.length >= conclusionTarget.length && !typeTimer) {
    void task()
    return
  }
  pendingFinish = task
}

function abortActiveStream() {
  abortStreamRequest()
  pendingFinish = null
  resetConclusionTypewriter()
  stopDetailStream()
  if (streaming.value) {
    streaming.value = false
    streamStatus.value = ''
  }
  if (streamFlushRaf) {
    cancelAnimationFrame(streamFlushRaf)
    streamFlushRaf = 0
  }
}

function scrollToBottom(force = false) {
  if (scrollTimer && !force) return
  const run = () => {
    scrollTimer = 0
    const el = messageListRef.value
    if (!el) return
    const distance = el.scrollHeight - el.scrollTop - el.clientHeight
    if (!force && distance > 140) return
    el.scrollTop = el.scrollHeight
  }
  if (force) {
    nextTick(run)
    return
  }
  scrollTimer = window.setTimeout(() => nextTick(run), 160)
}

function appendStreamChunk(chunk: string) {
  pushConclusion(chunk)
}

async function handleSend() {

  const text = inputText.value.trim()

  if (!text || streaming.value) return

  if (!await ensureLoggedIn()) return



  if (!currentConvId.value) {

    const conv = await createConversation()

    conversations.value.unshift(conv)

    currentConvId.value = conv.id
    rememberConversation(conv.id)

  }



  inputText.value = ''

  suggestions.value = []

  resetConclusionTypewriter()
  streaming.value = true
  streamStatus.value = ''



  messages.value.push({

    id: Date.now(),

    conversation_id: currentConvId.value!,

    role: 'user',

    content_type: 'text',

    content: text,

    tokens_used: 0,

    created_at: new Date().toISOString(),

  })

  scrollToBottom()



  const payload: {
    content: string
    deep_think?: boolean
    online_search?: boolean
    content_type?: string
    image_url?: string
  } = { content: text, deep_think: deepThink.value, online_search: onlineSearch.value }
  if (pendingImageUrl.value) {
    payload.image_url = pendingImageUrl.value
    payload.content_type = 'image'
  }
  pendingImageUrl.value = ''

  abortStreamRequest()
  streamAbort = new AbortController()
  const convId = currentConvId.value!

  await streamMessage(
    convId,
    payload,
    {
      onToken(chunk) {
        if (chunk) streamStatus.value = ''
        appendStreamChunk(chunk)
      },
      onReplace(content) {
        pushConclusion(content, true)
      },
      onDetail(content) {
        acceptStreamDetail(content)
      },
      onStatus(text) {
        streamStatus.value = text
      },
      onDone(event) {
        queueStreamFinish(async () => {
          const keepOpen = streamDetailOpen.value
          streamAbort = null
          if (currentConvId.value === convId) {
            messages.value = await getMessages(convId)
          }
          suggestions.value = event.suggestions || []
          if (event.conversation_title) {
            const conv = conversations.value.find((c) => c.id === convId)
            if (conv) conv.title = event.conversation_title!
          }
          const last = [...messages.value].reverse().find((item) => item.role === 'assistant')
          streaming.value = false
          streamStatus.value = ''
          resetConclusionTypewriter()
          if (keepOpen && last) {
            const detail = splitLegalAnswer(last.content).detail
            if (detail) {
              detailOpen.value = { ...detailOpen.value, [last.id]: true }
              detailShown.value = { ...detailShown.value, [last.id]: detail }
              detailHtml.value = { ...detailHtml.value, [last.id]: legalChatHtml(detail) }
            }
          }
          scrollToBottom()
        })
      },
      onError(msg) {
        streamAbort = null
        pendingFinish = null
        streaming.value = false
        streamStatus.value = ''
        resetConclusionTypewriter()
        ElMessage.error(msg)
      },
    },
    { signal: streamAbort.signal },
  )
}



function sendSuggestion(text: string) {

  inputText.value = text

  handleSend()

}



function quickStart(text: string) {

  inputText.value = text

  handleSend()

}



function handleKeydown(e: KeyboardEvent) {

  if (e.key === 'Enter' && !e.shiftKey) {

    e.preventDefault()

    handleSend()

  }

}



const { recording: voiceRecording, transcribing: voiceTranscribing, toggle: toggleVoice } = useVoiceRecorder({
  beforeSend: () => ensureSpeechAccess({ feature: 'voice', quotas: ['daily_chat', 'daily_voice'] }),
  onText(text) {
    inputText.value = text
    handleSend()
  },
})

function showVoiceTip() {
  if (streaming.value || voiceTranscribing.value) return
  toggleVoice()
}

async function handleImageUpload(file: File) {
  if (!await ensureLoggedIn()) return
  const token = getToken()
  const form = new FormData()
  form.append('file', file)
  const resp = await fetch(`${BASE_URL}/api/v1/conversations/upload-image`, {
    method: 'POST',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: form,
  })
  if (!resp.ok) {
    ElMessage.error('图片上传失败')
    return
  }
  const data = await resp.json()
  pendingImageUrl.value = data.url
  ElMessage.success('图片已添加，发送消息时将一并分析')
}

function showImageTip() { ElMessage.info('图片上传开发中') }

function showFileTip() { ElMessage.info('文件上传开发中') }

onBeforeUnmount(() => {
  abortActiveStream()
  stopDetailStream()
  speakAudio?.pause()
  if (generatingWatch) window.clearInterval(generatingWatch)
  window.speechSynthesis?.cancel()
})

function plainMessageText(content: string) {
  const html = legalChatHtml(content)
  const el = document.createElement('div')
  el.innerHTML = html
  return (el.textContent || '').replace(/\n{3,}/g, '\n\n').trim()
}

function toggleDetail(id: number, full: string) {
  if (detailOpen.value[id]) {
    stopDetailStream(id)
    detailOpen.value = { ...detailOpen.value, [id]: false }
    return
  }
  detailOpen.value = { ...detailOpen.value, [id]: true }
  if (!full) return
  if (detailShown.value[id] === full && detailHtml.value[id]) return
  let shown = full.startsWith(detailShown.value[id] || '') ? detailShown.value[id] || '' : ''
  stopDetailStream(id)
  const timer = window.setInterval(() => {
    if (!detailOpen.value[id]) {
      stopDetailStream(id)
      return
    }
    if (shown.length >= full.length) {
      detailShown.value = { ...detailShown.value, [id]: full }
      detailHtml.value = { ...detailHtml.value, [id]: legalChatHtml(full) }
      stopDetailStream(id)
      scrollToBottom()
      return
    }
    shown = full.slice(0, shown.length + 40)
    detailShown.value = { ...detailShown.value, [id]: shown }
    detailHtml.value = { ...detailHtml.value, [id]: legalChatHtml(shown, true) }
    scrollToBottom()
  }, 36)
  detailTimers.set(id, timer)
}

async function copyMessage(msg: ChatMessage) {
  const text = plainMessageText(readableLegalAnswer(msg.content))
  if (!text) {
    ElMessage.warning('没有可复制的内容')
    return
  }
  try {
    await navigator.clipboard.writeText(text)
  } catch {
    const area = document.createElement('textarea')
    area.value = text
    area.style.position = 'fixed'
    area.style.left = '-9999px'
    document.body.appendChild(area)
    area.select()
    document.execCommand('copy')
    area.remove()
  }
  ElMessage.success('已复制')
}

let speakAudio: HTMLAudioElement | null = null

function stopSpeaking() {
  speakAudio?.pause()
  speakAudio = null
  window.speechSynthesis?.cancel()
  speakingId.value = null
}

async function speakMessage(msg: ChatMessage) {
  if (speakingId.value === msg.id) {
    stopSpeaking()
    return
  }
  const text = plainMessageText(readableLegalAnswer(msg.content)).slice(0, 1500)
  if (!text) {
    ElMessage.warning('没有可朗读的内容')
    return
  }
  stopSpeaking()
  speakingId.value = msg.id
  try {
    const res = await synthesizeSpeech(text)
    speakAudio = new Audio(`data:${res.mime_type || 'audio/wav'};base64,${res.audio}`)
    speakAudio.onended = () => {
      if (speakingId.value === msg.id) speakingId.value = null
    }
    await speakAudio.play()
  } catch (err) {
    speakingId.value = null
    ElMessage.error(err instanceof Error ? err.message : '语音合成失败')
  }
}

async function voteMessage(msg: ChatMessage, vote: 'like' | 'dislike') {
  if (!currentConvId.value || streaming.value) return
  const next = msg.my_feedback === vote ? 'none' : vote
  const res = await setMessageFeedback(currentConvId.value, msg.id, next)
  msg.my_feedback = res.vote
}

async function shareMessage(msg: ChatMessage) {
  if (!currentConvId.value || streaming.value) return
  const res = await createMessageShare(currentConvId.value, msg.id)
  shareLink.value = `${window.location.origin}${res.path}`
  shareCopied.value = false
  try {
    shareQr.value = await qrCodeDataUrl(shareLink.value, 220)
  } catch {
    shareQr.value = ''
  }
  shareVisible.value = true
}

async function copyShareLink() {
  try {
    await navigator.clipboard.writeText(shareLink.value)
  } catch {
    const area = document.createElement('textarea')
    area.value = shareLink.value
    document.body.appendChild(area)
    area.select()
    document.execCommand('copy')
    area.remove()
  }
  shareCopied.value = true
  ElMessage.success('分享链接已复制')
}

async function regenerateMessage(msg: ChatMessage) {
  if (!currentConvId.value || streaming.value) return
  stopSpeaking()
  const convId = currentConvId.value
  messages.value = messages.value.filter((item) => item.id !== msg.id)
  suggestions.value = []
  resetConclusionTypewriter()
  streaming.value = true
  streamStatus.value = ''
  scrollToBottom()
  abortStreamRequest()
  streamAbort = new AbortController()
  await streamRegenerate(
    convId,
    msg.id,
    { deep_think: deepThink.value, online_search: onlineSearch.value },
    {
      onToken(chunk) {
        if (chunk) streamStatus.value = ''
        appendStreamChunk(chunk)
      },
      onReplace(content) {
        pushConclusion(content, true)
      },
      onDetail(content) {
        acceptStreamDetail(content)
      },
      onStatus(text) {
        streamStatus.value = text
      },
      onDone(event) {
        queueStreamFinish(async () => {
          const keepOpen = streamDetailOpen.value
          streamAbort = null
          if (currentConvId.value === convId) {
            messages.value = await getMessages(convId)
          }
          suggestions.value = event.suggestions || []
          const last = [...messages.value].reverse().find((item) => item.role === 'assistant')
          streaming.value = false
          streamStatus.value = ''
          resetConclusionTypewriter()
          if (keepOpen && last) {
            const detail = splitLegalAnswer(last.content).detail
            if (detail) {
              detailOpen.value = { ...detailOpen.value, [last.id]: true }
              detailShown.value = { ...detailShown.value, [last.id]: detail }
              detailHtml.value = { ...detailHtml.value, [last.id]: legalChatHtml(detail) }
            }
          }
          scrollToBottom()
        })
      },
      onError(err) {
        streamAbort = null
        pendingFinish = null
        streaming.value = false
        streamStatus.value = ''
        resetConclusionTypewriter()
        ElMessage.error(err)
        if (currentConvId.value === convId) {
          getMessages(convId).then((rows) => { messages.value = rows }).catch(() => null)
        }
      },
    },
    { signal: streamAbort.signal },
  )
}

</script>



<template>
  <div class="chat-panel">
    <aside class="chat-sidebar">

      <div class="sidebar-header">
        <div class="sidebar-brand">
          <FaIcon class="sidebar-brand-icon" name="comments" />
          <span class="sidebar-title">对话列表</span>
        </div>
        <button type="button" class="sidebar-new-btn" @click="newConversation">+ 新对话</button>
      </div>

      <div class="conv-list">
        <div
          v-for="conv in conversations"
          :key="conv.id"
          class="conv-item"
          :class="{ active: conv.id === currentConvId }"
          @click="selectConversation(conv.id)"
        >
          <div class="conv-item__main">
            <div class="conv-title">{{ conv.title }}</div>
            <div class="conv-preview">{{ conv.last_message || '暂无消息' }}</div>
          </div>
          <button type="button" class="conv-delete" title="删除" @click.stop="removeConversation(conv.id)">
            ×
          </button>
        </div>

        <el-empty v-if="!conversations.length" description="暂无对话" :image-size="48" />

      </div>

    </aside>



    <main class="chat-main">

      <div class="chat-topbar">
        <div class="topbar-title">
          <FaIcon class="topbar-icon" name="robot" />
          <span>{{ conversations.find(c => c.id === currentConvId)?.title || '法律咨询' }}</span>
        </div>
        <div class="topbar-actions">
          <el-button text size="small" @click="newConversation">+ 新对话</el-button>
          <el-switch v-model="onlineSearch" active-text="联网检索" size="small" />
          <el-switch v-model="deepThink" active-text="深度思考" size="small" />
        </div>
      </div>

      <div ref="messageListRef" class="message-list">

        <div v-if="!messages.length && !streaming" class="welcome">

          <FaIcon class="welcome-icon" name="robot" />

          <h2>{{ welcomeTitle }}</h2>

          <p>{{ welcomeDesc }}</p>

          <div class="quick-grid">

            <div v-for="q in QUICK_ENTRIES" :key="q.label" class="quick-card" @click="quickStart(q.text)">

              <FaIcon class="quick-icon" :name="q.icon" />

              <span class="quick-label">{{ q.label }}</span>

            </div>

          </div>

          <div class="welcome-prompts">
            <div class="welcome-prompts-head">
              <span>试试这么问：</span>
              <button type="button" class="welcome-prompts-refresh" @click="refreshWelcomePrompts">换一换</button>
            </div>
            <div class="welcome-prompt-chips">
              <button
                v-for="(p, i) in welcomePrompts"
                :key="`${welcomePromptIndex}-${i}`"
                type="button"
                class="welcome-prompt-chip"
                :title="p"
                @click="applyWelcomePrompt(p)"
              >
                {{ p }}
              </button>
            </div>
          </div>

        </div>



        <div v-for="msg in messages" :key="msg.id" class="message-row" :class="msg.role">

          <div class="msg-avatar" :class="{ 'has-photo': msg.role === 'assistant' ? !!aiUi.avatar : !!userStore.avatar }">
            <img v-if="msg.role === 'assistant' && aiUi.avatar" :src="aiUi.avatar" alt="" />
            <img v-else-if="msg.role === 'user' && userStore.avatar" :src="userStore.avatar" alt="" />
            <template v-else>{{ msg.role === 'user' ? '我' : 'AI' }}</template>
          </div>

          <div class="msg-body">

            <div class="msg-bubble" :class="msg.role">

              <img

                v-if="msg.content_type === 'image' && msg.metadata?.image_url"

                :src="msg.metadata.image_url"

                class="msg-image"

              />

              <template v-else-if="msg.role === 'assistant'">
                <div class="msg-text msg-markdown" v-html="legalChatHtml(splitLegalAnswer(msg.content).summary)" />
                <button
                  v-if="splitLegalAnswer(msg.content).detail"
                  type="button"
                  class="detail-toggle"
                  @click="toggleDetail(msg.id, splitLegalAnswer(msg.content).detail)"
                >
                  {{ detailOpen[msg.id] ? '收起详细内容' : '查看详细内容' }}
                </button>
                <p v-if="splitLegalAnswer(msg.content).detail && !detailOpen[msg.id]" class="detail-hint">
                  上面是根据现行规定整理的结论。需要地方补充和法条原文时，再查看详细内容。
                </p>
                <div
                  v-if="detailOpen[msg.id] && detailHtml[msg.id]"
                  class="msg-text msg-markdown detail-body"
                  v-html="detailHtml[msg.id]"
                />
              </template>
              <pre v-else class="msg-text">{{ msg.content }}</pre>

            </div>

            <ChatReplyActions
              v-if="msg.role === 'assistant' && hasReplyActions"
              :show-copy="aiUi.copy"
              :show-regenerate="aiUi.regenerate"
              :show-like="aiUi.like"
              :show-dislike="aiUi.dislike"
              :show-speak="aiUi.speak"
              :show-share="aiUi.share"
              :liked="msg.my_feedback === 'like'"
              :disliked="msg.my_feedback === 'dislike'"
              :speaking="speakingId === msg.id"
              :disabled="streaming"
              @copy="copyMessage(msg)"
              @regenerate="regenerateMessage(msg)"
              @like="voteMessage(msg, 'like')"
              @dislike="voteMessage(msg, 'dislike')"
              @speak="speakMessage(msg)"
              @share="shareMessage(msg)"
            />

          </div>

        </div>



        <div v-if="streaming" class="message-row assistant">

          <div class="msg-avatar" :class="{ 'has-photo': !!aiUi.avatar }">
            <img v-if="aiUi.avatar" :src="aiUi.avatar" alt="" />
            <template v-else>AI</template>
          </div>

          <div class="msg-body">

            <div v-if="!streamRaw && !streamStatus" class="thinking">

              <span class="thinking-dots"><i /><i /><i /></span>

              {{ deepThink ? '深度思考中，正在分析法律依据...' : 'AI 正在分析...' }}

            </div>

            <div v-else-if="!streamRaw && streamStatus" class="thinking">

              <span class="thinking-dots"><i /><i /><i /></span>

              {{ streamStatus }}

            </div>

            <div v-else class="msg-bubble assistant">

              <div
                v-for="(block, index) in streamBlocks"
                :key="index"
                class="msg-text msg-markdown stream-markdown"
                v-html="block"
              />
              <div v-if="streamTailHtml" class="msg-text msg-markdown stream-markdown stream-tail" v-html="streamTailHtml" />
              <div class="stream-slot">
                <div v-if="!streamDetail" class="stream-progress" aria-label="正在整理详细内容">
                  <div class="stream-progress__track"><i class="stream-progress__bar" /></div>
                </div>
                <button
                  v-else
                  type="button"
                  class="detail-toggle"
                  @click="toggleLiveDetail"
                >
                  {{ streamDetailOpen ? '收起详细内容' : '查看详细内容' }}
                </button>
              </div>
              <div
                v-if="streamDetailOpen && streamDetailHtml"
                class="msg-text msg-markdown detail-body"
                v-html="streamDetailHtml"
              />

            </div>

          </div>

        </div>

        <p v-if="showResultDisclaimer" class="msg-disclaimer" role="note">{{ AI_DISCLAIMER }}</p>

      </div>



      <div v-if="suggestions.length" class="suggestions">

        <el-tag v-for="(s, i) in suggestions" :key="i" class="chip" effect="plain" round @click="sendSuggestion(s)">

          {{ s }}

        </el-tag>

      </div>



      <div class="input-area">
        <div class="composer">
          <div v-if="pendingImageUrl" class="composer-attach">
            <el-tag size="small" type="success" closable @close="pendingImageUrl = ''">已选图片</el-tag>
          </div>

          <el-input
            v-model="inputText"
            class="composer-input"
            type="textarea"
            :autosize="{ minRows: 2, maxRows: 6 }"
            placeholder="输入法律问题，Enter 发送，Shift+Enter 换行"
            maxlength="5000"
            :disabled="streaming"
            @keydown="handleKeydown"
          />

          <div class="composer-footer">
            <div class="composer-tools">
              <button
                type="button"
                class="tool-btn"
                :class="{ 'tool-btn--active': showPanel }"
                :title="showPanel ? '收起更多' : '更多功能'"
                @click="showPanel = !showPanel"
              >
                <span class="tool-btn__glyph">{{ showPanel ? '✕' : '+' }}</span>
              </button>
              <button
                type="button"
                class="tool-btn"
                :class="{ 'tool-btn--active': voiceRecording }"
                :title="voiceRecording ? '停止录音' : voiceTranscribing ? '正在识别' : '语音输入'"
                :disabled="voiceTranscribing"
                @click="showVoiceTip"
              >
                <FaIcon class="tool-btn__glyph" name="microphone" />
              </button>
              <el-upload
                :show-file-list="false"
                accept="image/*"
                :auto-upload="false"
                :on-change="(f: { raw?: File }) => f.raw && handleImageUpload(f.raw)"
              >
                <button type="button" class="tool-btn" title="上传图片">
                  <FaIcon class="tool-btn__glyph" name="image" />
                </button>
              </el-upload>
              <span v-if="deepThink" class="deep-badge" title="顶部可关闭深度思考">
                <span class="deep-badge__dot" aria-hidden="true" />
                深度思考已开启
              </span>
            </div>
            <div class="composer-meta">
              <span class="composer-count">{{ inputCharCount }} / 5000</span>
              <WorkspaceQuotaHint :quota-keys="['daily_chat']" />
            </div>
            <el-button
              type="primary"
              class="composer-send"
              :disabled="!inputText.trim() || streaming"
              :loading="streaming"
              @click="handleSend"
            >
              发送
            </el-button>
          </div>
        </div>
      </div>



      <div v-if="showPanel" class="func-panel">

        <div class="panel-item" @click="showImageTip"><FaIcon name="image" /><small>图片</small></div>

        <div class="panel-item" @click="showFileTip"><FaIcon name="paperclip" /><small>文件</small></div>

      </div>

    </main>

    <el-dialog v-model="shareVisible" title="分享这条回复" width="420px" align-center>
      <div class="share-dialog">
        <img v-if="shareQr" :src="shareQr" alt="分享二维码" class="share-qr" />
        <p class="share-tip">扫码或打开链接即可查看这条回复，无需登录。</p>
        <el-input :model-value="shareLink" readonly />
        <el-button type="primary" class="share-copy" @click="copyShareLink">
          {{ shareCopied ? '已复制' : '复制链接' }}
        </el-button>
      </div>
    </el-dialog>
  </div>
</template>



<style scoped>

.chat-panel {
  display: flex;
  flex: 1;
  height: 100%;
  min-width: 0;
  background: var(--ft-bg);
}

.chat-topbar {

  display: flex;

  justify-content: space-between;

  align-items: center;

  padding: 12px 24px;

  background: var(--ft-card-bg);

  border-bottom: 1px solid var(--ft-border);

  flex-shrink: 0;

}



.topbar-title {

  display: flex;

  align-items: center;

  gap: 8px;

  font-size: 15px;

  font-weight: 500;

  color: var(--ft-text);

}



.topbar-icon { font-size: 20px; }



.topbar-actions {

  display: flex;

  align-items: center;

  gap: 12px;

}



.chat-sidebar {
  width: 280px;
  background: linear-gradient(180deg, #fafbfd 0%, #f8fafc 100%);
  border-right: 1px solid #e8edf5;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.sidebar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  padding: 18px 16px 14px;
  border-bottom: 1px solid #e8edf5;
  background: #fff;
}

.sidebar-brand {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.sidebar-brand-icon {
  font-size: 16px;
  line-height: 1;
}

.sidebar-title {
  font-weight: 700;
  color: #0f172a;
  font-size: 15px;
  letter-spacing: 0.02em;
}

.sidebar-new-btn {
  flex-shrink: 0;
  border: none;
  padding: 7px 14px;
  font-size: 12px;
  font-weight: 400;
  color: #fff;
  background: linear-gradient(90deg, #34d399 0%, #10b981 52%, #059669 100%);
  border-radius: 999px;
  cursor: pointer;
  box-shadow: 0 8px 18px rgba(16, 185, 129, 0.28);
  transition: transform 0.15s, box-shadow 0.15s;
}

.sidebar-new-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 8px 18px rgba(16, 185, 129, 0.36);
}

.conv-list {
  flex: 1;
  overflow-y: auto;
  padding: 12px 10px;
}

.conv-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 12px 12px 12px 16px;
  border-radius: 12px;
  cursor: pointer;
  margin-bottom: 6px;
  position: relative;
  border: 1px solid transparent;
  background: #fff;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
  transition: border-color 0.15s, box-shadow 0.15s, background 0.15s;
}

.conv-item:hover {
  border-color: #e2e8f0;
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.06);
}

.conv-item.active {
  background: #ecfdf5;
  border-color: #10b981;
  box-shadow: 0 4px 16px rgba(16, 185, 129, 0.16);
}

.conv-item.active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 10px;
  bottom: 10px;
  width: 3px;
  border-radius: 0 3px 3px 0;
  background: linear-gradient(180deg, #34d399 0%, #10b981 52%, #059669 100%);
}

.conv-item__main {
  flex: 1;
  min-width: 0;
}

.conv-title {
  font-size: 13px;
  font-weight: 600;
  color: #0f172a;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  line-height: 1.4;
}

.conv-item.active .conv-title {
  color: #047857;
}

.conv-item.active .conv-preview {
  color: #059669;
}

.conv-preview {
  font-size: 12px;
  color: #64748b;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-top: 4px;
  line-height: 1.45;
}

.conv-delete {
  flex-shrink: 0;
  width: 24px;
  height: 24px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: #94a3b8;
  font-size: 18px;
  line-height: 1;
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.15s, background 0.15s, color 0.15s;
}

.conv-item:hover .conv-delete {
  opacity: 1;
}

.conv-delete:hover {
  background: #fef2f2;
  color: #dc2626;
}



.chat-main { flex: 1; display: flex; flex-direction: column; min-width: 0; }



.message-list { flex: 1; overflow-y: auto; padding: 24px; }



.welcome { text-align: center; padding: 60px 24px; color: var(--ft-text-secondary); }

.welcome-icon { font-size: 56px; margin-bottom: 12px; }

.welcome h2 { color: var(--ft-text); margin-bottom: 8px; font-size: 22px; font-weight: 500; }

.welcome p { max-width: 480px; margin: 0 auto 28px; line-height: 1.6; }



.quick-grid {

  display: grid;

  grid-template-columns: repeat(4, 1fr);

  gap: 12px;

  max-width: 560px;

  margin: 0 auto;

}

.quick-card {

  background: var(--ft-card-bg);

  border: 1px solid var(--ft-border);

  border-radius: 20px;

  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.04);

  padding: 16px 8px;

  cursor: pointer;

  transition: all 0.2s;

  display: flex;

  flex-direction: column;

  align-items: center;

  gap: 6px;

}

.quick-card:hover {

  border-color: var(--ft-primary);

  box-shadow: var(--ft-shadow);

  transform: translateY(-2px);

}

.welcome-prompts {
  max-width: 920px;
  margin: 28px auto 0;
  text-align: left;
  padding: 0 12px;
}

.welcome-prompts-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  font-size: 13px;
  color: var(--ft-text-secondary);
}

.welcome-prompts-refresh {
  border: none;
  background: none;
  color: var(--ft-primary);
  font-size: 12px;
  cursor: pointer;
  padding: 0;
}

.welcome-prompts-refresh:hover {
  text-decoration: underline;
}

.welcome-prompt-chips {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.welcome-prompt-chip {
  min-width: 0;
  text-align: left;
  padding: 10px 12px;
  min-height: 40px;
  border: 1px solid var(--ft-border);
  border-radius: 16px;
  background: var(--ft-card-bg);
  font-size: 14px;
  line-height: 1.45;
  color: var(--ft-text);
  cursor: pointer;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  transition: border-color 0.15s, background 0.15s, box-shadow 0.15s;
}

.welcome-prompt-chip:hover {
  border-color: var(--ft-primary);
  background: #f8fafc;
  box-shadow: 0 8px 24px rgba(16, 185, 129, 0.08);
}

@media (max-width: 720px) {
  .welcome-prompt-chips {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

.quick-icon { font-size: 24px; color: var(--ft-primary); }

.quick-label { font-size: 13px; color: var(--ft-text); }



.message-row { display: flex; gap: 12px; margin-bottom: 24px; }

.message-row.user { flex-direction: row-reverse; }



.msg-avatar {

  width: 36px;

  height: 36px;

  border-radius: 50%;

  display: flex;

  align-items: center;

  justify-content: center;

  font-size: 12px;

  flex-shrink: 0;

  background: #EBF0F7;

  color: var(--ft-primary);

  overflow: hidden;

}

.msg-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.share-dialog {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.share-qr {
  width: 220px;
  height: 220px;
}

.share-tip {
  margin: 0;
  font-size: 13px;
  color: var(--ft-text-secondary, #64748b);
  text-align: center;
}

.share-copy {
  align-self: stretch;
}

.message-row.user .msg-avatar { background: var(--ft-primary); color: #fff; }



.msg-body { max-width: 70%; display: flex; flex-direction: column; gap: 4px; }

.message-row.user .msg-body { align-items: flex-end; }



.msg-bubble { padding: 12px 16px; border-radius: 12px; }

.msg-bubble.user {

  background: var(--ft-primary);

  color: #fff;

  border-bottom-right-radius: 4px;

}

.msg-bubble.assistant {

  background: var(--ft-card-bg);

  color: var(--ft-text);

  border-bottom-left-radius: 4px;

  box-shadow: var(--ft-shadow);

  overflow-x: auto;

  max-width: 100%;

}



.msg-text {

  margin: 0;

  font-family: inherit;

  font-size: 14px;

  line-height: 1.6;

  white-space: pre-wrap;

  word-break: break-word;

}

.msg-markdown {
  white-space: normal;
}

.detail-toggle {
  margin-top: 10px;
  border: 1px solid #d1fae5;
  background: #f0fdf4;
  color: #047857;
  border-radius: 999px;
  padding: 6px 12px;
  font-size: 13px;
  cursor: pointer;
}

.detail-hint {
  margin: 8px 0 0;
  color: #64748b;
  font-size: 12px;
  line-height: 1.6;
}

.detail-body {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #e2e8f0;
}

.msg-markdown :deep(h1),
.msg-markdown :deep(h2),
.msg-markdown :deep(h3) {
  margin: 0.6em 0 0.35em;
  font-weight: 600;
  line-height: 1.35;
  color: #0f172a;
}

.msg-markdown :deep(h1) { font-size: 1.15em; }
.msg-markdown :deep(h2) { font-size: 1.05em; }
.msg-markdown :deep(h3) { font-size: 1em; }

.msg-markdown :deep(p) {
  margin: 0.35em 0;
}

.msg-markdown :deep(ul),
.msg-markdown :deep(ol) {
  margin: 0.35em 0;
  padding-left: 1.25em;
}

.msg-markdown :deep(li) {
  margin: 0.2em 0;
}

.msg-markdown :deep(strong) {
  font-weight: 600;
  color: #1e293b;
}

.msg-markdown :deep(blockquote) {
  margin: 0.5em 0;
  padding: 0.35em 0.75em;
  border-left: 3px solid #94a3b8;
  color: #475569;
  background: #f8fafc;
  border-radius: 0 6px 6px 0;
}

.msg-markdown :deep(code) {
  font-family: ui-monospace, monospace;
  font-size: 0.92em;
  background: #f1f5f9;
  padding: 0.1em 0.35em;
  border-radius: 4px;
}

.msg-markdown :deep(pre) {
  margin: 0.5em 0;
  padding: 10px 12px;
  background: #f1f5f9;
  border-radius: 8px;
  overflow-x: auto;
}

.msg-markdown :deep(pre code) {
  padding: 0;
  background: none;
}

.msg-markdown :deep(table) {
  width: 100%;
  max-width: 100%;
  margin: 0.6em 0;
  border-collapse: collapse;
  font-size: 13px;
  line-height: 1.5;
  table-layout: auto;
}

.msg-markdown :deep(thead) {
  background: #f1f5f9;
}

.msg-markdown :deep(th),
.msg-markdown :deep(td) {
  border: 1px solid #e2e8f0;
  padding: 8px 10px;
  text-align: left;
  vertical-align: top;
  min-width: 72px;
  word-break: break-word;
}

.msg-markdown :deep(th) {
  font-weight: 600;
  color: #1e293b;
  background: #f8fafc;
}

.msg-markdown :deep(hr) {
  border: none;
  border-top: 1px solid #e2e8f0;
  margin: 0.75em 0;
}

.stream-markdown {
  font-size: 14px;
  line-height: 1.75;
}

.stream-slot {
  min-height: 36px;
  margin-top: 12px;
}

.stream-progress {
  display: flex;
  align-items: center;
  height: 36px;
}

.stream-progress__track {
  position: relative;
  width: 100%;
  height: 8px;
  overflow: hidden;
  border-radius: 999px;
  background: #d1fae5;
}

.stream-progress__bar {
  position: absolute;
  top: 0;
  left: -40%;
  width: 40%;
  height: 100%;
  border-radius: inherit;
  background: #059669;
  animation: stream-progress-slide 1.1s ease-in-out infinite;
}

@keyframes stream-progress-slide {
  0% { left: -40%; }
  100% { left: 100%; }
}



.msg-image { max-width: 300px; border-radius: var(--ft-radius); }

.msg-disclaimer {
  margin: 12px 0 4px;
  padding: 10px 14px;
  font-size: 12px;
  line-height: 1.55;
  color: var(--ft-text-secondary, #718096);
  background: var(--ft-fill-muted, #f7fafc);
  border-radius: 8px;
  border: 1px solid var(--ft-border, #edf2f7);
}

.cursor { animation: blink 1s infinite; display: inline-block; margin-left: 2px; }

@keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }



.thinking {

  display: flex;

  align-items: center;

  gap: 8px;

  padding: 12px 16px;

  background: var(--ft-card-bg);

  border-radius: 12px;

  box-shadow: var(--ft-shadow);

  font-size: 14px;

  color: var(--ft-text-secondary);

}



.thinking-dots { display: flex; gap: 4px; }

.thinking-dots i {

  display: block;

  width: 6px;

  height: 6px;

  background: var(--ft-primary);

  border-radius: 50%;

  animation: bounce 1.4s infinite ease-in-out both;

}

.thinking-dots i:nth-child(1) { animation-delay: -0.32s; }

.thinking-dots i:nth-child(2) { animation-delay: -0.16s; }

@keyframes bounce {

  0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }

  40% { transform: scale(1); opacity: 1; }

}



.suggestions {

  display: flex;

  flex-wrap: wrap;

  gap: 8px;

  padding: 8px 24px;

  background: var(--ft-card-bg);

  border-top: 1px solid var(--ft-border);

}

.chip { cursor: pointer; }



.input-area {
  padding: 12px 24px 16px;
  background: var(--ft-card-bg);
  border-top: 1px solid var(--ft-border);
}

.composer {
  display: flex;
  flex-direction: column;
  max-width: 920px;
  margin: 0 auto;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  background: #fff;
  box-shadow: 0 2px 14px rgba(15, 23, 42, 0.06);
  overflow: hidden;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.composer:focus-within {
  border-color: #94a3b8;
  box-shadow: 0 0 0 3px rgba(44, 82, 130, 0.1);
}

.composer-attach {
  padding: 10px 14px 0;
}

.composer-input :deep(.el-textarea__inner) {
  border: none;
  box-shadow: none !important;
  padding: 14px 16px 6px;
  resize: none;
  background: transparent;
  font-size: 14px;
  line-height: 1.6;
  color: var(--ft-text);
}

.composer-input :deep(.el-textarea__inner:focus) {
  box-shadow: none !important;
}

.composer-input :deep(.el-textarea__inner::placeholder) {
  color: #94a3b8;
}

.composer-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px 12px;
  padding: 8px 10px 10px 12px;
  border-top: 1px solid #f1f5f9;
  background: linear-gradient(180deg, #fafbfc 0%, #f8fafc 100%);
}

.composer-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  order: 2;
  margin-left: auto;
}

.composer-count {
  font-size: 12px;
  color: #94a3b8;
  white-space: nowrap;
}

.composer-send {
  order: 3;
}

.composer-tools {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  min-width: 0;
  flex: 1;
}

.tool-btn {
  width: 36px;
  height: 36px;
  padding: 0;
  border: 1px solid #e2e8f0;
  border-radius: 999px;
  background: #fff;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: border-color 0.22s ease, background 0.22s ease, transform 0.18s cubic-bezier(0.22, 1, 0.36, 1), box-shadow 0.22s ease;
}

.tool-btn:hover {
  border-color: #cbd5e1;
  background: #f8fafc;
}

.tool-btn--active {
  border-color: #a7f3d0;
  background: #ecfdf5;
  color: var(--ft-primary);
}

.tool-btn__glyph {
  font-size: 16px;
  line-height: 1;
}

.deep-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 18px;
  font-size: 12px;
  font-weight: 600;
  color: #b45309;
  background: linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%);
  border: 1px solid #fcd34d;
  white-space: nowrap;
}

.deep-badge__dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #f59e0b;
  box-shadow: 0 0 0 2px rgba(245, 158, 11, 0.25);
  animation: deep-pulse 1.6s ease-in-out infinite;
}

@keyframes deep-pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.65; transform: scale(0.85); }
}

.composer-send {
  flex-shrink: 0;
  min-width: 76px;
  height: 36px;
  border-radius: 999px;
  font-weight: 400;
}

.composer-tools :deep(.el-upload) {
  display: inline-flex;
  line-height: 0;
}



.func-panel {

  display: flex;

  gap: 32px;

  padding: 12px 24px;

  background: var(--ft-card-bg);

  border-top: 1px solid var(--ft-border);

}

.panel-item {

  display: flex;

  flex-direction: column;

  align-items: center;

  gap: 4px;

  cursor: pointer;

  font-size: 24px;

  color: var(--ft-text-secondary);

}

.panel-item small { font-size: 12px; }



@media (max-width: 768px) {
  .chat-sidebar { display: none; }
  .quick-grid { grid-template-columns: repeat(2, 1fr); }
}

</style>


