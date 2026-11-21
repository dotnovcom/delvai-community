<script setup lang="ts">
import { useLoginDialog } from '../../composables/useLoginDialog'
import AuthModalHeader from './AuthModalHeader.vue'
import LoginPanel from './LoginPanel.vue'
import RegisterPanel from './RegisterPanel.vue'
import ForgotPasswordPanel from './ForgotPasswordPanel.vue'

const emit = defineEmits<{ success: [] }>()

const { authView, redirectPath, notice } = useLoginDialog()
</script>

<template>
  <div class="auth-flow">
    <AuthModalHeader :view="authView" />
    <div class="auth-flow-body">
      <LoginPanel
        v-if="authView === 'login'"
        :redirect-path="redirectPath"
        :initial-notice="notice"
        @success="emit('success')"
      />
      <RegisterPanel v-else-if="authView === 'register'" @success="emit('success')" />
      <ForgotPasswordPanel v-else-if="authView === 'forgot'" />
    </div>
  </div>
</template>

<style scoped>
.auth-flow {
  padding-bottom: 8px;
  height: 100%;
  box-sizing: border-box;
}

.auth-flow-body {
  padding: 8px 36px 32px;
  position: relative;
}

.auth-flow :deep(.el-form-item) {
  margin-bottom: 10px;
}

.auth-flow :deep(.login-extra) {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin: 8px 0 4px;
}

.auth-flow :deep(.forgot-link) {
  font-size: 13px;
  color: #10b981;
  text-decoration: none;
  background: none;
  border: none;
  padding: 0;
  cursor: pointer;
  font-weight: 400;
}
</style>
