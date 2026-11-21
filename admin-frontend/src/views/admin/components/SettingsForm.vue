<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { listAdminSettings, updateAdminSettings, type SystemSetting } from '../../../api/admin'
import { fallbackForKey } from '../config/settingFallbacks'
import SettingField from './SettingField.vue'

const props = withDefaults(defineProps<{
  title: string
  categories?: string[]
  keys?: string[]
  sections?: { title: string; description?: string; keys: string[]; enableKey?: string }[]
  saveLabel?: string
  hideHeader?: boolean
  showFooterActions?: boolean
  embedded?: boolean
}>(), {
  saveLabel: '保存配置',
  hideHeader: false,
  showFooterActions: false,
  embedded: false,
})

const loading = ref(false)
const saving = ref(false)
const settings = ref<SystemSetting[]>([])
const form = ref<Record<string, string>>({})
const activeTab = ref('')
const activeSection = ref('')

function seedMissingFormValues() {
  const next = { ...form.value }
  let changed = false
  for (const key of requiredKeys.value) {
    if (next[key] === undefined) {
      next[key] = fallbackForKey(key)?.value ?? ''
      changed = true
    }
  }
  if (changed) form.value = next
}

const CATEGORY_META: Record<string, string> = {
  general: '站点与 SEO',
  auth: '登录注册',
  basic: '运维能力',
  pc: 'PC 端',
  h5: 'H5 端',
  wechat_mp: '微信小程序',
  wechat_official: '微信公众号',
  douyin_mp: '抖音小程序',
  android: '安卓端',
  ios: 'iOS 端',
  sms: '短信',
  payment: '支付',
  open_api: '开放 API',
  billing: '计费与积分',
}

const requiredKeys = computed(() => {
  const keys = new Set<string>()
  props.keys?.forEach((k) => keys.add(k))
  props.sections?.forEach((sec) => sec.keys.forEach((k) => keys.add(k)))
  return keys
})

watch(requiredKeys, seedMissingFormValues, { immediate: true })

const effectiveSettings = computed(() => {
  const list = [...settings.value]
  for (const key of requiredKeys.value) {
    if (!list.some((s) => s.key === key)) {
      const fb = fallbackForKey(key)
      if (fb) list.push(fb)
    }
  }
  return list
})

const filteredSettings = computed(() => {
  if (props.keys?.length) {
    return effectiveSettings.value.filter((s) => props.keys!.includes(s.key))
  }
  if (props.categories?.length) {
    return effectiveSettings.value.filter((s) => props.categories!.includes(s.category))
  }
  return effectiveSettings.value
})

const tabCategories = computed(() => [...new Set(filteredSettings.value.map((s) => s.category))])
const useSectionLayout = computed(() => !!(props.embedded && props.sections?.length))
const preferSectionsOverCategories = computed(() => !!props.sections?.length)
const useTabs = computed(
  () => tabCategories.value.length > 1 && !preferSectionsOverCategories.value,
)

const currentItems = computed(() =>
  useTabs.value
    ? filteredSettings.value.filter((s) => s.category === activeTab.value)
    : filteredSettings.value,
)

const settingsByKey = computed(() => {
  const map = new Map<string, SystemSetting>()
  filteredSettings.value.forEach((s) => map.set(s.key, s))
  return map
})

function isOn(value?: string) {
  return value === 'true' || value === '1'
}

const sectionGroups = computed(() => {
  if (!props.sections?.length) return null
  return props.sections.map((section) => ({
    title: section.title,
    description: section.description,
    enableKey: section.enableKey,
    items: section.keys
      .map((key) => settingsByKey.value.get(key) ?? fallbackForKey(key))
      .filter((item): item is SystemSetting => !!item),
  }))
})

const visibleSectionGroups = computed(() => {
  if (!sectionGroups.value) return null
  return sectionGroups.value.filter((section) => {
    if (!section.enableKey) return true
    return isOn(form.value[section.enableKey])
  })
})

async function load() {
  loading.value = true
  try {
    settings.value = await listAdminSettings()
    const map: Record<string, string> = {}
    settings.value.forEach((s) => { map[s.key] = s.value ?? '' })
    for (const key of requiredKeys.value) {
      if (map[key] === undefined) {
        map[key] = fallbackForKey(key)?.value ?? ''
      }
    }
    form.value = map
    if (tabCategories.value.length && !tabCategories.value.includes(activeTab.value)) {
      activeTab.value = tabCategories.value[0]
    }
  } finally {
    loading.value = false
  }
}

async function handleSave() {
  saving.value = true
  try {
    const items = filteredSettings.value.map((s) => ({
      key: s.key,
      value: form.value[s.key] ?? '',
      category: s.category,
      label: s.label,
      value_type: s.value_type,
    }))
    await updateAdminSettings(items)
    ElMessage.success('配置已保存，实时生效')
    window.dispatchEvent(new Event('admin-settings-saved'))
    await load()
  } finally {
    saving.value = false
  }
}

watch(tabCategories, (cats) => {
  if (cats.length && !cats.includes(activeTab.value)) activeTab.value = cats[0]
})

watch(visibleSectionGroups, (groups) => {
  if (groups?.length && !groups.some((g) => g.title === activeSection.value)) {
    activeSection.value = groups[0]?.title ?? ''
  }
}, { immediate: true })

