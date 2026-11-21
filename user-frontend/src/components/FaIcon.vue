<template>
  <i
    class="fa-icon"
    :class="[familyClass, `fa-${name}`]"
    :style="iconStyle"
    aria-hidden="true"
  />
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    name: string
    brand?: boolean
    size?: string | number
    color?: string
  }>(),
  { brand: false, size: '', color: '' },
)

const familyClass = computed(() => (props.brand ? 'fa-brands' : 'fa-solid'))

const iconStyle = computed(() => {
  const style: Record<string, string> = {}
  if (props.size !== '' && props.size != null) {
    style.fontSize = typeof props.size === 'number' ? `${props.size}px` : props.size
  }
  if (props.color) style.color = props.color
  return style
})
</script>

<style scoped>
.fa-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
  flex-shrink: 0;
  transition: transform 0.22s cubic-bezier(0.22, 1, 0.36, 1), opacity 0.22s ease;
}
</style>
