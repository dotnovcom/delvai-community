<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useBrandLabels } from '../../composables/useBrandLabels'
import type { AuthView } from '../../composables/useLoginDialog'

const props = defineProps<{ view: AuthView }>()

const { platformName, config, load } = useBrandLabels()

const logoUrl = computed(() => (config.value.logo_url || '').trim())

const tagline = computed(() => {
  if (props.view === 'register') {
    return platformName.value
      ? `加入${platformName.value}，开启智能法律服务`
      : '开启智能法律服务'
  }
  if (props.view === 'forgot') return '通过验证码重置登录密码'
  return '登录后体验完整 AI 法律服务'
})

onMounted(() => load())
</script>

<template>
  <header class="auth-modal-head">
    <img
      v-if="logoUrl"
      :src="logoUrl"
      :alt="platformName || 'LOGO'"
      class="auth-modal-logo"
    />
    <strong v-else class="auth-modal-name">{{ platformName }}</strong>
    <p class="auth-modal-tagline">{{ tagline }}</p>
  </header>
</template>

<style scoped>
.auth-modal-head {
  text-align: center;
  padding: 50px 32px;
}

.auth-modal-logo {
  display: block;
  margin: 0 auto 12px;
  height: 56px;
  max-width: 220px;
  width: auto;
  object-fit: contain;
}

.auth-modal-name {
  display: block;
  margin-bottom: 10px;
  font-size: 24px;
  font-weight: 700;
  color: #111827;
  letter-spacing: 0.04em;
  line-height: 1.2;
}

.auth-modal-tagline {
  margin: 0;
  font-size: 13px;
  font-weight: 400;
  color: #9ca3af;
  line-height: 1.5;
}
</style>
