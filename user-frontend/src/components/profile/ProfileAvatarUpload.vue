<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ElMessage, type UploadRequestOptions } from 'element-plus'
import { Camera, Picture } from '@element-plus/icons-vue'
import { uploadAvatar } from '../../api/auth'
import { useUserStore } from '../../store/user'

const props = withDefaults(defineProps<{
  modelValue: string
  nickname?: string
}>(), {
  nickname: '',
})

const emit = defineEmits<{ 'update:modelValue': [value: string] }>()
const userStore = useUserStore()

const uploading = ref(false)

function toSameOriginFileUrl(url: string) {
  const raw = url.trim()
  if (!raw) return ''
  try {
    const parsed = new URL(raw, window.location.origin)
    if (parsed.hostname === 'localhost' || parsed.hostname === '127.0.0.1') {
      return `${parsed.pathname}${parsed.search}`
    }
  } catch {
    return raw
  }
  return raw
}

const previewSrc = computed(() => toSameOriginFileUrl(props.modelValue || ''))

watch(
  () => props.modelValue,
  (value) => {
    const next = toSameOriginFileUrl(value || '')
    if (next && next !== value) emit('update:modelValue', next)
  },
  { immediate: true },
)

function applyAvatar(url: string) {
  emit('update:modelValue', url)
  if (!userStore.userInfo) return
  userStore.userInfo = { ...userStore.userInfo, avatar: url || null }
  localStorage.setItem('user_info', JSON.stringify(userStore.userInfo))
}

async function handleUpload(options: UploadRequestOptions) {
  const file = options.file as File
  if (!file) return
  uploading.value = true
  try {
    const res = await uploadAvatar(file)
    const url = res.avatar || res.url
    applyAvatar(url)
    ElMessage.success('头像已上传')
    options.onSuccess?.(res)
  } catch {
    // 错误由 request 拦截器提示
  } finally {
    uploading.value = false
  }
}
</script>

<template>
  <div class="profile-avatar-upload">
    <div class="profile-avatar-upload__preview">
      <el-upload
        class="profile-avatar-upload__hit"
        accept="image/jpeg,image/png,image/gif,image/webp"
        :show-file-list="false"
        :disabled="uploading"
        :http-request="handleUpload"
      >
        <el-avatar :size="96" :src="previewSrc || undefined" class="profile-avatar-upload__avatar">
          {{ (nickname || '?').slice(0, 1) }}
        </el-avatar>
      </el-upload>
      <el-upload
        accept="image/jpeg,image/png,image/gif,image/webp"
        :show-file-list="false"
        :disabled="uploading"
        :http-request="handleUpload"
      >
        <el-button type="primary" plain size="small" :loading="uploading" class="profile-avatar-upload__btn">
          <el-icon><Camera /></el-icon>
          {{ uploading ? '上传中…' : '上传头像' }}
        </el-button>
      </el-upload>
    </div>
    <div class="profile-avatar-upload__url">
      <label class="profile-avatar-upload__label">头像链接（可选）</label>
      <el-input
        :model-value="previewSrc"
        placeholder="粘贴图片 URL，或点击左侧上传"
        clearable
        @update:model-value="applyAvatar"
      >
        <template #prefix>
          <el-icon><Picture /></el-icon>
        </template>
      </el-input>
    </div>
  </div>
</template>

<style scoped>
.profile-avatar-upload {
  display: flex;
  gap: 24px;
  align-items: flex-start;
  flex-wrap: wrap;
}

.profile-avatar-upload__preview {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}

.profile-avatar-upload__hit {
  cursor: pointer;
  line-height: 0;
}

.profile-avatar-upload__avatar {
  border: 3px solid #d1fae5;
  box-shadow: 0 4px 16px rgba(16, 185, 129, 0.16);
  cursor: pointer;
}

.profile-avatar-upload__btn .el-icon {
  margin-right: 4px;
}

.profile-avatar-upload__url {
  flex: 1;
  min-width: 220px;
}

.profile-avatar-upload__label {
  display: block;
  margin-bottom: 8px;
  font-size: 13px;
  font-weight: 500;
  color: var(--ft-text-secondary, #64748b);
}
</style>
