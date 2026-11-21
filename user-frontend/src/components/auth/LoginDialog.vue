<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { closeLoginDialog, useLoginDialog, type LoginMethod } from '../../composables/useLoginDialog'
import { useAuthConfig } from '../../composables/useAuthConfig'
import AuthFlowBody from './AuthFlowBody.vue'
import FaIcon from '../FaIcon.vue'
import qrcodeCorner from '../../assets/auth/qrcode.png'
import pcCorner from '../../assets/auth/pc.png'

const router = useRouter()
const { visible, redirectPath, authView, loginMethod } = useLoginDialog()
const { auth, load } = useAuthConfig()

onMounted(() => {
  load()
})

const showQrCorner = computed(() => authView.value === 'login' && auth.value.loginWechat)
const isWechat = computed(() => loginMethod.value === 'wechat')
const lastFormMethod = ref<LoginMethod>('password')

function toggleWechatLogin() {
  if (loginMethod.value === 'wechat') {
    loginMethod.value = lastFormMethod.value
    return
  }
  lastFormMethod.value = loginMethod.value
  loginMethod.value = 'wechat'
}

function onSuccess() {
  const target = redirectPath.value
  closeLoginDialog(true)
  if (target) router.push(target)
}

function onClosed() {
  if (visible.value) closeLoginDialog(false)
}

function handleClose() {
  closeLoginDialog(false)
}
</script>

<template>
  <el-dialog
    v-model="visible"
    width="520px"
    append-to-body
    destroy-on-close
    :close-on-click-modal="true"
    :show-close="false"
    class="login-dialog"
    :class="{
      'has-qr-corner': showQrCorner,
      'is-login-mode': authView === 'login',
      'is-wechat-mode': isWechat,
    }"
    modal-class="login-dialog-overlay"
    @closed="onClosed"
  >
    <template #header>
      <span class="login-dialog-sr-title">登录</span>
      <button
        v-if="showQrCorner"
        type="button"
        class="login-qr-corner"
        :title="isWechat ? '返回帐密登录' : '微信扫码登录'"
        @click="toggleWechatLogin"
      >
        <img
          :key="isWechat ? 'pc' : 'qr'"
          :src="isWechat ? pcCorner : qrcodeCorner"
          :alt="isWechat ? '返回帐密登录' : '微信扫码登录'"
          class="login-qr-corner__img"
        />
      </button>
      <button
        type="button"
        class="login-dialog-close"
        aria-label="关闭"
        @click="handleClose"
      >
        <FaIcon name="xmark" size="16" />
      </button>
    </template>
    <AuthFlowBody @success="onSuccess" />
  </el-dialog>
</template>

<style scoped>
.login-dialog-sr-title {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
</style>

<style>
.login-dialog-overlay {
  backdrop-filter: blur(6px);
  background-color: rgba(15, 23, 42, 0.45) !important;
}

.login-dialog-overlay .el-overlay-dialog {
  display: flex;
  align-items: center;
  justify-content: center;
}

.el-dialog.login-dialog {
  margin-top: 0 !important;
}
</style>
