<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import {
  register,
  emailRegister,
  sendSms,
  sendEmailCode,
  checkPhoneRegistered,
  checkEmailRegistered,
} from '../../api/auth'
import { parseApiError } from '../../utils/error'
import { getLegalPages, EMPTY_LEGAL_PAGES, type LegalPages } from '../../api/cms'
import { useUserStore } from '../../store/user'
import { useAuthConfig } from '../../composables/useAuthConfig'
import { setAuthView, useLoginDialog } from '../../composables/useLoginDialog'
import { sanitizeHtml } from '../../utils/sanitizeHtml'
import FaIcon from '../FaIcon.vue'

const emit = defineEmits<{ success: [] }>()

const userStore = useUserStore()
const { auth, hasAnyRegister, load: loadAuth } = useAuthConfig()
const { inviteCode: globalInviteCode } = useLoginDialog()
const localInvite = ref('')

const registerTab = ref<'phone' | 'email'>('phone')
const configReady = ref(false)

const phone = ref('')
const email = ref('')
const password = ref('')
const confirmPassword = ref('')
const code = ref('')
const agreed = ref(false)
const countdown = ref(0)
const loading = ref(false)

const legal = ref<LegalPages>({ ...EMPTY_LEGAL_PAGES })
const legalVisible = ref(false)
const legalTitle = ref('')
const legalContent = ref('')

const isPhoneValid = computed(() => /^1[3-9]\d{9}$/.test(phone.value))
const isEmailValid = computed(() => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value.trim()))
const canPhoneRegister = computed(() =>
  isPhoneValid.value
  && !!code.value.trim()
  && password.value.length >= 6
  && password.value === confirmPassword.value
  && agreed.value,
)
const canEmailRegister = computed(() =>
  isEmailValid.value
  && !!code.value.trim()
  && password.value.length >= 6
  && password.value === confirmPassword.value
  && agreed.value,
)

const registerMethods = computed(() => {
  const list: { name: 'phone' | 'email'; label: string }[] = []
  if (auth.value.registerPhone) list.push({ name: 'phone', label: '手机号注册' })
  if (auth.value.registerEmail) list.push({ name: 'email', label: '邮箱注册' })
  return list
})

function pickDefaultTab() {
  const first = registerMethods.value[0]?.name
  if (first) registerTab.value = first
}

watch(registerMethods, () => pickDefaultTab(), { immediate: true })

let timer: ReturnType<typeof setInterval> | null = null
let redirectTimer: ReturnType<typeof setInterval> | null = null
const redirectNotice = ref('')

async function loadLegal() {
  try {
    legal.value = await getLegalPages()
  } catch {
    legal.value = { ...EMPTY_LEGAL_PAGES }
  }
}

function openLegal(type: 'agreement' | 'privacy') {
  if (type === 'agreement') {
    legalTitle.value = '用户协议'
    legalContent.value = legal.value.user_agreement
  } else {
    legalTitle.value = '隐私政策'
    legalContent.value = legal.value.privacy_policy
  }
  legalVisible.value = true
}

function clearRedirectTimer() {
  if (redirectTimer) {
    clearInterval(redirectTimer)
    redirectTimer = null
  }
  redirectNotice.value = ''
}

function goLogin(notice?: string) {
  clearRedirectTimer()
  setAuthView('login', { notice })
}

function goWechatAuth() {
  setAuthView('login', { loginMethod: 'wechat' })
}

function scheduleLoginRedirect(message: string) {
  clearRedirectTimer()
  let sec = 5
  redirectNotice.value = `${message}（${sec} 秒后返回登录）`
  redirectTimer = setInterval(() => {
    sec -= 1
    if (sec <= 0) {
      goLogin(message)
      return
    }
    redirectNotice.value = `${message}（${sec} 秒后返回登录）`
  }, 1000)
}

function startCountdown() {
  if (timer) clearInterval(timer)
  countdown.value = 60
  timer = setInterval(() => {
    countdown.value--
    if (countdown.value <= 0 && timer) {
      clearInterval(timer)
      timer = null
    }
  }, 1000)
}

function isAlreadyRegisteredMessage(msg: string) {
  return msg.includes('已注册')
}

async function handleSendSms() {
  if (!isPhoneValid.value) {
    ElMessage.warning('请输入正确的手机号')
    return
  }
  if (countdown.value > 0) return
  try {
    const check = await checkPhoneRegistered(phone.value)
    if (check.registered) {
      scheduleLoginRedirect('您已经是本站会员，即将返回登录')
      return
    }
    const res = await sendSms(phone.value, 'register')
    ElMessage.success('验证码已发送')
    if (res.debug_code) code.value = res.debug_code
    startCountdown()
  } catch (e: unknown) {
    const msg = parseApiError(e)
    if (isAlreadyRegisteredMessage(msg)) {
      scheduleLoginRedirect('您已经是本站会员，即将返回登录')
      return
    }
    ElMessage.error(msg || '验证码发送失败')
  }
}

