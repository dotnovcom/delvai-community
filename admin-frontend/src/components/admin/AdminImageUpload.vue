<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage, type UploadRequestOptions } from 'element-plus'
import { Picture, Upload } from '@element-plus/icons-vue'
import { uploadAdminFile } from '../../api/admin'

const props = withDefaults(defineProps<{
  modelValue: string
  previewWidth?: string
  previewHeight?: string
  placeholder?: string
}>(), {
  previewWidth: '120px',
  previewHeight: '80px',
  placeholder: '暂无图片',
})

const emit = defineEmits<{ 'update:modelValue': [value: string] }>()

const uploading = ref(false)

async function handleUpload(options: UploadRequestOptions) {
  const file = options.file as File
  if (!file) return
  uploading.value = true
  try {
    const res = await uploadAdminFile(file)
    emit('update:modelValue', res.url)
    ElMessage.success('图片已上传')
    options.onSuccess?.(res)
  } catch {
    // 错误提示由 request 拦截器统一处理
  } finally {
    uploading.value = false
  }
}
</script>

<template>
  <div class="admin-image-upload">
    <div class="admin-image-upload__preview" :style="{ width: previewWidth, height: previewHeight }">
      <el-image v-if="modelValue" :src="modelValue" fit="cover" class="admin-image-upload__img" />
      <div v-else class="admin-image-upload__empty">
        <el-icon :size="26"><Picture /></el-icon>
        <span>{{ placeholder }}</span>
      </div>
    </div>

    <div class="admin-image-upload__panel">
      <el-upload
        accept="image/jpeg,image/png,image/gif,image/webp"
        :show-file-list="false"
        :disabled="uploading"
        :http-request="handleUpload"
        class="admin-image-upload__uploader"
      >
        <el-button type="primary" plain size="small" :loading="uploading">
          <el-icon class="admin-image-upload__btn-icon"><Upload /></el-icon>
          {{ uploading ? '上传中…' : '选择图片' }}
        </el-button>
      </el-upload>
      <p class="admin-image-upload__hint">支持 JPG / PNG / GIF / WebP，大小受「上传配置」限制</p>
      <el-input
        :model-value="modelValue"
        placeholder="或粘贴图片 URL"
        size="small"
        clearable
        @update:model-value="emit('update:modelValue', $event)"
      />
    </div>
  </div>
</template>

<style scoped>
.admin-image-upload {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  width: 100%;
  max-width: 520px;
}

.admin-image-upload__preview {
  flex-shrink: 0;
  border-radius: 8px;
  overflow: hidden;
  border: 1px dashed var(--adm-border, #e2e8f0);
  background: var(--adm-bg-subtle, #f8fafc);
}

.admin-image-upload__img {
  width: 100%;
  height: 100%;
  display: block;
}

.admin-image-upload__empty {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 8px;
  text-align: center;
  color: var(--adm-text-secondary, #64748b);
  font-size: 12px;
}

.admin-image-upload__empty .el-icon {
  color: var(--adm-text-muted, #94a3b8);
}

.admin-image-upload__panel {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.admin-image-upload__uploader :deep(.el-upload) {
  display: block;
}

.admin-image-upload__btn-icon {
  margin-right: 4px;
}

.admin-image-upload__hint {
  margin: 0;
  font-size: 12px;
  line-height: 1.45;
  color: var(--adm-text-secondary, #64748b);
}
</style>
