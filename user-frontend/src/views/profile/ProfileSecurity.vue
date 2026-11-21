<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  bindEmail,
  bindPhone,
  createBindWechatTicket,
  getBindWechatStatus,
  getMe,
  sendEmailCode,
  sendSms,
} from '../../api/auth'
import { useUserStore } from '../../store/user'
import { useBrandLabels } from '../../composables/useBrandLabels'
import ChangePasswordDialog from '../../components/profile/ChangePasswordDialog.vue'
import type { UserInfo } from '../../types/user'
import { useAuthConfig, userNeedsBinding } from '../../composables/useAuthConfig'
import FaIcon from '../../components/FaIcon.vue'
import { qrCodeDataUrl } from '../../utils/qrCodeDataUrl'
import { apiErrorMessage } from '../../utils/apiErrorMessage'

const route = useRoute()
const userStore = useUserStore()
const { load: loadBrand } = useBrandLabels()
const { auth, load: loadAuthConfig } = useAuthConfig()
const wechatLoginEnabled = computed(() => auth.value.loginWechat)

const wechatBindHint = '请使用微信扫码完成绑定'
const pwdDialog = ref<InstanceType<typeof ChangePasswordDialog> | null>(null)
const user = ref<UserInfo | null>(null)
const loading = ref(false)

const phoneDialog = ref(false)
const emailDialog = ref(false)
const wechatDialog = ref(false)

const bindPhoneVal = ref('')
const bindEmailVal = ref('')
const bindCode = ref('')
const bindLoading = ref(false)
const countdown = ref(0)
let smsTimer: ReturnType<typeof setInterval> | null = null

const wechatTicket = ref('')
const wechatUrl = ref('')
const wechatStatus = ref<'pending' | 'confirmed' | 'expired'>('pending')
let wechatPoll: ReturnType<typeof setInterval> | null = null

const isPhoneValid = computed(() => /^1[3-9]\d{9}$/.test(bindPhoneVal.value))
const isEmailValid = computed(() => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(bindEmailVal.value.trim()))

const phoneBound = computed(() => !!user.value?.phone)
const emailBound = computed(() => !!user.value?.email)
const wechatBound = computed(() => !!user.value?.openid)

const forcePhoneRequired = computed(
  () => !!user.value?.binding_required_phone || (route.query.bind === 'required' && !phoneBound.value),
)
const forceEmailRequired = computed(
  () => !!user.value?.binding_required_email || (route.query.bind === 'required' && !emailBound.value),
)
const forceBindMode = computed(() => userNeedsBinding(user.value) || route.query.bind === 'required')

function maskPhone(phone?: string | null) {
  if (!phone) return ''
  return phone.replace(/(\d{3})\d{4}(\d{4})/, '$1****$2')
}

function maskEmail(email?: string | null) {
  if (!email) return ''
  const [name, domain] = email.split('@')
  if (!domain) return email
  const head = name.length <= 2 ? name[0] : name.slice(0, 2)
  return `${head}***@${domain}`
}

async function loadUser() {
  loading.value = true
  try {
    user.value = await getMe()
    await userStore.fetchUserInfo()
    maybeOpenForcedBind()
    maybeOpenAction()
  } finally {
    loading.value = false
  }
}

function maybeOpenForcedBind() {
  if (!forceBindMode.value) return
  if (forcePhoneRequired.value && !phoneBound.value) {
    openPhoneDialog(true)
    return
  }
  if (forceEmailRequired.value && !emailBound.value) {
    openEmailDialog(true)
  }
}

function maybeOpenAction() {
  if (phoneDialog.value || emailDialog.value) return
  const action = String(route.query.action || '')
  if (action === 'phone') openPhoneDialogManual()
  else if (action === 'email') openEmailDialogManual()
}

function openPhoneDialog(forced = false) {
  bindPhoneVal.value = ''
  bindCode.value = ''
  phoneDialog.value = true
  if (forced) phoneDialogForced.value = true
}

function openEmailDialog(forced = false) {
  bindEmailVal.value = ''
  bindCode.value = ''
  emailDialog.value = true
  if (forced) emailDialogForced.value = true
}

const phoneDialogForced = ref(false)
const emailDialogForced = ref(false)

function startCountdown() {
  countdown.value = 60
  smsTimer = setInterval(() => {
    countdown.value--
    if (countdown.value <= 0 && smsTimer) clearInterval(smsTimer)
  }, 1000)
}

