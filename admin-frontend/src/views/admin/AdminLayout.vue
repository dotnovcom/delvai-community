<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Expand, Fold, Link, Lock, Setting, SwitchButton } from '@element-plus/icons-vue'
import { resolveAdminIcon, type AdminIconName } from '../../components/admin/adminIcons'
import { useBrandLabels } from '../../composables/useBrandLabels'
import { useAdminSessionIdle } from '../../composables/useAdminSessionIdle'
import { openUserSite } from '../../utils/userOrigin'
import { useUserStore } from '../../store/user'

interface MenuLeaf {
  path: string
  title: string
  icon: AdminIconName
}

interface MenuNode {
  title: string
  icon: AdminIconName
  path?: string
  index: string
  children?: MenuLeaf[]
}

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const collapsed = ref(false)
const { platformName, brandInitial, load } = useBrandLabels()

onMounted(() => load())
useAdminSessionIdle()

const menuGroups: { title: string; items: MenuNode[] }[] = [
  {
    title: '概览',
    items: [{ index: '/admin', title: '数据概览', icon: 'dashboard', path: '/admin' }],
  },
  {
    title: '运营',
    items: [
      { index: '/admin/hub/users', title: '用户中心', icon: 'users', path: '/admin/hub/users/list' },
      { index: '/admin/hub/content', title: '内容运营', icon: 'content', path: '/admin/hub/content/announcements' },
      { index: '/admin/hub/business', title: '业务中心', icon: 'business', path: '/admin/hub/business/ai-usage' },
      
      { index: '/admin/hub/legal', title: '法律服务', icon: 'legal', path: '/admin/hub/legal/consult' },
    ],
  },
  {
    title: '系统',
    items: [
      {
        index: 'system',
        title: '系统设置',
        icon: 'settings',
        children: [
          { path: '/admin/hub/system/basic/general', title: '基础配置', icon: 'tools' },
          { path: '/admin/hub/system/settings', title: '平台配置', icon: 'platform' },
          { path: '/admin/hub/system/integrations', title: '服务集成', icon: 'integration' },
          
          { path: '/admin/hub/system/roles', title: '角色权限', icon: 'roles' },
          { path: '/admin/hub/system/audit-logs', title: '操作日志', icon: 'audit' },
          { path: '/admin/hub/system/profile', title: '管理员资料', icon: 'profile' },
        ],
      },
    ],
  },
]

const active = computed(() => {
  const p = route.path
  if (p.startsWith('/admin/hub/system/basic')) return '/admin/hub/system/basic/general'
  if (p.startsWith('/admin/hub/system/')) return p
  if (p.startsWith('/admin/hub/users')) return '/admin/hub/users'
  if (p.startsWith('/admin/hub/content')) return '/admin/hub/content'
  if (p.startsWith('/admin/hub/business')) return '/admin/hub/business'
  if (p.startsWith('/admin/hub/enterprise')) return '/admin/hub/enterprise'
  if (p.startsWith('/admin/hub/legal')) return '/admin/hub/legal'
  return p
})

const pageTitle = computed(() => (route.meta.title as string) || '运营后台')

const breadcrumbText = computed(() => {
  const hub =
    route.path.startsWith('/admin/hub/users') ? '用户中心'
    : route.path.startsWith('/admin/hub/content') ? '内容运营'
    : route.path.startsWith('/admin/hub/business') ? '业务中心'
    : route.path.startsWith('/admin/hub/enterprise') ? '企业服务'
    : route.path.startsWith('/admin/hub/legal') ? '法律服务'
    : route.path.startsWith('/admin/hub/system') ? '系统设置'
    : ''
  const prefix = platformName.value ? `${platformName.value} / ` : ''
  if (route.path === '/admin') return `${prefix}数据概览`
  if (hub) return `${prefix}${hub} / ${pageTitle.value}`
  return `${prefix}${pageTitle.value}`
})

const adminName = computed(() => userStore.nickname || '管理员')
const adminInitial = computed(() => (adminName.value[0] || '管').toUpperCase())

const defaultOpeneds = computed(() =>
  route.path.startsWith('/admin/hub/system/') ? ['system'] : [],
)

function navigate(path: string) {
  router.push(path)
}

