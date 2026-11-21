<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getMe, updateMe } from '../../api/auth'
import { getMyMembership } from '../../api/membership'
import { useUserStore } from '../../store/user'
import ProfileAvatarUpload from '../../components/profile/ProfileAvatarUpload.vue'
import type { UserInfo } from '../../types/user'
import FaIcon from '../../components/FaIcon.vue'

const userStore = useUserStore()
const router = useRouter()
const form = ref({ nickname: '', phone: '', email: '', avatar: '' })
const userMeta = ref<UserInfo | null>(null)
const membership = ref({
  plan_name: '免费版',
  level_name: 'free',
  level_label: '',
  expire_at: '' as string | undefined,
  is_active: true,
})
const loading = ref(false)
const saving = ref(false)

const PLATFORM_LABELS: Record<string, string> = {
  phone: '手机号',
  web: '网页',
  wechat: '微信',
  alipay: '支付宝',
  douyin: '抖音',
}

const STATUS_LABELS: Record<string, string> = {
  active: '正常',
  disabled: '已禁用',
}

const registerText = computed(() => {
  const t = userMeta.value?.created_at
  if (!t) return '—'
  return new Date(t).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
})

const platformText = computed(() => {
  const p = userMeta.value?.platform
  return p ? (PLATFORM_LABELS[p] || p) : '—'
})

const statusText = computed(() => {
  const s = userMeta.value?.status
  return s ? (STATUS_LABELS[s] || s) : '—'
})

function maskPhone(phone?: string | null) {
  if (!phone) return ''
  return phone.replace(/(\d{3})\d{4}(\d{4})/, '$1****$2')
}

function maskEmail(email?: string | null) {
  if (!email) return ''
  const [name, domain] = email.split('@')
  if (!domain) return email
  const head = name.length <= 2 ? `${name.slice(0, 1)}*` : `${name.slice(0, 2)}***`
  return `${head}@${domain}`
}

const phoneDisplay = computed(() => maskPhone(form.value.phone))
const emailDisplay = computed(() => maskEmail(form.value.email))

function openSecurity(target: 'phone' | 'email') {
  router.push({ path: '/profile/security', query: { action: target } })
}

onMounted(async () => {
  loading.value = true
  try {
    const [user, mem] = await Promise.all([getMe(), getMyMembership()])
    userMeta.value = user
    form.value.nickname = user.nickname || ''
    form.value.phone = user.phone || ''
    form.value.email = user.email || ''
    form.value.avatar = user.avatar || ''
    membership.value = {
      plan_name: mem.plan_name || '免费版',
      level_name: mem.level_name || 'free',
      level_label: mem.level_label || '',
      expire_at: mem.expire_at,
      is_active: mem.is_active,
    }
  } finally {
    loading.value = false
  }
})