onMounted(load)

defineExpose({ reload: load, form })
</script>

<template>
  <div v-loading="loading" class="admin-page settings-page">
    <div v-if="!hideHeader && !embedded" class="admin-page-header">
      <div>
        <h2>{{ title }}</h2>
      </div>
      <el-button type="primary" :loading="saving" @click="handleSave">{{ saving ? '保存中…' : saveLabel }}</el-button>
    </div>

    <div :class="embedded ? 'settings-panel-embedded' : 'admin-panel-card settings-panel'">
      <template v-if="useSectionLayout">
        <div class="admin-panel-body settings-panel-body settings-panel-body--embedded">
          <el-form label-width="220px" label-position="right" class="settings-form">
            <template v-for="(section, index) in visibleSectionGroups" :key="section.title">
              <div v-if="index > 0" class="settings-section-divider" />
              <div class="settings-section-block">
                <h3 class="settings-section-title">{{ section.title }}</h3>
                <p v-if="section.description" class="settings-section-desc">{{ section.description }}</p>
                <el-form-item v-for="item in section.items" :key="item.key" :label="item.label || item.key">
                  <SettingField v-model="form[item.key]" :item="item" />
                </el-form-item>
              </div>
            </template>
          </el-form>
          <div v-if="showFooterActions" class="settings-footer">
            <el-button type="primary" :loading="saving" @click="handleSave">{{ saveLabel }}</el-button>
          </div>
        </div>
      </template>

      <template v-else>
      <el-tabs v-if="useTabs" v-model="activeTab" class="admin-segment-tabs">
        <el-tab-pane
          v-for="cat in tabCategories"
          :key="cat"
          :name="cat"
        >
          <template #label>
            <span class="segment-tab-label">{{ CATEGORY_META[cat] || cat }}</span>
          </template>
        </el-tab-pane>
      </el-tabs>

      <el-tabs
        v-else-if="visibleSectionGroups?.length"
        v-model="activeSection"
        class="admin-segment-tabs"
      >
        <el-tab-pane
          v-for="section in visibleSectionGroups"
          :key="section.title"
          :name="section.title"
        >
          <template #label>
            <span class="segment-tab-label">{{ section.title }}</span>
          </template>
        </el-tab-pane>
      </el-tabs>

      <div class="admin-panel-body settings-panel-body" :class="{ 'settings-panel-body--embedded': embedded }">
        <el-form
          v-if="useTabs"
          label-width="220px"
          label-position="right"
          class="settings-form"
        >
          <el-form-item
            v-for="item in filteredSettings.filter((s) => s.category === activeTab)"
            :key="item.key"
            :label="item.label || item.key"
          >
            <SettingField v-model="form[item.key]" :item="item" />
          </el-form-item>
        </el-form>

        <el-form
          v-else-if="visibleSectionGroups?.length"
          label-width="220px"
          label-position="right"
          class="settings-form"
        >
          <template v-for="section in visibleSectionGroups" :key="section.title">
            <template v-if="section.title === activeSection">
              <p v-if="section.description" class="settings-section-desc">{{ section.description }}</p>
              <el-form-item v-for="item in section.items" :key="item.key" :label="item.label || item.key">
                <SettingField v-model="form[item.key]" :item="item" />
              </el-form-item>
            </template>
          </template>
        </el-form>

        <el-form v-else label-width="220px" label-position="right" class="settings-form">
          <el-form-item v-for="item in currentItems" :key="item.key" :label="item.label || item.key">
            <SettingField v-model="form[item.key]" :item="item" />
          </el-form-item>
        </el-form>

        <div v-if="hideHeader && showFooterActions" class="settings-footer">
          <el-button type="primary" :loading="saving" @click="handleSave">{{ saveLabel }}</el-button>
        </div>
        <div v-else-if="embedded && showFooterActions" class="settings-footer">
          <el-button type="primary" :loading="saving" @click="handleSave">{{ saveLabel }}</el-button>
        </div>
      </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.settings-page { width: 100%; }
.settings-panel-embedded {
  width: 100%;
}
.settings-panel-body--embedded {
  padding: 20px 0 0;
}
.settings-panel-body {
  padding-top: 20px;
}
.settings-form {
  max-width: 880px;
  width: 100%;
}
.settings-form :deep(.el-form-item) {
  margin-bottom: 22px;
}
.settings-form :deep(.el-input),
.settings-form :deep(.el-textarea) {
  max-width: 520px;
}
.settings-inner-panel {
  border: 1px solid var(--ft-border, #e2e8f0);
  overflow: hidden;
}
.settings-footer {
  margin-top: 8px;
  padding-top: 16px;
  border-top: 1px solid var(--ft-border, #e2e8f0);
}
.settings-section-block {
  padding-bottom: 4px;
}
.settings-section-title {
  margin: 0 0 8px;
  font-size: 15px;
  font-weight: 600;
  color: var(--ft-text-primary, #1e293b);
  line-height: 1.4;
}
.settings-section-desc {
  margin: 0 0 18px;
  font-size: 13px;
  line-height: 1.6;
  color: var(--ft-text-secondary, #64748b);
  max-width: 760px;
}
.settings-section-divider {
  margin: 8px 0 24px;
  border-top: 1px solid var(--ft-border, #e2e8f0);
}
</style>