async function handleSendEmail() {
  if (!isEmailValid.value) {
    ElMessage.warning('请输入正确的邮箱')
    return
  }
  if (countdown.value > 0) return
  try {
    const check = await checkEmailRegistered(email.value.trim())
    if (check.registered) {
      scheduleLoginRedirect('您已经是本站会员，即将返回登录')
      return
    }
    const res = await sendEmailCode(email.value.trim(), 'register')
    ElMessage.success('验证码已发送')
    if (res.debug_code) code.value = res.debug_code
    startCountdown()
  } catch (e: unknown) {
    const msg = parseApiError(e)
    if (isAlreadyRegisteredMessage(msg)) {
      scheduleLoginRedirect('您已经是本站会员，即将返回登录')
      return
    }
    ElMessage.error(msg || '验证码发送失败')
  }
}

function validatePasswords(): boolean {
  if (password.value.length < 6) {
    ElMessage.warning('密码至少 6 位')
    return false
  }
  if (password.value !== confirmPassword.value) {
    ElMessage.warning('两次密码不一致')
    return false
  }
  if (!code.value) {
    ElMessage.warning('请输入验证码')
    return false
  }
  if (!agreed.value) {
    ElMessage.warning('请先阅读并同意用户协议')
    return false
  }
  return true
}

async function handlePhoneRegister() {
  if (!isPhoneValid.value) {
    ElMessage.warning('请输入正确的手机号')
    return
  }
  if (!validatePasswords()) return

  loading.value = true
  try {
    const result = await register(
      {
        phone: phone.value,
        password: password.value,
        code: code.value,
        invite_code: auth.value.inviteEnabled
          ? (globalInviteCode.value || localInvite.value).trim() || undefined
          : undefined,
      },
      { skipGlobalErrorHandler: true },
    )
    userStore.setAuth(result)
    ElMessage.success('注册成功')
    emit('success')
  } catch (e: unknown) {
    const msg = parseApiError(e)
    if (isAlreadyRegisteredMessage(msg)) {
      scheduleLoginRedirect('您已经是本站会员，即将返回登录')
    } else {
      ElMessage.error(msg || '注册失败')
    }
  } finally {
    loading.value = false
  }
}

async function handleEmailRegisterSubmit() {
  if (!isEmailValid.value) {
    ElMessage.warning('请输入正确的邮箱')
    return
  }
  if (!validatePasswords()) return

  loading.value = true
  try {
    const result = await emailRegister({
      email: email.value.trim(),
      password: password.value,
      code: code.value,
      invite_code: auth.value.inviteEnabled
        ? (globalInviteCode.value || localInvite.value).trim() || undefined
        : undefined,
    })
    userStore.setAuth(result)
    ElMessage.success('注册成功')
    emit('success')
  } catch (e: unknown) {
    const msg = parseApiError(e)
    if (isAlreadyRegisteredMessage(msg)) {
      scheduleLoginRedirect('您已经是本站会员，即将返回登录')
    } else {
      ElMessage.error(msg || '注册失败')
    }
  } finally {
    loading.value = false
  }
}

function onRegisterTabChange() {
  code.value = ''
  if (timer) {
    clearInterval(timer)
    timer = null
  }
  countdown.value = 0
}

onMounted(async () => {
  await Promise.all([loadAuth(), loadLegal()])
  configReady.value = true
  pickDefaultTab()
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
  clearRedirectTimer()
})
</script>

