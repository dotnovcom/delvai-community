import { ElMessage } from 'element-plus'
import { get } from '../utils/request'
import { ensureLoggedIn } from './useLoginDialog'

export interface SpeechAccessInput {
  feature?: string
  quotas: string[]
}

/** 登录且具备对应功能权限、额度或积分后，才允许把音频发给识别接口。 */
export async function ensureSpeechAccess(input: SpeechAccessInput): Promise<boolean> {
  if (!await ensureLoggedIn()) return false
  const params = new URLSearchParams()
  if (input.feature) params.set('feature', input.feature)
  if (input.quotas.length) params.set('quotas', input.quotas.join(','))
  try {
    const res = await get<{ allowed: boolean; message: string }>(
      `/api/v1/membership/access?${params.toString()}`,
      { skipGlobalErrorHandler: true },
    )
    if (!res.allowed) {
      ElMessage.warning(res.message || '额度不足，无法使用语音识别')
      return false
    }
    return true
  } catch {
    ElMessage.warning('暂时无法确认额度，请稍后重试')
    return false
  }
}
