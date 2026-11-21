import { parseResponseDetail } from './error'

export function apiErrorMessage(error: unknown, fallback: string): string {
  const detail = (error as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
  return parseResponseDetail(detail, fallback)
}
