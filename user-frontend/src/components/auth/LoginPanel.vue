<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import {
  phoneLogin,
  emailLogin,
  sendSms,
  sendEmailCode,
  createQrcode,
  getQrcodeStatus,
  discoverEnterpriseSso,
  getEnterpriseSsoAuthorizeUrl,
  listPublicEnterpriseSso,
} from '../../api/auth'
import { useUserStore } from '../../store/user'
import { saveRememberedLogin, loadRememberedLogin, clearRememberedLogin } from '../../utils/authStorage'
import { qrCodeDataUrl } from '../../utils/qrCodeDataUrl'
import { useAuthConfig } from '../../composables/useAuthConfig'
import { useBrandLabels } from '../../composables/useBrandLabels'
import { setAuthView, useLoginDialog, type LoginMethod } from '../../composables/useLoginDialog'
import { parseApiError } from '../../utils/error'

const props = withDefaults(
  defineProps<{
    redirectPath?: string
    initialNotice?: string
  }>(),
  { initialNotice: '' },
)

const emit = defineEmits<{ success: [] }>()

const userStore = useUserStore()
const { auth, hasAnyLogin, hasAnyRegister, load: loadAuth } = useAuthConfig()
const { load: loadBrand } = useBrandLabels()
const { loginMethod } = useLoginDialog()

const wechatLoginHint = computed(() => '请使用微信扫码登录')

const PHONE_RE = /^1[3-9]\d{9}$/
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

const account = ref('')
const phone = ref('')
const email = ref('')
const password = ref('')
const code = ref('')
const countdown = ref(0)
const loading = ref(false)
const rememberMe = ref(true)
const configReady = ref(false)
const loginNotice = ref('')

const ssoEnterprise = ref<{ enterprise_id: number; name: string; email_domain: string } | null>(null)
const publicSsoList = ref<{ id: number; name: string; email_domain: string; provider: string }[]>([])
let ssoDiscoverTimer: ReturnType<typeof setTimeout> | null = null

const qrcodeTicket = ref('')
const qrcodeImage = ref('')
const qrcodeStatus = ref<'pending' | 'scanned' | 'confirmed' | 'expired'>('pending')
let pollTimer: ReturnType<typeof setInterval> | null = null
let smsTimer: ReturnType<typeof setInterval> | null = null

const isPhoneValid = computed(() => PHONE_RE.test(phone.value))
const isEmailValid = computed(() => EMAIL_RE.test(email.value.trim()))
const canPasswordLogin = computed(() => !!account.value.trim() && !!password.value)
const canPhoneLogin = computed(() => isPhoneValid.value && !!code.value.trim())
const canEmailLogin = computed(() => isEmailValid.value && !!code.value.trim())
const formTab = computed(() => (loginMethod.value === 'wechat' ? 'password' : loginMethod.value))

function detectAccountKind(raw: string): 'phone' | 'email' | null {
  const v = raw.trim()
  if (PHONE_RE.test(v)) return 'phone'
  if (EMAIL_RE.test(v)) return 'email'
  return null
}

const loginTabs = computed(() => {
  const list: { name: LoginMethod; label: string }[] = []
  if (auth.value.loginPhone || auth.value.loginEmail) {
    list.push({ name: 'password', label: '帐密登录' })
  }
  if (auth.value.loginPhone && auth.value.loginPhoneSms) {
    list.push({ name: 'phone', label: '手机登录' })
  }
  if (auth.value.loginEmail && auth.value.loginEmailSms) {
    list.push({ name: 'email', label: '邮箱登录' })
  }
  return list
})

function pickDefaultMethod() {
  if (loginMethod.value === 'wechat' && auth.value.loginWechat) return
  if (loginTabs.value.some((t) => t.name === loginMethod.value)) return
  const first = loginTabs.value[0]?.name
  if (first) loginMethod.value = first
  else if (auth.value.loginWechat) loginMethod.value = 'wechat'
}

