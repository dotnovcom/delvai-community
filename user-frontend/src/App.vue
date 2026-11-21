<script setup lang="ts">
import LoginDialog from './components/auth/LoginDialog.vue'
import QuotaExceededHandler from './components/QuotaExceededHandler.vue'
import MembershipRequiredHandler from './components/MembershipRequiredHandler.vue'
</script>

<template>
  <QuotaExceededHandler />
  <MembershipRequiredHandler />
  <router-view />
  <LoginDialog />
</template>

<style>
html,
body,
#app {
  height: 100%;
  margin: 0;
  overflow: hidden;
}
</style>
