<script setup lang="ts">
</script>

<template>
  <div class="admin-system-body admin-fade-in">
    <router-view />
  </div>
</template>

<style scoped>
.admin-system-body {
  width: 100%;
  min-height: 100%;
  display: flex;
  flex-direction: column;
}

.admin-system-body > :deep(.open-api-page) {
  flex: 1;
  min-height: 0;
}
</style>
