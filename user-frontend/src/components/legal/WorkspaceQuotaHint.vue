<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useFeatureQuotaHint } from '../../composables/useFeatureQuotaHint'

const props = defineProps<{
  quotaKeys: string[]
}>()

const router = useRouter()
const { hintText } = useFeatureQuotaHint(props.quotaKeys)

function goTopUp() {
  router.push({ path: '/profile/membership', query: { tab: 'peruse' } })
}
</script>

<template>
  <div v-if="hintText" class="ws-quota-hint">
    <span class="ws-quota-hint__text" :title="hintText">{{ hintText }}</span>
    <button type="button" class="ws-quota-hint__link" @click="goTopUp">增购</button>
  </div>
</template>

<style scoped>
.ws-quota-hint {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--ft-text-secondary, #64748b);
}
.ws-quota-hint__text {
  max-width: 280px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ws-quota-hint__link {
  border: none;
  background: none;
  padding: 0;
  font-size: 12px;
  color: var(--ft-primary, #4338ca);
  cursor: pointer;
  font-weight: 600;
}
.ws-quota-hint__link:hover {
  text-decoration: underline;
}
</style>