async function handleSave() {
  if (!form.value.nickname.trim()) {
    ElMessage.warning('请填写昵称')
    return
  }
  saving.value = true
  try {
    await updateMe({
      nickname: form.value.nickname.trim(),
      avatar: form.value.avatar.trim() || undefined,
    })
    await userStore.fetchUserInfo()
    ElMessage.success('个人信息已保存')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div v-loading="loading" class="profile-page">
    <header class="member-strip">
      <div class="member-strip__main">
        <p class="member-strip__eyebrow">当前会员</p>
        <div class="member-strip__title">
          <h1>{{ membership.plan_name }}</h1>
          <span class="member-strip__chip">
            {{ membership.level_label || (membership.level_name === 'free' ? '免费版' : '已订阅') }}
          </span>
        </div>
        <p v-if="membership.expire_at" class="member-strip__sub">
          有效期至 {{ new Date(membership.expire_at).toLocaleDateString('zh-CN') }}
        </p>
        <p v-else class="member-strip__sub">
          升级会员可解锁无限对话、文书生成、合同审查等能力
        </p>
      </div>
      <router-link to="/profile/membership" class="member-strip__cta">升级会员</router-link>
    </header>

    <div class="profile-grid">
      <section class="pc-card profile-main">
        <div class="profile-main__head">
          <h2>基本资料</h2>
          <p>完善头像与昵称，便于法律咨询个性化服务</p>
        </div>

        <div class="profile-block">
          <h3>头像</h3>
          <ProfileAvatarUpload v-model="form.avatar" :nickname="form.nickname" />
        </div>

        <el-divider class="profile-divider" />

        <div class="profile-block">
          <h3>账号信息</h3>
          <el-form
            label-width="88px"
            label-position="left"
            class="profile-form"
            @submit.prevent="handleSave"
          >
            <el-form-item label="昵称" required>
              <el-input
                v-model="form.nickname"
                placeholder="请输入昵称（2–32 字）"
                maxlength="32"
                show-word-limit
              />
            </el-form-item>
            <el-form-item label="手机号">
              <div class="bind-field">
                <el-input :model-value="phoneDisplay" disabled placeholder="未绑定" />
                <el-button type="primary" @click="openSecurity('phone')">
                  {{ form.phone ? '更换' : '去绑定' }}
                </el-button>
              </div>
            </el-form-item>
            <el-form-item label="邮箱">
              <div class="bind-field">
                <el-input :model-value="emailDisplay" disabled placeholder="未绑定" />
                <el-button type="primary" @click="openSecurity('email')">
                  {{ form.email ? '更换' : '去绑定' }}
                </el-button>
              </div>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="saving" @click="handleSave">保存资料</el-button>
            </el-form-item>
          </el-form>
        </div>
      </section>

      <aside class="profile-side">
        <section class="pc-card">
          <h3>我的法律服务记录</h3>
          <p class="profile-records-hint">文书、合同与检索将自动保存，可导出 Word 或打印</p>
          <nav class="profile-records-quick">
            <router-link to="/profile/records?tab=documents"><FaIcon name="file-lines" /> 我的文书</router-link>
            <router-link to="/profile/records?tab=reviews"><FaIcon name="clipboard" /> 合同审查</router-link>
            <router-link to="/profile/records?tab=extracts"><FaIcon name="layer-group" /> 合同抽取</router-link>
            <router-link to="/profile/records?tab=search"><FaIcon name="magnifying-glass" /> 检索记录</router-link>
            <router-link to="/profile/records?tab=analysis"><FaIcon name="chart-column" /> 类案分析</router-link>
          </nav>
        </section>
        <section class="pc-card">
          <h3>账号概览</h3>
          <dl class="meta-list">
            <div class="meta-row">
              <dt>用户 ID</dt>
              <dd>{{ userMeta?.id ?? '—' }}</dd>
            </div>
            <div class="meta-row">
              <dt>账号状态</dt>
              <dd>
                <el-tag
                  v-if="userMeta?.status"
                  size="small"
                  :type="userMeta.status === 'active' ? 'success' : 'danger'"
                >
                  {{ statusText }}
                </el-tag>
                <span v-else>—</span>
              </dd>
            </div>
            <div class="meta-row">
              <dt>注册来源</dt>
              <dd>{{ platformText }}</dd>
            </div>
            <div class="meta-row">
              <dt>注册时间</dt>
              <dd>{{ registerText }}</dd>
            </div>
          </dl>
        </section>
        <section class="pc-card pc-card--tips">
          <h3>温馨提示</h3>
          <ul>
            <li>手机号、邮箱、微信可在「账号安全」中绑定</li>
            <li>头像支持本地上传或粘贴图片链接</li>
            <li>昵称将用于 AI 对话称呼与订单展示</li>
          </ul>
        </section>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.profile-page {
  --pc-green: linear-gradient(90deg, #34d399 0%, #10b981 52%, #059669 100%);
  --pc-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
  display: flex;
  flex-direction: column;
  gap: 16px;
  max-width: 1100px;
  margin: 0 auto;
}

.member-strip {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 24px 28px;
  border-radius: 24px;
  background: var(--pc-green);
  color: #fff;
  box-shadow: 0 12px 28px rgba(16, 185, 129, 0.22);
}

.member-strip__eyebrow {
  margin: 0 0 6px;
  font-size: 12px;
  letter-spacing: 0.12em;
  opacity: 0.82;
}

.member-strip__title {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.member-strip__title h1 {
  margin: 0;
  font-size: 22px;
  font-weight: 600;
  color: #fff;
}

.member-strip__chip {
  padding: 2px 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.18);
  border: 1px solid rgba(255, 255, 255, 0.28);
  font-size: 12px;
}

.member-strip__sub {
  margin: 8px 0 0;
  font-size: 13px;
  opacity: 0.92;
  line-height: 1.5;
}

.member-strip__cta {
  flex-shrink: 0;
  padding: 10px 22px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.32);
  color: #fff;
  font-size: 14px;
  font-weight: 400;
  text-decoration: none;
  white-space: nowrap;
}

.member-strip__cta:hover {
  background: rgba(255, 255, 255, 0.28);
}

.profile-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 280px;
  gap: 16px;
  align-items: start;
}

.pc-card {
  padding: 24px;
  background: #fff;
  border: 1px solid #e8e8e8;
  border-radius: 24px;
  box-shadow: var(--pc-shadow);
}

.profile-main__head {
  margin-bottom: 22px;
}

.profile-main__head h2 {
  margin: 0 0 6px;
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
}

.profile-main__head p {
  margin: 0;
  font-size: 13px;
  color: #6b7280;
}

.profile-block h3,
.pc-card h3 {
  margin: 0 0 14px;
  font-size: 14px;
  font-weight: 600;
  color: #1f2937;
}

.profile-divider {
  margin: 24px 0;
}

.profile-form {
  max-width: 480px;
}

.profile-form :deep(.el-form-item) {
  margin-bottom: 20px;
}

.profile-form :deep(.el-input) {
  width: 100%;
}

.bind-field {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
}

.bind-field :deep(.el-input) {
  flex: 1;
}

.profile-side {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.profile-records-hint {
  margin: -8px 0 12px;
  font-size: 12px;
  color: #6b7280;
  line-height: 1.5;
}

.profile-records-quick {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.profile-records-quick a {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  font-size: 13px;
  font-weight: 400;
  color: #1f2937;
  text-decoration: none;
  background: #f3f4f6;
  border: 1px solid #e8e8e8;
  border-radius: 12px;
}

.profile-records-quick a:hover {
  background: #ecfdf5;
  border-color: #6ee7b7;
  color: #059669;
}

.pc-card--tips ul {
  margin: 0;
  padding-left: 18px;
  font-size: 12px;
  color: #6b7280;
  line-height: 1.75;
}

.meta-list {
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.meta-row {
  display: grid;
  grid-template-columns: 68px 1fr;
  gap: 8px;
  align-items: center;
  font-size: 13px;
}

.meta-row dt {
  margin: 0;
  color: #6b7280;
}

.meta-row dd {
  margin: 0;
  color: #1f2937;
  word-break: break-all;
}

@media (max-width: 900px) {
  .profile-grid {
    grid-template-columns: 1fr;
  }

  .member-strip {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
