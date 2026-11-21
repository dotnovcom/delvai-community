import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  getMe,
  saveAuthResult,
  clearAuth,
  loadStoredUser,
} from '../api/auth'
import type { TokenResponse, UserInfo } from '../types/user'
import { getToken } from '../utils/request'

export const useUserStore = defineStore('user', () => {
  const token = ref(getToken())
  const userInfo = ref<UserInfo | null>(loadStoredUser())

  const isLoggedIn = computed(() => !!token.value)
  const isAdmin = computed(() => !!userInfo.value?.is_admin)
  const nickname = computed(() => userInfo.value?.nickname || '未登录')
  const avatar = computed(() => userInfo.value?.avatar || '')

  function setAuth(result: TokenResponse) {
    saveAuthResult(result)
    token.value = result.access_token
    userInfo.value = result.user
  }

  async function fetchUserInfo() {
    if (!token.value) return null
    const user = await getMe()
    userInfo.value = user
    localStorage.setItem('user_info', JSON.stringify(user))
    return user
  }

  function logout() {
    clearAuth()
    token.value = ''
    userInfo.value = null
  }

  return {
    token,
    userInfo,
    nickname,
    avatar,
    isAdmin,
    isLoggedIn,
    setAuth,
    fetchUserInfo,
    logout,
  }
})
