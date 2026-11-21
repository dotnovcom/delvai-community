<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '../../store/user'
import { useBrandLabels } from '../../composables/useBrandLabels'
import { useNotificationUnread } from '../../composables/useNotificationUnread'
import FaIcon from '../FaIcon.vue'

const props = defineProps<{ active?: string }>()

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const { platformName, config, load } = useBrandLabels()
const { unreadCount } = useNotificationUnread()

onMounted(() => {
  load()
  if (userStore.isLoggedIn) userStore.fetchUserInfo().catch(() => null)
})

const menus: {
  key: string
  label: string
  icon: string
  tone: string
  path: string
  badge?: boolean
  highlight?: boolean
}[] = [
  { key: 'profile', label: '个人信息', icon: 'circle-user', tone: 'blue', path: '/profile' },
  
  { key: 'notifications', label: '站内信', icon: 'envelope', tone: 'teal', path: '/profile/notifications', badge: true },
  { key: 'records', label: '我的记录', icon: 'folder-open', tone: 'indigo', path: '/profile/records' },
  { key: 'usage', label: '用量统计', icon: 'chart-column', tone: 'rose', path: '/profile/usage' },
  { key: 'security', label: '账号安全', icon: 'lock', tone: 'slate', path: '/profile/security' },
  { key: 'chat', label: '法律咨询', icon: 'comments', tone: 'blue', path: '/chat/ai' },
]

const current = computed(() => props.active || 'profile')

function navigate(item: typeof menus[0]) {
  if (route.path !== item.path) router.push(item.path)
}

function handleLogout() {
  userStore.logout()
  router.push('/chat/ai')
}
</script>

<template>
  <aside class="profile-sidebar">
    <div class="profile-sidebar-brand" @click="router.push('/chat/ai')">
      <img v-if="config.logo_url" :src="config.logo_url" alt="" class="brand-logo-img" />
      <FaIcon v-else class="brand-icon" name="scale-balanced" />
      <span class="brand-text">{{ platformName }}</span>
    </div>

    <div class="profile-user-card">
      <el-avatar :size="44" :src="userStore.avatar || undefined">{{ userStore.nickname.slice(0, 1) }}</el-avatar>
      <div class="profile-user-meta">
        <span class="profile-user-name">{{ userStore.nickname }}</span>
        <span class="profile-user-sub">个人中心</span>
      </div>
    </div>

    <nav class="profile-nav">
      <button
        v-for="item in menus"
        :key="item.key"
        type="button"
        class="profile-nav-item"
        :class="{ active: current === item.key, highlight: item.highlight }"
        @click="navigate(item)"
      >
        <FaIcon class="nav-icon" :name="item.icon" />
        <span class="nav-label">{{ item.label }}</span>
        <span v-if="item.badge && unreadCount > 0" class="nav-badge">{{ unreadCount > 99 ? '99+' : unreadCount }}</span>
      </button>
    </nav>

    <div class="profile-sidebar-footer">
      <button type="button" class="footer-link" @click="router.push('/chat/ai')">
        <FaIcon name="comments" size="12" /> 返回工作台
      </button>
      <button type="button" class="footer-logout" @click="handleLogout">
        <FaIcon name="right-to-bracket" size="12" /> 退出登录
      </button>
    </div>
  </aside>
</template>

<style scoped>
.profile-sidebar {
  width: 200px;
  flex-shrink: 0;
  background: var(--ft-portal-dark);
  display: flex;
  flex-direction: column;
  height: 100%;
  border-right: 1px solid rgba(255, 255, 255, 0.06);
}

.profile-sidebar-brand {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 16px 16px 12px;
  cursor: pointer;
  color: #fff;
}

.brand-icon { font-size: 20px; flex-shrink: 0; }
.brand-logo-img {
  height: 28px;
  width: auto;
  max-width: 120px;
  object-fit: contain;
  flex-shrink: 0;
}
.brand-text {
  font-size: 15px;
  font-weight: 700;
  letter-spacing: 0.5px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.profile-user-card {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 0 12px 12px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.06);
  border-radius: var(--ft-radius);
}

.profile-user-meta {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.profile-user-name {
  font-size: 13px;
  font-weight: 600;
  color: #fff;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.profile-user-sub {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.5);
}

.profile-nav {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
  display: flex;
  flex-direction: column;
  gap: 0;
}

.profile-nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  margin: 0;
  border: none;
  border-radius: 0;
  box-shadow: none;
  background: transparent;
  padding: 12px 16px;
  cursor: pointer;
  color: rgba(255, 255, 255, 0.65);
  font-size: 13px;
  font-weight: 400;
  text-align: left;
  transition: background 0.22s ease, color 0.22s ease;
}

.profile-nav-item:hover {
  background: rgba(255, 255, 255, 0.08);
  color: #fff;
}

.profile-nav-item.active {
  background: rgba(16, 185, 129, 0.22);
  color: #fff;
  border: none;
  border-radius: 0;
  box-shadow: none;
}

.profile-nav-item.highlight {
  color: #fff;
}

.profile-nav-item.highlight.active,
.profile-nav-item.highlight:hover {
  color: #fff;
  background: rgba(16, 185, 129, 0.28);
}

.nav-icon {
  font-size: 14px;
  color: #fff;
}

.nav-label {
  flex: 1;
}

.nav-badge {
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  border-radius: 999px;
  background: #ef4444;
  color: #fff;
  font-size: 11px;
  line-height: 18px;
  text-align: center;
  flex-shrink: 0;
}

.profile-sidebar-footer {
  padding: 12px 10px 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.footer-link,
.footer-logout {
  border: none;
  background: transparent;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 12px;
  cursor: pointer;
  text-align: left;
}

.footer-link {
  color: rgba(255, 255, 255, 0.55);
}

.footer-link:hover {
  color: #fff;
  background: rgba(255, 255, 255, 0.06);
}

.footer-logout {
  color: #fca5a5;
}

.footer-logout:hover {
  background: rgba(239, 68, 68, 0.12);
}
</style>
