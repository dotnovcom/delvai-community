<script setup lang="ts">
import { computed } from 'vue'

import { useRoute } from 'vue-router'

import ProfileSidebar from '../../components/profile/ProfileSidebar.vue'
import WorkspaceAnnouncement from '../../components/layout/WorkspaceAnnouncement.vue'
import SiteBottomBar from '../../components/layout/SiteBottomBar.vue'


const route = useRoute()


const activeMenu = computed(() => {
  if (route.name === 'ProfileOrders') return 'orders'
  if (route.name === 'ProfileRecords') return 'records'
  if (route.name === 'ProfileNotifications') return 'notifications'
  if (route.name === 'ProfileUsage') return 'usage'
  if (route.name === 'ProfileSecurity') return 'security'
  if (route.name === 'ProfileMembership') return 'membership'
  if (route.name === 'ProfileWallet') return 'wallet'
  return 'profile'
})


</script>

<template>
  <div class="profile-workspace">
    <ProfileSidebar :active="activeMenu" />
    <div class="profile-panel">
      <WorkspaceAnnouncement />
      <div
        class="profile-panel-body"
        :class="{ 'profile-panel-body--membership': activeMenu === 'membership' }"
      >
        <router-view v-slot="{ Component }">
          <transition name="page" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </div>
      <SiteBottomBar />
    </div>
    
  </div>
</template>

<style scoped>
.profile-workspace {
  height: 100%;
  min-height: 0;
  display: flex;
  background: #f3f4f6;
}

.profile-panel {
  flex: 1;
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.profile-panel-body {
  flex: 1;
  overflow-y: auto;
  min-height: 0;
  padding: 16px 20px 28px;
  background: #f3f4f6;
}

.profile-panel-body :deep(.profile-page) {
  width: 100%;
  max-width: none;
}

.profile-panel-body :deep(.user-card) {
  width: 100%;
  box-sizing: border-box;
}

.profile-panel-body--membership {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 16px 20px 20px;
  min-height: 0;
  background: #f3f4f6;
}

.profile-panel-body--membership :deep(.profile-membership-page) {
  flex: 1;
  min-height: 0;
}
</style>