watch(loginTabs, () => pickDefaultMethod(), { immediate: true })

watch(
  () => props.initialNotice,
  (val) => {
    if (val) loginNotice.value = val
  },
  { immediate: true },
)

function scheduleSsoDiscover(value: string) {
  if (ssoDiscoverTimer) clearTimeout(ssoDiscoverTimer)
  ssoEnterprise.value = null
  if (!EMAIL_RE.test(value.trim())) return
  ssoDiscoverTimer = setTimeout(async () => {
    try {
      const res = await discoverEnterpriseSso(value.trim())
      if (res.found && res.provider === 'oidc' && res.enterprise_id && res.name && res.email_domain) {
        ssoEnterprise.value = {
          enterprise_id: res.enterprise_id,
          name: res.name,
          email_domain: res.email_domain,
        }
      }
    } catch {
      ssoEnterprise.value = null
    }
  }, 400)
}

watch(email, (val) => {
  if (loginMethod.value === 'email' || loginMethod.value === 'password') scheduleSsoDiscover(val)
})

watch(account, (val) => {
  if (loginMethod.value === 'password') scheduleSsoDiscover(val)
})

function finishLogin() {
  emit('success')
}

function switchView(view: 'register' | 'forgot') {
  setAuthView(view)
}

async function afterLogin(result: Awaited<ReturnType<typeof phoneLogin>>) {
  userStore.setAuth(result)
  ElMessage.success('登录成功')
  finishLogin()
}

onMounted(async () => {
  await Promise.all([loadAuth(), loadBrand()])
  try {
    publicSsoList.value = await listPublicEnterpriseSso()
  } catch {
    publicSsoList.value = []
  }
  configReady.value = true
  pickDefaultMethod()

  const saved = loadRememberedLogin()
  if (saved?.phone) {
    account.value = saved.phone
    phone.value = saved.phone
    rememberMe.value = true
  }
})

function startCountdown() {
  if (smsTimer) clearInterval(smsTimer)
  countdown.value = 60
  smsTimer = setInterval(() => {
    countdown.value--
    if (countdown.value <= 0 && smsTimer) {
      clearInterval(smsTimer)
      smsTimer = null
    }
  }, 1000)
}

function resetCodeState() {
  code.value = ''
  if (smsTimer) {
    clearInterval(smsTimer)
    smsTimer = null
  }
  countdown.value = 0
}

function setTab(tab: LoginMethod) {
  loginMethod.value = tab
}

watch(loginMethod, (tab) => {
  resetCodeState()
  if (tab === 'wechat' && auth.value.loginWechat) startQrcodeLogin()
  else stopPoll()
}, { immediate: true })

async function handleSendSms() {
  if (!isPhoneValid.value) {
    ElMessage.warning('请输入正确的手机号')
    return
  }
  if (countdown.value > 0) return
  try {
    const res = await sendSms(phone.value, 'login')
    ElMessage.success('验证码已发送')
    if (res.debug_code) code.value = res.debug_code
    startCountdown()
  } catch (e: unknown) {
    const msg = (e as { response?: { data?: { detail?: { message?: string } } } })?.response?.data?.detail?.message
    ElMessage.error(msg || '验证码发送失败')
  }
}

async function handleSendEmail() {
  if (!isEmailValid.value) {
    ElMessage.warning('请输入正确的邮箱')
    return
  }
  try {
    const res = await sendEmailCode(email.value.trim(), 'login')
    ElMessage.success('验证码已发送')
    if (res.debug_code) code.value = res.debug_code
    startCountdown()
  } catch (e: unknown) {
    ElMessage.error(parseApiError(e) || '验证码发送失败')
  }
}

async function handleEnterpriseSsoLogin(enterpriseId?: number) {
  const eid = enterpriseId ?? ssoEnterprise.value?.enterprise_id
  if (!eid) return
  loading.value = true
  try {
    const res = await getEnterpriseSsoAuthorizeUrl(eid)
    window.location.href = res.authorize_url
  } catch {
    ElMessage.error('无法发起企业 SSO 登录')
    loading.value = false
  }
}