function refresh() {
  router.go(0)
}

function logout() {
  userStore.logout()
  router.replace('/login')
}
</script>

<template>
  <el-container class="admin-layout" :class="{ 'is-collapsed': collapsed }">
    <el-aside :width="collapsed ? '72px' : '240px'" class="aside">
      <div class="brand admin-fade-in">
        <div class="brand-seal">{{ brandInitial }}</div>
        <div v-if="!collapsed" class="brand-text-wrap">
          <span class="brand-text">{{ platformName }}</span>
          <span class="brand-sub">运营管理中心</span>
        </div>
      </div>
      <el-scrollbar class="menu-scroll">
        <el-menu
          :key="collapsed ? 'collapsed' : 'expanded'"
          :default-active="active"
          :default-openeds="collapsed ? [] : defaultOpeneds"
          :collapse="collapsed"
          :collapse-transition="false"
          background-color="transparent"
          text-color="rgba(255,255,255,0.72)"
          active-text-color="#FFFFFF"
        >
          <template v-for="group in menuGroups" :key="group.title">
            <div v-if="!collapsed" class="menu-group-title">{{ group.title }}</div>
            <template v-for="item in group.items" :key="item.index">
              <el-sub-menu v-if="item.children?.length" :index="item.index">
                <template #title><span class="menu-label">{{ item.title }}</span></template>
                <template #icon>
                  <el-icon><component :is="resolveAdminIcon(item.icon)" /></el-icon>
                </template>
                <el-menu-item
                  v-for="child in item.children"
                  :key="child.path"
                  :index="child.path"
                  @click="navigate(child.path)"
                >
                  <el-icon><component :is="resolveAdminIcon(child.icon)" /></el-icon>
                  <template #title><span class="menu-label">{{ child.title }}</span></template>
                </el-menu-item>
              </el-sub-menu>
              <el-menu-item
                v-else
                :index="item.index"
                @click="navigate(item.path || item.index)"
              >
                <el-icon><component :is="resolveAdminIcon(item.icon)" /></el-icon>
                <template #title><span class="menu-label">{{ item.title }}</span></template>
              </el-menu-item>
            </template>
          </template>
        </el-menu>
      </el-scrollbar>
      <div class="aside-footer">
        <el-button text class="footer-btn" @click="collapsed = !collapsed">
          <el-icon><component :is="collapsed ? Expand : Fold" /></el-icon>
          <span v-if="!collapsed">收起侧栏</span>
        </el-button>
        <el-button text class="footer-btn" @click="openUserSite('/chat/ai')">
          <el-icon><Link /></el-icon>
          <span v-if="!collapsed">返回前台</span>
        </el-button>
      </div>
    </el-aside>
    <el-container direction="vertical" class="main-wrap">
      <el-header class="topbar" height="64px">
        <div class="topbar-left">
          <span class="topbar-breadcrumb">{{ breadcrumbText }}</span>
        </div>
        <div class="topbar-actions">
          <a class="topbar-link" href="javascript:void(0)" @click.prevent="openUserSite('/')">访问前台</a>
          <el-button size="small" @click="refresh">刷新</el-button>
          <el-dropdown trigger="click">
            <span class="admin-user">
              <el-avatar :size="32" class="admin-avatar">{{ adminInitial }}</el-avatar>
              {{ adminName }}
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="router.push('/admin/hub/system/profile')">
                  <el-icon><Lock /></el-icon>
                  修改资料
                </el-dropdown-item>
                <el-dropdown-item @click="router.push('/admin/hub/system/settings')">
                  <el-icon><Setting /></el-icon>
                  平台配置
                </el-dropdown-item>
                <el-dropdown-item divided @click="logout">
                  <el-icon><SwitchButton /></el-icon>
                  退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      <el-main class="main">
        <div class="page-wrap">
          <router-view v-slot="{ Component }">
            <transition name="admin-page" mode="out-in">
              <component :is="Component" />
            </transition>
          </router-view>
        </div>
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.brand-text-wrap {
  min-width: 0;
  overflow: hidden;
}

.main-wrap {
  flex: 1;
  min-width: 0;
  background: var(--adm-bg);
}
</style>
