import { createRouter, createWebHistory } from 'vue-router'

import { getToken } from '../utils/request'

import { useUserStore } from '../store/user'
import { usePublicConfig } from '../composables/usePublicConfig'
import { userNeedsBinding } from '../composables/useAuthConfig'
import { buildLoginRoute } from '../utils/authRedirect'
import { applySeo, resolveRouteSeo } from '../utils/seo'
import { redirectPcToH5 } from '../utils/siteRedirect'



const router = createRouter({

  history: createWebHistory(),

  routes: [

    {

      path: '/',

      component: () => import('../components/layout/AppLayout.vue'),

      children: [

        { path: '', redirect: '/chat/ai' },

        { path: 'chat', redirect: '/chat/ai' },





        { path: 'chat/:func', name: 'LegalWorkspace', component: () => import('../views/legal/LegalWorkspace.vue'), meta: { title: '', layout: 'workspace', flush: true, fullHeight: true } },





        { path: 'news', name: 'News', component: () => import('../views/News.vue'), meta: { title: '平台公告' } },

        { path: 'news/:id', name: 'NewsDetail', component: () => import('../views/NewsDetail.vue'), meta: { title: '公告详情' } },




        {
          path: 'profile',
          component: () => import('../views/profile/ProfileWorkspace.vue'),
          meta: { title: '个人中心', requiresAuth: true, layout: 'workspace', flush: true, fullHeight: true },
          children: [
            { path: '', name: 'Profile', component: () => import('../views/profile/Profile.vue'), meta: { title: '个人中心' } },
            { path: 'usage', name: 'ProfileUsage', component: () => import('../views/profile/ProfileUsage.vue'), meta: { title: '用量统计' } },
            { path: 'records', name: 'ProfileRecords', component: () => import('../views/profile/ProfileRecords.vue'), meta: { title: '我的记录' } },
            { path: 'notifications', name: 'ProfileNotifications', component: () => import('../views/profile/ProfileNotifications.vue'), meta: { title: '站内信' } },
            { path: 'security', name: 'ProfileSecurity', component: () => import('../views/profile/ProfileSecurity.vue'), meta: { title: '账号安全' } },
          ],
        },





        { path: 'share/:token', name: 'ChatShare', component: () => import('../views/ChatShare.vue'), meta: { title: '分享内容', hideFooter: true } },

      ],

    },

    {
      path: '/admin',
      name: 'AdminRedirect',
      component: () => import('../views/AdminRedirect.vue'),
      meta: { title: '运营后台' },
    },
    {
      path: '/admin/:pathMatch(.*)*',
      name: 'AdminRedirectNested',
      component: () => import('../views/AdminRedirect.vue'),
      meta: { title: '运营后台' },
    },

    { path: '/login', name: 'Login', component: () => import('../views/AuthLegacyRedirect.vue'), meta: { title: '登录', guest: true } },

    { path: '/register', name: 'Register', component: () => import('../views/AuthLegacyRedirect.vue'), meta: { title: '注册', guest: true } },

    { path: '/forgot-password', name: 'ForgotPassword', component: () => import('../views/AuthLegacyRedirect.vue'), meta: { title: '找回密码', guest: true } },

  ],

})



router.beforeEach(async (to, _from, next) => {
  try {
    const { load, config } = usePublicConfig()
    await load()
    if (redirectPcToH5(config.value, to.fullPath)) {
      next(false)
      return
    }
    applySeo(resolveRouteSeo(to, config.value))
  } catch {
    applySeo(resolveRouteSeo(to, {}))
  }

  const token = getToken()

  if (to.meta.requiresAuth && !token) {
    next(buildLoginRoute(to.fullPath))
    return
  }

  if (token && to.meta.requiresAuth && to.meta.guest !== true) {
    const store = useUserStore()
    try {
      const user = store.userInfo?.id ? store.userInfo : await store.fetchUserInfo()
      if (userNeedsBinding(user)) {
        const onSecurity = to.path === '/profile/security' || to.name === 'ProfileSecurity'
        if (!onSecurity) {
          next({ path: '/profile/security', query: { bind: 'required' } })
          return
        }
      }
    } catch {
      /* 用户信息拉取失败时不阻断导航 */
    }
  }

  if (token && to.meta.guest) {

    next('/chat/ai')

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