function ssoProviderLabel(provider: string) {
  if (provider === 'wecom') return '企业微信'
  if (provider === 'dingtalk') return '钉钉'
  return 'SSO'
}

async function handleSmsLogin() {
  if (!isPhoneValid.value) {
    ElMessage.warning('请输入正确的手机号')
    return
  }
  if (!code.value) {
    ElMessage.warning('请输入验证码')
    return
  }
  const result = await phoneLogin({ phone: phone.value, login_type: 'sms', code: code.value })
  clearRememberedLogin()
  await afterLogin(result)
}

async function handleEmailSmsLogin() {
  if (!isEmailValid.value) {
    ElMessage.warning('请输入正确的邮箱')
    return
  }
  if (!code.value) {
    ElMessage.warning('请输入验证码')
    return
  }
  const result = await emailLogin({
    email: email.value.trim(),
    login_type: 'sms',
    code: code.value,
  })
  clearRememberedLogin()
  await afterLogin(result)
}

async function handlePasswordLogin() {
  const kind = detectAccountKind(account.value)
  if (!kind) {
    ElMessage.warning('请输入帐号、手机号或邮箱')
    return
  }
  if (!password.value) {
    ElMessage.warning('请输入密码')
    return
  }
  const result = kind === 'phone'
    ? await phoneLogin({
        phone: account.value.trim(),
        login_type: 'password',
        password: password.value,
      })
    : await emailLogin({
        email: account.value.trim(),
        login_type: 'password',
        password: password.value,
      })
  if (rememberMe.value) {
    saveRememberedLogin({ phone: account.value.trim() })
  } else {
    clearRememberedLogin()
  }
  await afterLogin(result)
}

async function submitLogin() {
  if (loading.value) return
  loading.value = true
  try {
    if (loginMethod.value === 'password') {
      await handlePasswordLogin()
    } else if (loginMethod.value === 'phone') {
      await handleSmsLogin()
    } else if (loginMethod.value === 'email') {
      await handleEmailSmsLogin()
    }
  } catch (e: unknown) {
    ElMessage.error(parseApiError(e))
  } finally {
    loading.value = false
  }
}

function stopPoll() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

async function startQrcodeLogin() {
  stopPoll()
  qrcodeStatus.value = 'pending'
  qrcodeImage.value = ''
  const res = await createQrcode()
  qrcodeTicket.value = res.ticket
  try {
    qrcodeImage.value = await qrCodeDataUrl(res.qrcode_url, 200)
  } catch {
    qrcodeImage.value = ''
  }

  pollTimer = setInterval(async () => {
    try {
      const status = await getQrcodeStatus(qrcodeTicket.value)
      qrcodeStatus.value = status.status
      if (status.status === 'confirmed' && status.access_token && status.user) {
        stopPoll()
        userStore.setAuth({
          access_token: status.access_token,
          refresh_token: status.refresh_token!,
          token_type: 'bearer',
          user: status.user,
        })
        ElMessage.success('扫码登录成功')
        finishLogin()
      } else if (status.status === 'expired') {
        stopPoll()
      }
    } catch {
      stopPoll()
    }
  }, 2000)
}

onUnmounted(() => {
  stopPoll()
  if (smsTimer) clearInterval(smsTimer)
  if (ssoDiscoverTimer) clearTimeout(ssoDiscoverTimer)
})
</script>

