import { createRouter, createWebHistory } from 'vue-router'

import { getToken } from '../utils/request'

import { useUserStore } from '../store/user'
import { usePublicConfig } from '../composables/usePublicConfig'
import { buildLoginRoute } from '../utils/authRedirect'
import { applySeo, resolveRouteSeo } from '../utils/seo'



const router = createRouter({

  history: createWebHistory(),

  routes: [

    { path: '/', redirect: '/admin' },

    {

      path: '/admin',

      component: () => import('../views/admin/AdminLayout.vue'),

      meta: { title: '运营后台', requiresAuth: true, requiresAdmin: true },

      children: [

        { path: '', name: 'AdminDashboard', component: () => import('../views/admin/Dashboard.vue'), meta: { title: '数据概览' } },

        {
          path: 'hub/users',
          component: () => import('../views/admin/hubs/UserHub.vue'),
          meta: { title: '用户中心' },
          redirect: '/admin/hub/users/list',
          children: [
            { path: 'list', name: 'AdminUsers', component: () => import('../views/admin/Users.vue'), meta: { title: '用户列表', hub: true } },
            { path: 'feedbacks', name: 'AdminFeedbacks', component: () => import('../views/admin/Feedbacks.vue'), meta: { title: '用户反馈', hub: true } },
          ],
        },

        {
          path: 'hub/content',
          component: () => import('../views/admin/hubs/ContentHub.vue'),
          meta: { title: '内容运营' },
          redirect: '/admin/hub/content/announcements',
          children: [
            { path: 'articles', redirect: '/admin/hub/content/announcements' },
            { path: 'announcements', name: 'AdminAnnouncements', component: () => import('../views/admin/Announcements.vue'), meta: { title: '平台公告', hub: true } },
            { path: 'legal', name: 'AdminLegalPages', component: () => import('../views/admin/LegalPages.vue'), meta: { title: '协议政策', hub: true } },
          ],
        },

        

        {
          path: 'hub/business',
          component: () => import('../views/admin/hubs/BusinessHub.vue'),
          meta: { title: '业务中心' },
          redirect: '/admin/hub/business/ai-usage',
          children: [
            { path: 'ai-usage', name: 'AdminAiUsage', component: () => import('../views/admin/AiUsage.vue'), meta: { title: 'AI 用量', hub: true } },
            { path: 'conversations', name: 'AdminConversations', component: () => import('../views/admin/Conversations.vue'), meta: { title: '对话管理', hub: true } },
          ],
        },

        {
          path: 'hub/legal',
          component: () => import('../views/admin/hubs/LegalServicesHub.vue'),
          meta: { title: '法律服务' },
          redirect: '/admin/hub/legal/consult',
          children: [
            { path: 'consult', name: 'AdminLegalConsult', component: () => import('../views/admin/legal/LegalConsult.vue'), meta: { title: '法律咨询', hub: true } },
            { path: 'chat-actions', name: 'AdminLegalChatActions', component: () => import('../views/admin/legal/LegalChatActions.vue'), meta: { title: '回复互动', hub: true } },
          ],
        },

        {
          path: 'hub/system',
          component: () => import('../views/admin/hubs/SystemHub.vue'),
          meta: { title: '系统设置' },
          redirect: '/admin/hub/system/basic/general',
          children: [
            {
              path: 'basic',
              component: () => import('../views/admin/hubs/BasicConfigHub.vue'),
              meta: { title: '基础配置' },
              redirect: '/admin/hub/system/basic/general',
              children: [
                { path: 'general', name: 'AdminBasicGeneral', component: () => import('../views/admin/BasicConfigTab.vue'), meta: { title: '常规配置', hub: true } },
                { path: 'upload', name: 'AdminBasicUpload', component: () => import('../views/admin/UploadConfigTab.vue'), meta: { title: '上传配置', hub: true } },
                { path: 'cache', name: 'AdminBasicCache', component: () => import('../views/admin/BasicConfigTab.vue'), meta: { title: '缓存配置', hub: true } },
                { path: 'security', name: 'AdminBasicSecurity', component: () => import('../views/admin/BasicConfigTab.vue'), meta: { title: '安全配置', hub: true } },
                { path: 'auth', name: 'AdminBasicAuth', component: () => import('../views/admin/BasicConfigTab.vue'), meta: { title: '登录注册', hub: true } },
              ],
            },
            { path: 'settings', name: 'AdminSettings', component: () => import('../views/admin/PlatformConfig.vue'), meta: { title: '平台配置', hub: true } },
            { path: 'integrations', name: 'AdminIntegrations', component: () => import('../views/admin/AiChatProvider.vue'), meta: { title: '服务集成', hub: true } },
            { path: 'roles', name: 'AdminRoles', component: () => import('../views/admin/Roles.vue'), meta: { title: '角色权限', hub: true } },
            { path: 'audit-logs', name: 'AdminAuditLogs', component: () => import('../views/admin/AuditLogs.vue'), meta: { title: '操作日志', hub: true } },
            { path: 'profile', name: 'AdminProfile', component: () => import('../views/admin/AdminProfile.vue'), meta: { title: '管理员资料', hub: true } },
          ],
        },

        { path: 'users', redirect: '/admin/hub/users/list' },
        { path: 'feedbacks', redirect: '/admin/hub/users/feedbacks' },
        { path: 'content', redirect: '/admin/hub/content/announcements' },
        { path: 'conversations', redirect: '/admin/hub/business/conversations' },
        { path: 'legal-consult', redirect: '/admin/hub/legal/consult' },
        { path: 'settings', redirect: '/admin/hub/system/settings' },
        { path: 'basic', redirect: '/admin/hub/system/basic/general' },
        { path: 'general', redirect: '/admin/hub/system/basic/general' },
        { path: 'ai-providers', redirect: '/admin/hub/system/integrations' },
        { path: 'roles', redirect: '/admin/hub/system/roles' },
        { path: 'audit-logs', redirect: '/admin/hub/system/audit-logs' },
        { path: 'profile', redirect: '/admin/hub/system/profile' },

      ],

    },

    { path: '/login', name: 'AdminLogin', component: () => import('../views/AdminLogin.vue'), meta: { title: '管理员登录', guest: true } },

  ],

})



