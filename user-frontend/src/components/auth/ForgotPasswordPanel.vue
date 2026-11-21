<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { sendSms, sendEmailCode, resetPassword, resetPasswordByEmail } from '../../api/auth'
import { useAuthConfig } from '../../composables/useAuthConfig'
import { setAuthView } from '../../composables/useLoginDialog'
import FaIcon from '../FaIcon.vue'

const { auth, load: loadAuth } = useAuthConfig()
const configReady = ref(false)
const methodTab = ref<'phone' | 'email'>('phone')

const phone = ref('')
const email = ref('')
const code = ref('')
const password = ref('')
const confirmPassword = ref('')
const countdown = ref(0)
const loading = ref(false)

const isPhoneValid = computed(() => /^1[3-9]\d{9}$/.test(phone.value))
const isEmailValid = computed(() => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value.trim()))
const canResetPhone = computed(() =>
  isPhoneValid.value
  && !!code.value.trim()
  && password.value.length >= 6
  && password.value === confirmPassword.value,
)
const canResetEmail = computed(() =>
  isEmailValid.value
  && !!code.value.trim()
  && password.value.length >= 6
  && password.value === confirmPassword.value,
)

const methods = computed(() => {
  const list: { name: 'phone' | 'email'; label: string }[] = []
  if (auth.value.loginPhone) list.push({ name: 'phone', label: '手机号找回' })
  if (auth.value.loginEmail) list.push({ name: 'email', label: '邮箱找回' })
  return list
})

let timer: ReturnType<typeof setInterval> | null = null

function clearTimer() {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
}

onMounted(async () => {
  await loadAuth()
  configReady.value = true
  const first = methods.value[0]?.name
  if (first) methodTab.value = first
})

onUnmounted(clearTimer)

function goLogin(notice?: string) {
  setAuthView('login', { notice })
}

function startCountdown() {
  clearTimer()
  countdown.value = 60
  timer = setInterval(() => {
    countdown.value--
    if (countdown.value <= 0) clearTimer()
  }, 1000)
}

async function handleSendSms() {
  if (!isPhoneValid.value) {
    ElMessage.warning('请输入正确的手机号')
    return
  }
  const res = await sendSms(phone.value, 'reset_password')
  ElMessage.success('验证码已发送')
  if (res.debug_code) code.value = res.debug_code
  startCountdown()
}

async function handleSendEmail() {
  if (!isEmailValid.value) {
    ElMessage.warning('请输入正确的邮箱')
    return
  }
  const res = await sendEmailCode(email.value.trim(), 'reset_password')
  ElMessage.success('验证码已发送')
  if (res.debug_code) code.value = res.debug_code
  startCountdown()
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
  return true
}

async function handleResetPhone() {
  if (!isPhoneValid.value) {
    ElMessage.warning('请输入正确的手机号')
    return
  }
  if (!validatePasswords()) return

  loading.value = true
  try {
    await resetPassword({ phone: phone.value, code: code.value, new_password: password.value })
    ElMessage.success('密码已重置，请登录')
    goLogin('密码已重置，请使用新密码登录')
  } finally {
    loading.value = false
  }
}

async function handleResetEmail() {
  if (!isEmailValid.value) {
    ElMessage.warning('请输入正确的邮箱')
    return
  }
  if (!validatePasswords()) return

  loading.value = true
  try {
    await resetPasswordByEmail({
      email: email.value.trim(),
      code: code.value,
      new_password: password.value,
    })
    ElMessage.success('密码已重置，请登录')
    goLogin('密码已重置，请使用新密码登录')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div v-if="configReady" class="forgot-panel">
    <div v-if="methods.length > 1" class="uemo-switch">
      <button
        v-for="m in methods"
        :key="m.name"
        type="button"
        class="uemo-switch__btn"
        :class="{ 'is-active': methodTab === m.name }"
        @click="methodTab = m.name"
      >
        <FaIcon :name="m.name === 'phone' ? 'mobile-screen' : 'envelope'" size="13" />
        {{ m.name === 'phone' ? '手机找回' : '邮箱找回' }}
      </button>
    </div>

    <div class="auth-tab-stage">
    <el-form
      v-if="auth.loginPhone"
      class="auth-tab-pane"
      :class="{ 'is-active': methodTab === 'phone' }"
      @submit.prevent="handleResetPhone"
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
        <el-input v-model="password" type="password" placeholder="新密码（至少6位）" show-password />
      </el-form-item>
      <el-form-item>
        <el-input v-model="confirmPassword" type="password" placeholder="确认新密码" show-password />
      </el-form-item>
      <el-button
        type="primary"
        class="uemo-submit"
        :disabled="!canResetPhone"
        :loading="loading"
        @click="handleResetPhone"
      >
        重置密码
      </el-button>
    </el-form>

    <el-form
      v-if="auth.loginEmail"
      class="auth-tab-pane"
      :class="{ 'is-active': methodTab === 'email' }"
      @submit.prevent="handleResetEmail"
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
        <el-input v-model="password" type="password" placeholder="新密码（至少6位）" show-password />
      </el-form-item>
      <el-form-item>
        <el-input v-model="confirmPassword" type="password" placeholder="确认新密码" show-password />
      </el-form-item>
      <el-button
        type="primary"
        class="uemo-submit"
        :disabled="!canResetEmail"
        :loading="loading"
        @click="handleResetEmail"
      >
        重置密码
      </el-button>
    </el-form>
    </div>

    <div class="uemo-footer">
      <button type="button" @click="goLogin()">返回登录</button>
    </div>
  </div>
</template>

<style scoped>
.forgot-panel :deep(.el-form-item) {
  margin-bottom: 8px;
}

.forgot-panel :deep(.el-input__wrapper) {
  min-height: 46px;
  padding: 6px 0;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
  border-bottom: 1px solid #e8e8e8;
}

.forgot-panel :deep(.el-input__wrapper:hover) {
  box-shadow: none;
  border-bottom-color: #d1d5db;
}

.forgot-panel :deep(.el-input__wrapper.is-focus) {
  box-shadow: none;
  border-bottom-color: #10b981;
}

.reset-tabs {
  margin-bottom: 18px;
}

.reset-tabs :deep(.el-radio-group) {
  width: 100%;
  display: flex;
}

.reset-tabs :deep(.el-radio-button) {
  flex: 1;
}

.reset-tabs :deep(.el-radio-button__inner) {
  width: 100%;
}

.auth-footer {
  text-align: center;
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid var(--ft-border);
}

.auth-footer-link {
  font-size: 14px;
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
</style>
