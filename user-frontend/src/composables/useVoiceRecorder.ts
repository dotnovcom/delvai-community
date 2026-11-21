import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { transcribeVoiceFile } from '../api/legal'
import { blobToWav } from '../utils/wavEncode'

export function useVoiceRecorder(hooks: {
  onText?: (text: string) => void
  onError?: (err: Error) => void
  /** 返回 false 时不开始录音，也不把音频发给识别接口 */
  beforeSend?: () => Promise<boolean>
}) {
  const recording = ref(false)
  const transcribing = ref(false)
  let mediaRecorder: MediaRecorder | null = null
  let mediaStream: MediaStream | null = null
  let audioChunks: Blob[] = []

  async function canSend() {
    if (!hooks.beforeSend) return true
    return hooks.beforeSend()
  }

  async function start() {
    if (recording.value || transcribing.value) return
    if (!await canSend()) return
    if (!navigator.mediaDevices?.getUserMedia) {
      ElMessage.warning('当前浏览器不支持录音')
      return
    }
    recording.value = true
    navigator.mediaDevices.getUserMedia({ audio: true }).then((stream) => {
      if (!recording.value) {
        stream.getTracks().forEach((track) => track.stop())
        return
      }
      mediaStream = stream
      audioChunks = []
      mediaRecorder = new MediaRecorder(stream)
      mediaRecorder.ondataavailable = (event) => {
        if (event.data?.size) audioChunks.push(event.data)
      }
      mediaRecorder.onstop = async () => {
        mediaStream?.getTracks().forEach((track) => track.stop())
        mediaStream = null
        if (!audioChunks.length) return
        const raw = new Blob(audioChunks, { type: mediaRecorder?.mimeType || 'audio/webm' })
        transcribing.value = true
        try {
          if (!await canSend()) return
          const wav = raw.type.includes('wav') ? raw : await blobToWav(raw)
          const file = new File([wav], 'voice.wav', { type: 'audio/wav' })
          const res = await transcribeVoiceFile(file)
          const text = (res.text || '').trim()
          if (text) hooks.onText?.(text)
          else ElMessage.warning('未识别到语音')
        } catch (err) {
          const error = err instanceof Error ? err : new Error('语音识别失败')
          hooks.onError?.(error)
          ElMessage.error(error.message)
        } finally {
          transcribing.value = false
        }
      }
      mediaRecorder.start()
    }).catch(() => {
      recording.value = false
      ElMessage.warning('无法访问麦克风')
    })
  }

  function stop() {
    if (!recording.value) return
    recording.value = false
    if (mediaRecorder && mediaRecorder.state !== 'inactive') mediaRecorder.stop()
    else {
      mediaStream?.getTracks().forEach((track) => track.stop())
      mediaStream = null
    }
  }

  function toggle() {
    if (recording.value) stop()
    else start()
  }

  return { recording, transcribing, start, stop, toggle }
}