<template>
  <div class="login-panel">
    <div v-if="configReady && !hasAnyLogin" class="auth-disabled-tip">
      管理员暂未开放任何登录方式，请联系客服。
    </div>

    <template v-else-if="configReady">
      <el-alert
        v-if="loginNotice"
        type="warning"
        show-icon
        :closable="false"
        class="login-notice-alert"
        :title="loginNotice"
      />

      <div class="login-stage">
        <div
          class="login-stage__pane login-stage__pane--form"
          :class="{ 'is-active': loginMethod !== 'wechat' }"
        >
      <div v-if="loginTabs.length" class="uemo-switch">
        <button
          v-for="tab in loginTabs"
          :key="tab.name"
          type="button"
          class="uemo-switch__btn"
          :class="{ 'is-active': loginMethod === tab.name }"
          @click="setTab(tab.name)"
        >
          {{ tab.label }}
        </button>
      </div>

      <div class="auth-tab-stage">
      <el-form
        class="auth-tab-pane"
        :class="{ 'is-active': formTab === 'password' }"
        @submit.prevent="submitLogin"
      >
        <el-form-item>
          <el-input
            v-model="account"
            placeholder="帐号 / 手机号 / 邮箱"
          />
        </el-form-item>
        <el-form-item>
          <el-input
            v-model="password"
            type="password"
            placeholder="密码"
            show-password
          />
        </el-form-item>
        <div class="login-extra">
          <el-checkbox v-model="rememberMe">记住登录</el-checkbox>
          <button
            v-if="auth.loginPhone || auth.loginEmail"
            type="button"
            class="forgot-link"
            @click="switchView('forgot')"
          >
            忘记密码？
          </button>
        </div>
        <el-button
          type="primary"
          class="uemo-submit"
          native-type="submit"
          :disabled="!canPasswordLogin"
          :loading="loading"
        >
          登录
        </el-button>
        <div v-if="ssoEnterprise" class="sso-login-block">
          <el-divider>或</el-divider>
          <el-button class="uemo-submit" :loading="loading" @click="handleEnterpriseSsoLogin()">
            使用 {{ ssoEnterprise.name }} 企业 SSO 登录
          </el-button>
        </div>
      </el-form>

      <el-form
        v-if="auth.loginPhone"
        class="auth-tab-pane"
        :class="{ 'is-active': formTab === 'phone' }"
        @submit.prevent="submitLogin"
      >
        <el-form-item>
          <el-input v-model="phone" placeholder="手机号" maxlength="11" />
        </el-form-item>
        <el-form-item>
          <div class="auth-code-row">
            <el-input v-model="code" placeholder="验证码" maxlength="6" />
            <el-button
              class="uemo-code-btn"
              :disabled="countdown > 0 || !isPhoneValid"
              @click="handleSendSms"
            >
              {{ countdown > 0 ? `${countdown}s` : '发送验证码' }}
            </el-button>
          </div>
        </el-form-item>
        <el-button
          type="primary"
          class="uemo-submit"
          native-type="submit"
          :disabled="!canPhoneLogin"
          :loading="loading"
        >
          登录
        </el-button>
      </el-form>

      <el-form
        v-if="auth.loginEmail"
        class="auth-tab-pane"
        :class="{ 'is-active': formTab === 'email' }"
        @submit.prevent="submitLogin"
      >
        <el-form-item>
          <el-input v-model="email" placeholder="邮箱" type="email" />
        </el-form-item>
        <el-form-item>
          <div class="auth-code-row">
            <el-input v-model="code" placeholder="验证码" maxlength="6" />
            <el-button
              class="uemo-code-btn"
              :disabled="countdown > 0 || !isEmailValid"
              @click="handleSendEmail"
            >
              {{ countdown > 0 ? `${countdown}s` : '发送验证码' }}
            </el-button>
          </div>
        </el-form-item>
        <el-button
          type="primary"
          class="uemo-submit"
          native-type="submit"
          :disabled="!canEmailLogin"
          :loading="loading"
        >
          登录
        </el-button>
        <div v-if="ssoEnterprise" class="sso-login-block">
          <el-divider>或</el-divider>
          <el-button class="uemo-submit" :loading="loading" @click="handleEnterpriseSsoLogin()">
            使用 {{ ssoEnterprise.name }} 企业 SSO 登录
          </el-button>
        </div>
      </el-form>
      </div>

      <div v-if="publicSsoList.length" class="sso-login-block">
        <el-divider>企业登录</el-divider>
        <el-button
          v-for="ent in publicSsoList.filter((e) => e.provider !== 'oidc')"
          :key="ent.id"
          class="auth-submit sso-public-btn"
          :loading="loading"
          @click="handleEnterpriseSsoLogin(ent.id)"
        >
          {{ ent.name }} · {{ ssoProviderLabel(ent.provider) }} 登录
        </el-button>
      </div>

      <div v-if="hasAnyRegister" class="uemo-footer">
        还没有账号？
        <button type="button" @click="switchView('register')">点击注册</button>
      </div>
        </div>

        <div
          class="login-stage__pane login-stage__pane--wechat"
          :class="{ 'is-active': loginMethod === 'wechat' }"
        >
          <div class="qrcode-area">
            <div class="qrcode-box">
              <img v-if="qrcodeImage" :src="qrcodeImage" alt="微信扫码登录" class="qrcode-img" />
              <el-empty v-else description="正在生成二维码..." />
            </div>
            <p class="qrcode-hint">{{ wechatLoginHint }}</p>
            <p class="qrcode-status">
              {{
                qrcodeStatus === 'pending' ? '等待扫码'
                  : qrcodeStatus === 'scanned' ? '已扫码，请在手机上确认'
                    : qrcodeStatus === 'confirmed' ? '登录成功'
                      : qrcodeStatus === 'expired' ? '二维码已过期' : qrcodeStatus
              }}
            </p>
            <el-button v-if="qrcodeStatus === 'expired'" class="uemo-code-btn" @click="startQrcodeLogin">
              刷新二维码
            </el-button>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.login-panel {
  position: relative;
}