<template>
  <div v-if="configReady && hasAnyRegister" class="register-panel">
    <div v-if="registerMethods.length > 1" class="uemo-switch">
      <button
        v-for="m in registerMethods"
        :key="m.name"
        type="button"
        class="uemo-switch__btn"
        :class="{ 'is-active': registerTab === m.name }"
        @click="registerTab = m.name; onRegisterTabChange()"
      >
        <FaIcon :name="m.name === 'phone' ? 'mobile-screen' : 'envelope'" size="13" />
        {{ m.name === 'phone' ? '手机注册' : '邮箱注册' }}
      </button>
    </div>

    <el-alert
      v-if="redirectNotice"
      type="warning"
      :closable="false"
      show-icon
      class="register-redirect-alert"
      :title="redirectNotice"
    />

    <div class="auth-tab-stage">
    <el-form
      v-if="auth.registerPhone"
      class="auth-tab-pane"
      :class="{ 'is-active': registerTab === 'phone' }"
      @submit.prevent="handlePhoneRegister"
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
      <el-form-item>
        <el-input v-model="password" type="password" placeholder="请输入密码" show-password />
      </el-form-item>
      <el-form-item>
        <el-input v-model="confirmPassword" type="password" placeholder="确认密码" show-password />
      </el-form-item>
      <el-form-item v-if="auth.inviteEnabled && globalInviteCode">
        <el-input :model-value="globalInviteCode" placeholder="邀请码" disabled />
      </el-form-item>
      <el-form-item v-else-if="auth.inviteEnabled">
        <el-input v-model="localInvite" placeholder="邀请码（选填）" maxlength="16" />
      </el-form-item>
      <el-checkbox v-model="agreed">
        我已阅读并同意
        <a href="#" class="link" @click.prevent="openLegal('agreement')">《用户协议》</a>
        和
        <a href="#" class="link" @click.prevent="openLegal('privacy')">《隐私政策》</a>
      </el-checkbox>
      <el-button
        type="primary"
        class="uemo-submit"
        :disabled="!canPhoneRegister"
        :loading="loading"
        @click="handlePhoneRegister"
      >
        立即注册
      </el-button>
    </el-form>

    <el-form
      v-if="auth.registerEmail"
      class="auth-tab-pane"
      :class="{ 'is-active': registerTab === 'email' }"
      @submit.prevent="handleEmailRegisterSubmit"
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
      <el-form-item>
        <el-input v-model="password" type="password" placeholder="请输入密码" show-password />
      </el-form-item>
      <el-form-item>
        <el-input v-model="confirmPassword" type="password" placeholder="确认密码" show-password />
      </el-form-item>
      <el-form-item v-if="auth.inviteEnabled && globalInviteCode">
        <el-input :model-value="globalInviteCode" placeholder="邀请码" disabled />
      </el-form-item>
      <el-form-item v-else-if="auth.inviteEnabled">
        <el-input v-model="localInvite" placeholder="邀请码（选填）" maxlength="16" />
      </el-form-item>
      <el-checkbox v-model="agreed">
        我已阅读并同意
        <a href="#" class="link" @click.prevent="openLegal('agreement')">《用户协议》</a>
        和
        <a href="#" class="link" @click.prevent="openLegal('privacy')">《隐私政策》</a>
      </el-checkbox>
      <el-button
        type="primary"
        class="uemo-submit"
        :disabled="!canEmailRegister"
        :loading="loading"
        @click="handleEmailRegisterSubmit"
      >
        立即注册
      </el-button>
    </el-form>
    </div>

    <div v-if="auth.loginWechat" class="uemo-toolbar register-wechat">
      <button type="button" class="uemo-wechat" @click="goWechatAuth">
        <FaIcon name="weixin" brand size="14" />
        微信授权登录注册
      </button>
    </div>

    <div class="uemo-footer">
      已有账号？
      <button type="button" @click="goLogin()">点击登录</button>
    </div>

    <el-dialog v-model="legalVisible" :title="legalTitle" width="720px" append-to-body align-center class="ft-legal-dialog">
      <div class="ft-legal-doc" v-html="sanitizeHtml(legalContent || '<p>暂无内容，请联系管理员在后台配置。</p>')" />
    </el-dialog>
  </div>

  <div v-else-if="configReady" class="auth-disabled-tip">
    当前未开放注册，请联系管理员。
    <button type="button" class="auth-footer-link" @click="goLogin()">返回登录</button>
  </div>
</template>

<style scoped>
.register-panel :deep(.el-form-item) {
  margin-bottom: 8px;
}

.register-panel :deep(.el-input__wrapper) {
  min-height: 46px;
  padding: 6px 0;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
  border-bottom: 1px solid #e8e8e8;
}

.register-panel :deep(.el-input__wrapper:hover) {
  box-shadow: none;
  border-bottom-color: #d1d5db;
}

.register-panel :deep(.el-input__wrapper.is-focus) {
  box-shadow: none;
  border-bottom-color: #10b981;
}

.link {
  color: var(--ft-primary);
  text-decoration: none;
}

.legal-content {
  max-height: 60vh;
  overflow-y: auto;
  line-height: 1.7;
  font-size: 14px;
}

.legal-content :deep(h3) {
  margin: 1.2em 0 0.5em;
  font-size: 15px;
}

.register-redirect-alert {
  margin-bottom: 16px;
  border-radius: 12px;
}

.auth-footer {
  text-align: center;
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid var(--ft-border);
  font-size: 14px;
  color: var(--ft-text-secondary);
}

.auth-footer-link {
  font-size: inherit;
  color: var(--ft-primary);
  background: none;
  border: none;
  padding: 0;
  cursor: pointer;
  font-weight: 400;
}

.auth-footer-link:hover {
  text-decoration: underline;
}

.auth-disabled-tip {
  text-align: center;
  padding: 24px 0;
  color: var(--ft-text-secondary);
  font-size: 14px;
}
</style>
