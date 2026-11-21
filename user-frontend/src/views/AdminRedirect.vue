<script setup lang="ts">
import { onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { adminUrl } from '../utils/adminOrigin'

const route = useRoute()

onMounted(() => {
  window.location.replace(adminUrl(route.fullPath))
})
</script>

<template>
  <div class="admin-redirect">正在打开运营后台…</div>
</template>

<style scoped>
.admin-redirect {
  min-height: 40vh;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #64748b;
  font-size: 14px;
}
</style>