.login-stage {
  position: relative;
  height: 360px;
}

.login-stage__pane {
  position: absolute;
  inset: 0;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.36s ease, transform 0.36s ease;
}

.login-stage__pane--form {
  transform: translate3d(-18px, 0, 0);
}

.login-stage__pane--wechat {
  transform: translate3d(18px, 0, 0);
  display: flex;
  align-items: center;
  justify-content: center;
}

.login-stage__pane.is-active {
  opacity: 1;
  pointer-events: auto;
  transform: translate3d(0, 0, 0);
}

.login-panel :deep(.el-form-item) {
  margin-bottom: 8px;
}

.login-panel :deep(.el-input__wrapper) {
  min-height: 46px;
  padding: 6px 0;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
  border-bottom: 1px solid #e8e8e8;
}

.login-panel :deep(.el-input__wrapper:hover) {
  box-shadow: none;
  border-bottom-color: #d1d5db;
}

.login-panel :deep(.el-input__wrapper.is-focus) {
  box-shadow: none;
  border-bottom-color: #10b981;
}

.auth-disabled-tip {
  text-align: center;
  color: var(--ft-text-secondary);
  padding: 24px 0;
  font-size: 14px;
  font-weight: 400;
}

.sso-login-block {
  margin-top: 8px;
}

.sso-login-block .auth-submit {
  width: 100%;
}

.sso-public-btn {
  margin-bottom: 8px;
}

.login-notice-alert {
  margin-bottom: 20px;
  border-radius: 12px;
}

.login-extra {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin: 4px 0 8px;
}

.forgot-link {
  font-size: 13px;
  color: #10b981;
  text-decoration: none;
  background: none;
  border: none;
  padding: 0;
  cursor: pointer;
  font-weight: 400;
}

.forgot-link:hover {
  text-decoration: underline;
}

.qrcode-area {
  text-align: center;
  padding: 8px 0 16px;
  width: 100%;
}

.qrcode-box {
  min-height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.qrcode-img {
  width: 200px;
  height: 200px;
  display: block;
}

.qrcode-hint,
.qrcode-status {
  font-size: 13px;
  color: #9ca3af;
  font-weight: 400;
  margin: 8px 0 0;
}
</style>