function openPhoneDialogManual() {
  phoneDialogForced.value = forcePhoneRequired.value
  openPhoneDialog(false)
}

function openEmailDialogManual() {
  emailDialogForced.value = forceEmailRequired.value
  openEmailDialog(false)
}

async function handleSendBindSms() {
  if (!isPhoneValid.value) {
    ElMessage.warning('请输入正确的手机号')
    return
  }
  try {
    const res = await sendSms(bindPhoneVal.value, 'bind_phone')
    ElMessage.success('验证码已发送')
    if (res.debug_code) bindCode.value = res.debug_code
    startCountdown()
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : '发送失败')
  }
}

async function handleSendBindEmail() {
  if (!isEmailValid.value) {
    ElMessage.warning('请输入正确的邮箱')
    return
  }
  try {
    const res = await sendEmailCode(bindEmailVal.value.trim(), 'bind_email')
    ElMessage.success('验证码已发送')
    if (res.debug_code) bindCode.value = res.debug_code
    startCountdown()
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : '发送失败')
  }
}

async function submitBindPhone() {
  if (!isPhoneValid.value || !bindCode.value) {
    ElMessage.warning('请填写手机号和验证码')
    return
  }
  bindLoading.value = true
  try {
    const replacing = phoneBound.value
    user.value = await bindPhone({ phone: bindPhoneVal.value, code: bindCode.value })
    await userStore.fetchUserInfo()
    phoneDialog.value = false
    phoneDialogForced.value = false
    ElMessage.success(replacing ? '手机号已更换' : '手机号绑定成功')
    if (forceEmailRequired.value && !user.value?.email) {
      openEmailDialog(true)
    }
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : '绑定失败')
  } finally {
    bindLoading.value = false
  }
}

async function submitBindEmail() {
  if (!isEmailValid.value || !bindCode.value) {
    ElMessage.warning('请填写邮箱和验证码')
    return
  }
  bindLoading.value = true
  try {
    const replacing = emailBound.value
    user.value = await bindEmail({ email: bindEmailVal.value.trim(), code: bindCode.value })
    await userStore.fetchUserInfo()
    emailDialog.value = false
    emailDialogForced.value = false
    ElMessage.success(replacing ? '邮箱已更换' : '邮箱绑定成功')
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : '绑定失败')
  } finally {
    bindLoading.value = false
  }
}

function stopWechatPoll() {
  if (wechatPoll) {
    clearInterval(wechatPoll)
    wechatPoll = null
  }
}

async function startWechatBind() {
  if (!wechatLoginEnabled.value) return
  stopWechatPoll()
  wechatStatus.value = 'pending'
  wechatUrl.value = ''
  try {
    const res = await createBindWechatTicket()
    wechatTicket.value = res.ticket
    try {
      wechatUrl.value = await qrCodeDataUrl(res.qrcode_url, 200)
    } catch {
      wechatUrl.value = res.qrcode_url
    }
    wechatDialog.value = true
    wechatPoll = setInterval(async () => {
      try {
        const st = await getBindWechatStatus(wechatTicket.value)
        wechatStatus.value = st.status
        if (st.status === 'confirmed') {
          stopWechatPoll()
          ElMessage.success('微信绑定成功')
          wechatDialog.value = false
          await loadUser()
          await userStore.fetchUserInfo()
        } else if (st.status === 'expired') {
          stopWechatPoll()
        }
      } catch {
        stopWechatPoll()
      }
    }, 2000)
  } catch (e: unknown) {
    ElMessage.error(apiErrorMessage(e, '无法创建绑定二维码'))
  }
}

onMounted(async () => {
  await Promise.all([loadBrand(), loadAuthConfig()])
  loadUser()
})
onUnmounted(() => {
  stopWechatPoll()
  if (smsTimer) clearInterval(smsTimer)
})
</script>

