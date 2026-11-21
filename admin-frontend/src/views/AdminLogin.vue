<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Lock, User } from '@element-plus/icons-vue'
import { adminLogin } from '../api/auth'
import { useUserStore } from '../store/user'
import { usePublicConfig } from '../composables/usePublicConfig'
import { parseApiError } from '../utils/error'
import { safeRedirectPath } from '../utils/safeRedirect'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const { config, load } = usePublicConfig()
const logoUrl = computed(() => (config.value.logo_url || '').trim())
const platformName = computed(() => (config.value.platform_name || '').trim())

onMounted(() => {
  load().catch(() => undefined)
})

const account = ref('')
const password = ref('')
const loading = ref(false)

const notice = computed(() => {
  if (route.query.reason === 'other_device') return '您已经在其它设备登录，请重新登录。'
  if (route.query.reason === 'password_changed') return '密码已更新，请使用新密码登录。'
  if (route.query.reason === 'session_expired') return '登录已过期，请重新登录。'
  if (route.query.reason === 'not_admin') return '该账号没有运营后台权限。'
  return ''
})

async function submit() {
  const phone = account.value.trim()
  if (!phone || !password.value) {
    ElMessage.warning('请输入账号和密码')
    return
  }
  loading.value = true
  try {
    const result = await adminLogin({
      phone,
      login_type: 'password',
      password: password.value,
    })
    userStore.setAuth(result)
    if (!result.user?.is_admin) {
      userStore.logout()
      ElMessage.error('该账号没有运营后台权限')
      return
    }
    const dest = safeRedirectPath(route.query.redirect, '/admin')
    router.replace(dest === '/' || dest.startsWith('/admin') ? dest === '/' ? '/admin' : dest : '/admin')
  } catch (err) {
    ElMessage.error(parseApiError(err))
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="admin-login">
    <div class="admin-login__card">
      <div class="admin-login__mark">
        <img v-if="logoUrl" :src="logoUrl" :alt="platformName || 'LOGO'" class="admin-login__logo" />
        <svg v-else viewBox="0 0 24 24" width="26" height="26" fill="none" aria-hidden="true">
          <rect x="3" y="5" width="18" height="14" rx="2" stroke="#fff" stroke-width="1.8" />
          <path d="M4 7l8 6 8-6" stroke="#fff" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
        </svg>
      </div>
      <h1>欢迎回来</h1>
      <p class="admin-login__sub">登录您的账户以继续</p>
      <p v-if="notice" class="admin-login__notice">{{ notice }}</p>
      <el-form class="admin-login__form" @submit.prevent="submit">
        <el-form-item>
          <el-input v-model="account" placeholder="请输入账号" size="large" autocomplete="username">
            <template #prefix>
              <el-icon><User /></el-icon>
            </template>
          </el-input>
        </el-form-item>
        <el-form-item>
          <el-input
            v-model="password"
            type="password"
            placeholder="请输入密码"
            size="large"
            show-password
            autocomplete="current-password"
            @keyup.enter="submit"
          >
            <template #prefix>
              <el-icon><Lock /></el-icon>
            </template>
          </el-input>
        </el-form-item>
        <el-button class="admin-login__submit" :loading="loading" @click="submit">登录</el-button>
      </el-form>
    </div>
  </div>
</template>

<style scoped>
.admin-login {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background:
    linear-gradient(160deg, rgba(255, 255, 255, 0.16), transparent 42%),
    linear-gradient(180deg, #3b93f7 0%, #1d74f2 48%, #1567ea 100%);
  position: relative;
  overflow: hidden;
}
.admin-login::before,
.admin-login::after {
  content: '';
  position: absolute;
  background: rgba(255, 255, 255, 0.08);
  transform: rotate(32deg);
}
.admin-login::before {
  width: 420px;
  height: 720px;
  left: -180px;
  top: -80px;
}
.admin-login::after {
  width: 280px;
  height: 520px;
  right: -80px;
  bottom: -120px;
}
.admin-login__card {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 400px;
  background: #fff;
  border-radius: 8px;
  padding: 36px 32px 32px;
  box-shadow: 0 18px 50px rgba(15, 60, 140, 0.18);
  text-align: center;
}
.admin-login__mark {
  width: 56px;
  height: 56px;
  margin: 0 auto 16px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  background: linear-gradient(180deg, #4da3ff 0%, #1d74f2 100%);
  box-shadow: 0 8px 16px rgba(29, 116, 242, 0.28);
}
.admin-login__logo {
  width: 100%;
  height: 100%;
  object-fit: cover;
  background: #fff;
}
.admin-login__card h1 {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
  color: #1f2937;
}
.admin-login__sub {
  margin: 8px 0 22px;
  font-size: 13px;
  color: #9ca3af;
}
.admin-login__notice {
  margin: -8px 0 16px;
  padding: 8px 10px;
  border-radius: 6px;
  background: #fef2f2;
  color: #b91c1c;
  font-size: 13px;
  text-align: left;
}
.admin-login__form :deep(.el-form-item) {
  margin-bottom: 16px;
}
.admin-login__form :deep(.el-input__wrapper) {
  border-radius: 6px;
  box-shadow: 0 0 0 1px #e5e7eb inset;
  background: #fff;
}
.admin-login__form :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px #3b82f6 inset;
}
.admin-login__submit {
  width: 100%;
  height: 42px;
  margin-top: 4px;
  border: none;
  border-radius: 6px;
  color: #fff;
  font-size: 15px;
  font-weight: 600;
  background: linear-gradient(90deg, #3b93f7 0%, #1d74f2 100%);
}
.admin-login__submit:hover,
.admin-login__submit:focus {
  color: #fff;
  background: linear-gradient(90deg, #59a4f8 0%, #2b82f4 100%);
}
</style>
