<script setup lang="ts">
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { exchangeEnterpriseSsoCode } from '../api/auth'
import { useUserStore } from '../store/user'
import { safeRedirectPath } from '../utils/safeRedirect'
import { openLoginDialog } from '../composables/useLoginDialog'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

onMounted(async () => {
  const ssoCode = route.query.sso_code
  if (typeof ssoCode === 'string' && ssoCode) {
    try {
      const result = await exchangeEnterpriseSsoCode(ssoCode)
      userStore.setAuth(result)
      ElMessage.success('登录成功')
      router.replace(safeRedirectPath(route.query.redirect))
      return
    } catch {
      ElMessage.error('企业 SSO 登录失败，请重试')
    }
  }

  let notice = ''
  if (route.query.reason === 'other_device') {
    notice = '您已经在其它设备登录，如不是您本人登录，请至用户中心及时更改密码。'
  } else if (route.query.reason === 'session_expired') {
    notice = '登录已过期，请重新登录'
  }

  const view =
    route.path === '/register' ? 'register' : route.path === '/forgot-password' ? 'forgot' : 'login'

  openLoginDialog({
    view,
    redirect: typeof route.query.redirect === 'string' ? route.query.redirect : undefined,
    invite: typeof route.query.invite === 'string' ? route.query.invite : undefined,
    notice: notice || undefined,
  })
  router.replace('/chat/ai')
})
</script>

<template>
  <div class="auth-legacy-redirect" aria-hidden="true" />
</template>

<style scoped>
.auth-legacy-redirect {
  display: none;
}
</style>
