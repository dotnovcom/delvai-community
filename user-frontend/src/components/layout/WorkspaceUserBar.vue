<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../../store/user'
import { ensureLoggedIn, openLoginDialog } from '../../composables/useLoginDialog'
import { openAdminConsole } from '../../utils/adminOrigin'

const router = useRouter()
const userStore = useUserStore()

onMounted(() => {
  if (userStore.isLoggedIn) {
    userStore.fetchUserInfo().catch(() => null)
  }
})

function handleLogout() {
  userStore.logout()
  router.push('/chat/ai')
}

async function goProfile() {
  if (!await ensureLoggedIn('/profile')) return
  router.push('/profile')
}

async function goMembership() {
  if (!await ensureLoggedIn('/profile/membership')) return
  router.push('/profile/membership')
}
</script>

<template>
  <div class="ws-user-bar">
    <template v-if="userStore.isLoggedIn">
      <el-dropdown trigger="click" placement="top-start">
        <div class="ws-user-entry">
          <el-avatar :size="36" :src="userStore.avatar || undefined" class="ws-user-avatar">{{ userStore.nickname.slice(0, 1) }}</el-avatar>
          <div class="ws-user-meta">
            <span class="ws-user-name">{{ userStore.nickname }}</span>
            <span class="ws-user-role">{{ userStore.isAdmin ? '管理员' : '会员用户' }}</span>
          </div>
        </div>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item @click="goProfile">个人中心</el-dropdown-item>
            <el-dropdown-item @click="goMembership">升级会员</el-dropdown-item>
            <el-dropdown-item v-if="userStore.isAdmin" @click="openAdminConsole()">运营后台</el-dropdown-item>
            <el-dropdown-item divided @click="handleLogout">退出登录</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
      <button type="button" class="ws-vip-btn" @click="goMembership">升级</button>
    </template>
    <template v-else>
      <button type="button" class="ws-login-btn" @click="openLoginDialog()">登录</button>
      <button type="button" class="ws-vip-btn" @click="openLoginDialog({ redirect: '/profile/membership' })">升级</button>
    </template>
  </div>
</template>

<style scoped>
.ws-user-bar {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 10px 6px 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.ws-user-entry {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  width: 100%;
  padding: 4px;
  border-radius: 8px;
  transition: background 0.2s;
}

.ws-user-entry:hover {
  background: rgba(255, 255, 255, 0.06);
}

.ws-user-avatar {
  background: linear-gradient(135deg, var(--ft-primary), var(--ft-primary-light)) !important;
  color: #fff !important;
  font-weight: 600;
}

.ws-user-meta {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  width: 100%;
}

.ws-user-name {
  font-size: 10px;
  font-weight: 600;
  color: #fff;
  max-width: 56px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-align: center;
}

.ws-user-role {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.78);
}

.ws-vip-btn,
.ws-login-btn {
  width: 52px;
  height: 24px;
  border: none;
  border-radius: 12px;
  font-size: 10px;
  font-weight: 400;
  color: #fff;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
}

.ws-vip-btn {
  background: linear-gradient(90deg, #34d399 0%, #10b981 52%, #059669 100%);
}

.ws-login-btn {
  background: rgba(255, 255, 255, 0.12);
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.ws-vip-btn:hover,
.ws-login-btn:hover {
  transform: translateY(-1px);
}

.ws-vip-btn:hover {
  box-shadow: 0 4px 12px rgba(16, 185, 129, 0.35);
}
</style>