<template>
  <div v-loading="loading" class="profile-page">
    <ChangePasswordDialog ref="pwdDialog" />
    <div class="pc-card security-card">
      <div class="security-header">
        <h2>账号安全</h2>
        <p class="page-desc">管理登录密码与账号绑定，保障账户安全</p>
      </div>

      <el-alert
        v-if="forceBindMode"
        type="warning"
        :closable="false"
        show-icon
        title="请先完成账号绑定"
        description="管理员已开启强制绑定策略，绑定完成后即可正常使用平台功能。"
        class="binding-alert"
      />

      <div class="security-grid">
        <div class="security-item">
          <div class="security-icon"><FaIcon name="key" /></div>
          <div class="security-body">
            <div class="title">登录密码</div>
            <div class="desc">定期更换密码可提升账号安全性，建议使用字母、数字与符号组合</div>
          </div>
          <el-button @click="pwdDialog?.open()">修改密码</el-button>
        </div>

        <div class="security-item">
          <div class="security-icon"><FaIcon name="mobile-screen" /></div>
          <div class="security-body">
            <div class="title">手机号绑定</div>
            <div class="desc">
              {{ phoneBound ? `已绑定：${maskPhone(user?.phone)}` : '绑定手机号可用于登录和找回密码' }}
            </div>
          </div>
          <div class="security-actions">
            <el-tag v-if="phoneBound" type="success">已绑定</el-tag>
            <el-button type="primary" @click="openPhoneDialogManual">
              {{ phoneBound ? '更换' : '绑定手机号' }}
            </el-button>
          </div>
        </div>

        <div class="security-item">
          <div class="security-icon"><FaIcon name="envelope" /></div>
          <div class="security-body">
            <div class="title">邮箱绑定</div>
            <div class="desc">
              {{ emailBound ? `已绑定：${maskEmail(user?.email)}` : '绑定邮箱后可接收订单提醒等通知' }}
            </div>
          </div>
          <div class="security-actions">
            <el-tag v-if="emailBound" type="success">已绑定</el-tag>
            <el-button type="primary" @click="openEmailDialogManual">
              {{ emailBound ? '更换' : '绑定邮箱' }}
            </el-button>
          </div>
        </div>

        <div class="security-item">
          <div class="security-icon"><FaIcon name="weixin" brand /></div>
          <div class="security-body">
            <div class="title">微信绑定</div>
            <div class="desc">
              {{
                wechatBound
                  ? '已绑定微信，可使用微信扫码登录'
                  : wechatLoginEnabled
                    ? '绑定后可使用微信扫码登录'
                    : '当前未开启微信登录，暂不可绑定'
              }}
            </div>
          </div>
          <el-tag v-if="wechatBound" type="success">已绑定</el-tag>
          <el-button
            v-else
            plain
            class="wechat-bind-btn"
            :class="{ 'is-open': wechatLoginEnabled }"
            :disabled="!wechatLoginEnabled"
            @click="startWechatBind"
          >
            {{ wechatLoginEnabled ? '绑定微信' : '暂未开放' }}
          </el-button>
        </div>

        <div class="security-item security-item--info">
          <div class="security-icon"><FaIcon name="shield-halved" /></div>
          <div class="security-body">
            <div class="title">安全建议</div>
            <div class="desc">请勿在公共设备保存登录状态；发现异常登录请及时修改密码</div>
          </div>
        </div>
      </div>
    </div>

    <el-dialog
      v-model="phoneDialog"
      :title="phoneBound ? '更换手机号' : '绑定手机号'"
      width="460px"
      destroy-on-close
      :close-on-click-modal="!phoneDialogForced"
      :show-close="!phoneDialogForced"
    >
      <el-form class="bind-form" label-position="top" @submit.prevent="submitBindPhone">
        <el-form-item label="手机号">
          <el-input v-model="bindPhoneVal" maxlength="11" placeholder="请输入新手机号" />
        </el-form-item>
        <p v-if="phoneBound" class="bind-tip">
          当前已绑定 {{ maskPhone(user?.phone) }}。验证新手机号后将替换当前绑定，原号码不能再用于本账号登录。
        </p>
        <el-form-item label="验证码">
          <div class="bind-code-row">
            <el-input v-model="bindCode" maxlength="6" placeholder="请输入验证码" />
            <el-button :disabled="countdown > 0 || !isPhoneValid" @click="handleSendBindSms">
              {{ countdown > 0 ? `${countdown}s` : '获取验证码' }}
            </el-button>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button v-if="!phoneDialogForced" @click="phoneDialog = false">取消</el-button>
        <el-button type="primary" :loading="bindLoading" @click="submitBindPhone">
          {{ phoneBound ? '确认更换' : '确认绑定' }}
        </el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="emailDialog"
      :title="emailBound ? '更换邮箱' : '绑定邮箱'"
      width="460px"
      destroy-on-close
      :close-on-click-modal="!emailDialogForced"
      :show-close="!emailDialogForced"
    >
      <el-form class="bind-form" label-position="top" @submit.prevent="submitBindEmail">
        <el-form-item label="邮箱">
          <el-input v-model="bindEmailVal" type="email" placeholder="请输入新邮箱" />
        </el-form-item>
        <p v-if="emailBound" class="bind-tip">
          当前已绑定 {{ maskEmail(user?.email) }}。验证新邮箱后将替换当前绑定。
        </p>
        <el-form-item label="验证码">
          <div class="bind-code-row">
            <el-input v-model="bindCode" maxlength="6" placeholder="请输入验证码" />
            <el-button :disabled="countdown > 0 || !isEmailValid" @click="handleSendBindEmail">
              {{ countdown > 0 ? `${countdown}s` : '获取验证码' }}
            </el-button>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button v-if="!emailDialogForced" @click="emailDialog = false">取消</el-button>
        <el-button type="primary" :loading="bindLoading" @click="submitBindEmail">
          {{ emailBound ? '确认更换' : '确认绑定' }}
        </el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="wechatDialog" title="绑定微信" width="440px" @closed="stopWechatPoll">
      <div class="wechat-bind-box">
        <div v-if="wechatUrl" class="wechat-bind-qr">
          <img v-if="wechatUrl.startsWith('data:')" :src="wechatUrl" alt="微信扫码绑定" />
          <p v-else class="wechat-bind-url">{{ wechatUrl }}</p>
        </div>
        <p class="wechat-bind-hint">{{ wechatBindHint }}</p>
        <p class="wechat-bind-status">
          状态：{{
            wechatStatus === 'pending' ? '等待扫码'
              : wechatStatus === 'confirmed' ? '绑定成功'
                : '已过期'
          }}
        </p>
        <el-button v-if="wechatStatus === 'expired'" @click="startWechatBind">刷新二维码</el-button>
      </div>
    </el-dialog>
  </div>
