import { computed } from 'vue'
import { usePublicConfig } from './usePublicConfig'

export interface AuthMethodsConfig {
  loginPhone: boolean
  loginPhoneSms: boolean
  loginEmail: boolean
  loginEmailSms: boolean
  loginWechat: boolean
  registerPhone: boolean
  registerEmail: boolean
  inviteEnabled: boolean
  requirePhoneBind: boolean
  requireEmailBind: boolean
}

function parseBool(value: string | undefined, defaultValue: boolean): boolean {
  if (value === undefined || value === '') return defaultValue
  return value === 'true' || value === '1'
}

export function parseAuthMethodsFromConfig(
  cfg: Record<string, string | undefined>,
): AuthMethodsConfig {
  return {
    loginPhone: parseBool(cfg.auth_login_phone_enabled, true),
    loginPhoneSms: parseBool(cfg.auth_login_phone_sms_enabled, true),
    loginEmail: parseBool(cfg.auth_login_email_enabled, true),
    loginEmailSms: parseBool(cfg.auth_login_email_sms_enabled, true),
    loginWechat: parseBool(cfg.auth_login_wechat_enabled, true),
    registerPhone: parseBool(cfg.auth_register_phone_enabled, true),
    registerEmail: parseBool(cfg.auth_register_email_enabled, true),
    inviteEnabled: parseBool(cfg.auth_invite_code_enabled, true),
    requirePhoneBind: parseBool(cfg.auth_require_phone_bind, false),
    requireEmailBind: parseBool(cfg.auth_require_email_bind, false),
  }
}

export function userNeedsBinding(user: {
  phone?: string | null
  email?: string | null
  binding_required_phone?: boolean
  binding_required_email?: boolean
  is_admin?: boolean
} | null | undefined): boolean {
  if (!user || user.is_admin) return false
  if (user.binding_required_phone || user.binding_required_email) return true
  return false
}

export function useAuthConfig() {
  const { config, load, loaded } = usePublicConfig()

  const auth = computed(() => parseAuthMethodsFromConfig(config.value))

  const hasAnyLogin = computed(
    () => auth.value.loginPhone || auth.value.loginEmail || auth.value.loginWechat,
  )

  const hasAnyRegister = computed(
    () => auth.value.registerPhone || auth.value.registerEmail,
  )

  return { auth, hasAnyLogin, hasAnyRegister, load, loaded, config }
}