router.beforeEach(async (to, _from, next) => {
  try {
    const { load, config } = usePublicConfig()
    await load()
    applySeo(resolveRouteSeo(to, config.value))
  } catch {
    applySeo(resolveRouteSeo(to, {}))
  }

  const token = getToken()

  if (to.meta.requiresAuth && !token) {
    next(buildLoginRoute(to.fullPath))
    return
  }

  if (to.meta.requiresAdmin) {
    const store = useUserStore()

    if (!token) {
      next(buildLoginRoute(to.fullPath, 'session_expired'))
      return
    }

    try {
      const user = await store.fetchUserInfo()
      if (!user?.is_admin) {
        store.logout()
        next(buildLoginRoute(to.fullPath, 'not_admin'))
        return
      }
    } catch {
      store.logout()
      next(buildLoginRoute(to.fullPath, 'session_expired'))
      return
    }
  }

  if (token && to.meta.guest) {
    next('/admin')
    return
  }

  next()

})

const CHUNK_RELOAD_KEY = 'delv_chunk_reload'

router.onError((err) => {
  const msg = String((err as Error)?.message || err)
  const staleChunk = /Failed to fetch dynamically imported module|Loading chunk|Unable to preload CSS/.test(msg)
  if (!staleChunk) return
  if (sessionStorage.getItem(CHUNK_RELOAD_KEY) === '1') return
  sessionStorage.setItem(CHUNK_RELOAD_KEY, '1')
  window.location.reload()
})

router.afterEach(() => {
  sessionStorage.removeItem(CHUNK_RELOAD_KEY)
})

export default router