</template>

<style scoped>
.pc-card {
  min-height: 360px;
  padding: 24px;
  background: #fff;
  border: 1px solid #e8e8e8;
  border-radius: 24px;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
}

.security-header {
  margin-bottom: 20px;
}

.binding-alert {
  margin-bottom: 16px;
}

h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
}

.page-desc {
  margin: 4px 0 0;
  font-size: 13px;
  color: #6b7280;
}

.security-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.security-item {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  padding: 20px;
  border: 1px solid #e8e8e8;
  border-radius: 20px;
  background: #fff;
}

.security-item:hover {
  border-color: #6ee7b7;
  box-shadow: 0 8px 24px rgba(16, 185, 129, 0.08);
}

.security-item--info {
  grid-column: 1 / -1;
  background: linear-gradient(180deg, #ecfdf5 0%, #fff 70%);
}

.security-icon {
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  background: linear-gradient(90deg, #34d399 0%, #10b981 52%, #059669 100%);
  color: #fff;
  border-radius: 12px;
}

.security-body {
  flex: 1;
  min-width: 0;
}

.security-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
  align-self: center;
}

.title {
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 6px;
}

.desc {
  font-size: 13px;
  color: #6b7280;
  line-height: 1.6;
}

.bind-form :deep(.el-form-item) {
  margin-bottom: 16px;
}

.bind-form :deep(.el-form-item__label) {
  margin-bottom: 6px;
  line-height: 1.4;
  color: #374151;
}

.bind-tip {
  display: block;
  margin: -4px 0 16px;
  padding: 10px 12px;
  border-radius: 8px;
  background: #f3f4f6;
  color: #6b7280;
  font-size: 12px;
  line-height: 1.6;
}

.bind-code-row {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
}

.bind-code-row :deep(.el-input) {
  flex: 1;
  min-width: 0;
}

.bind-code-row .el-button {
  flex-shrink: 0;
}

.wechat-bind-box {
  text-align: center;
  padding: 8px 0 4px;
}

.wechat-bind-qr img {
  width: 200px;
  height: 200px;
  display: block;
  margin: 0 auto;
}

.wechat-bind-url {
  word-break: break-all;
  font-size: 13px;
  color: #10b981;
  background: #ecfdf5;
  padding: 12px;
  border-radius: 12px;
  border: 1px dashed #6ee7b7;
}

.wechat-bind-btn.is-open {
  color: var(--el-color-primary);
  border-color: var(--el-color-primary-light-5);
}

.wechat-bind-hint,
.wechat-bind-status {
  font-size: 13px;
  color: #6b7280;
  margin: 12px 0 0;
}

@media (max-width: 768px) {
  .security-grid {
    grid-template-columns: 1fr;
  }

  .security-item--info {
    grid-column: auto;
  }
}
</style>
