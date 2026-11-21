<script setup lang="ts">
import type { Component } from 'vue'
import { useRouter } from 'vue-router'

export type StatAccent = 'indigo' | 'amber' | 'emerald' | 'violet' | 'ruby' | 'ocean' | 'coral' | 'magenta'

const props = defineProps<{
  label: string
  value: string | number
  sub?: string
  accent?: StatAccent
  icon?: Component
  to?: string
}>()

const router = useRouter()

function onClick() {
  if (props.to) router.push(props.to)
}
</script>

<template>
  <div
    class="admin-stat-card"
    :class="[`admin-stat-card--${accent || 'indigo'}`, { 'admin-stat-card--link': !!to }]"
    @click="onClick"
  >
    <div class="admin-stat-card__icon-wrap">
      <el-icon v-if="icon" class="admin-stat-card__icon"><component :is="icon" /></el-icon>
    </div>
    <div class="admin-stat-card__body">
      <p class="admin-stat-card__label">{{ label }}</p>
      <p class="admin-stat-card__value">{{ value }}</p>
      <p v-if="sub" class="admin-stat-card__sub">{{ sub }}</p>
    </div>
  </div>
</template>
