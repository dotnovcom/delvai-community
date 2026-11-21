<script setup lang="ts">
</script>

<template>
  <div class="app-shell">
    <main class="app-main app-main--flush">
      <router-view />
    </main>
  </div>
</template>

<style scoped>
.app-shell {
  height: 100vh;
  min-height: 100vh;
  max-height: 100vh;
  overflow: hidden;
  background: var(--ft-bg);
}

.app-main {
  height: 100%;
  width: 100%;
}

.app-main--flush {
  padding: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
</style>
