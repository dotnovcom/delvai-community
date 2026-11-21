<script setup lang="ts">
import { computed } from 'vue'
import type { SystemSetting } from '../../../api/admin'
import AdminImageUpload from '../../../components/admin/AdminImageUpload.vue'
import { getSettingFieldMeta } from '../config/settingFieldMeta'

const props = defineProps<{
  item: SystemSetting
  modelValue: string
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const meta = computed(() => getSettingFieldMeta(props.item.key))

const isSwitch = computed(() =>
  props.item.value_type === 'boolean' || props.item.key.endsWith('_enabled'),
)

const isTextarea = computed(() =>
  props.item.value_type === 'text'
  || props.item.value_type === 'json'
  || props.item.value_type === 'textarea'
  || props.item.key.includes('announcement')
  || props.item.key.includes('discount')
  || props.item.key.includes('private_key')
  || props.item.key.includes('public_key'),
)

const isImage = computed(() =>
  props.item.value_type === 'image'
  || props.item.key.endsWith('_qr_url')
  || props.item.key.endsWith('_og_image')
  || props.item.key.endsWith('_touch_icon')
  || ['logo_url', 'favicon_url', 'og_image'].includes(props.item.key),
)

const isSelect = computed(() => (meta.value.options?.length ?? 0) > 0)
const isSecret = computed(() =>
  !!props.item.is_secret || props.item.value_type === 'secret',
)

function onUpdate(value: string) {
  emit('update:modelValue', value ?? '')
}
</script>

<template>
  <div class="setting-field">
    <el-switch
      v-if="isSwitch"
      :model-value="modelValue"
      active-value="true"
      inactive-value="false"
      @update:model-value="onUpdate($event as string)"
    />
    <AdminImageUpload
      v-else-if="isImage"
      :model-value="modelValue"
      @update:model-value="onUpdate"
    />
    <el-select
      v-else-if="isSelect"
      :model-value="modelValue"
      style="width: 100%; max-width: 520px"
      @update:model-value="onUpdate"
    >
      <el-option
        v-for="opt in meta.options"
        :key="opt.value"
        :label="opt.label"
        :value="opt.value"
      />
    </el-select>
    <el-input
      v-else-if="isTextarea"
      :model-value="modelValue"
      type="textarea"
      :rows="item.value_type === 'json' ? 4 : 3"
      :placeholder="meta.placeholder || ''"
      @update:model-value="onUpdate"
    />
    <el-input
      v-else
      :model-value="modelValue"
      :placeholder="isSecret ? (meta.placeholder || '留空则不修改') : (meta.placeholder || '')"
      :type="isSecret ? 'password' : 'text'"
      :show-password="isSecret"
      @update:model-value="onUpdate"
    />
    <p v-if="meta.hint" class="setting-field-hint">{{ meta.hint }}</p>
  </div>
</template>

<style scoped>
.setting-field {
  width: 100%;
}
.setting-field-hint {
  margin: 6px 0 0;
  font-size: 12px;
  line-height: 1.55;
  color: var(--ft-text-secondary, #64748b);
  max-width: 560px;
}
</style>
