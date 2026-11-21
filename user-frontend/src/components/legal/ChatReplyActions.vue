<script setup lang="ts">
import FaIcon from '../FaIcon.vue'

defineProps<{
  showCopy: boolean
  showRegenerate: boolean
  showLike: boolean
  showDislike: boolean
  showSpeak: boolean
  showShare: boolean
  liked: boolean
  disliked: boolean
  speaking: boolean
  disabled: boolean
}>()

const emit = defineEmits<{
  copy: []
  regenerate: []
  like: []
  dislike: []
  speak: []
  share: []
}>()
</script>

<template>
  <div class="reply-actions">
    <button v-if="showCopy" type="button" class="reply-action" title="复制" :disabled="disabled" @click="emit('copy')">
      <FaIcon name="copy" />
    </button>
    <button v-if="showRegenerate" type="button" class="reply-action" title="重新生成" :disabled="disabled" @click="emit('regenerate')">
      <FaIcon name="rotate-right" />
    </button>
    <button
      v-if="showLike"
      type="button"
      class="reply-action"
      :class="{ 'is-on': liked }"
      title="赞"
      :disabled="disabled"
      @click="emit('like')"
    >
      <FaIcon name="thumbs-up" />
    </button>
    <button
      v-if="showDislike"
      type="button"
      class="reply-action"
      :class="{ 'is-on': disliked }"
      title="踩"
      :disabled="disabled"
      @click="emit('dislike')"
    >
      <FaIcon name="thumbs-down" />
    </button>
    <button
      v-if="showSpeak"
      type="button"
      class="reply-action"
      :class="{ 'is-on': speaking }"
      title="朗读"
      :disabled="disabled"
      @click="emit('speak')"
    >
      <FaIcon name="volume-high" />
    </button>
    <button v-if="showShare" type="button" class="reply-action" title="分享" :disabled="disabled" @click="emit('share')">
      <FaIcon name="share-from-square" />
    </button>
  </div>
</template>

<style scoped>
.reply-actions {
  display: flex;
  align-items: center;
  gap: 2px;
  margin-top: 6px;
}

.reply-action {
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: #9aa3b2;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
}

.reply-action:hover:not(:disabled) {
  background: rgba(15, 23, 42, 0.06);
  color: #64748b;
}

.reply-action.is-on {
  color: var(--ft-primary, #10b981);
}

.reply-action:disabled {
  opacity: 0.45;
  cursor: default;
}
</style>
