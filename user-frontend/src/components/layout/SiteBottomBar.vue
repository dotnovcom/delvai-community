<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { getPublicConfig, getLegalPages, EMPTY_LEGAL_PAGES, type LegalPages, type PublicConfig } from '../../api/cms'
import { AI_DISCLAIMER } from '../../constants/aiDisclaimer'
import { sanitizeHtml } from '../../utils/sanitizeHtml'

withDefaults(
  defineProps<{
    showDisclaimer?: boolean
  }>(),
  { showDisclaimer: true },
)

const config = ref<PublicConfig>({})
const legal = ref<LegalPages>({ ...EMPTY_LEGAL_PAGES })
const legalVisible = ref(false)
const legalTitle = ref('')
const legalContent = ref('')

async function load() {
  try {
    const [cfg, pages] = await Promise.all([getPublicConfig(), getLegalPages()])
    config.value = cfg
    legal.value = pages
  } catch {
    config.value = {}
    legal.value = { ...EMPTY_LEGAL_PAGES }
  }
}

const showContact = computed(() => legalTitle.value === '联系我们')

function openLegal(type: 'agreement' | 'privacy' | 'about' | 'contact') {
  const map = {
    agreement: ['用户协议', legal.value.user_agreement],
    privacy: ['隐私政策', legal.value.privacy_policy],
    about: ['关于平台', legal.value.about_platform || ''],
    contact: ['联系我们', legal.value.contact_us || ''],
  } as const
  legalTitle.value = map[type][0]
  legalContent.value = map[type][1]
  legalVisible.value = true
}

onMounted(load)
</script>

<template>
  <footer class="site-bottom-bar">
    <p v-if="showDisclaimer" class="site-bottom-bar__disclaimer" role="note">{{ AI_DISCLAIMER }}</p>
    <div class="site-bottom-bar__meta">
      <span class="site-bottom-bar__copy">© {{ new Date().getFullYear() }} {{ config.platform_name || '' }}</span>
      <a
        v-if="config.icp_number"
        class="site-bottom-bar__link"
        href="https://beian.miit.gov.cn/"
        target="_blank"
        rel="noopener"
      >{{ config.icp_number }}</a>
      <span v-if="config.police_icp_number" class="site-bottom-bar__text">{{ config.police_icp_number }}</span>
      <span class="site-bottom-bar__sep">|</span>
      <a href="#" class="site-bottom-bar__link" @click.prevent="openLegal('agreement')">用户协议</a>
      <a href="#" class="site-bottom-bar__link" @click.prevent="openLegal('privacy')">隐私政策</a>
      <a href="#" class="site-bottom-bar__link" @click.prevent="openLegal('about')">关于平台</a>
      <a href="#" class="site-bottom-bar__link" @click.prevent="openLegal('contact')">联系我们</a>
    </div>

    <el-dialog v-model="legalVisible" :title="legalTitle" width="720px" append-to-body align-center class="ft-legal-dialog">
      <div v-if="showContact" class="contact-card">
        <p v-if="config.support_phone">客服电话 {{ config.support_phone }}</p>
        <p v-if="config.support_email">客服邮箱 <a :href="`mailto:${config.support_email}`">{{ config.support_email }}</a></p>
        <p v-if="config.company_address">公司地址 {{ config.company_address }}</p>
        <div v-if="config.support_qr_url || config.wechat_official_qr_url" class="contact-qr-row">
          <div v-if="config.support_qr_url" class="contact-qr">
            <img :src="config.support_qr_url" alt="客服二维码" />
            <span>客服微信</span>
          </div>
          <div v-if="config.wechat_official_qr_url" class="contact-qr">
            <img :src="config.wechat_official_qr_url" alt="公众号二维码" />
            <span>公众号</span>
          </div>
        </div>
      </div>
      <div v-if="legalContent" class="ft-legal-doc" v-html="sanitizeHtml(legalContent)" />
      <div v-else-if="!showContact" class="ft-legal-doc"><p>暂无内容</p></div>
    </el-dialog>
  </footer>
</template>

<style scoped>
.site-bottom-bar {
  flex-shrink: 0;
  padding: 6px 16px 8px;
  background: var(--ft-card-bg, #fff);
  border-top: 1px solid var(--ft-border, #edf2f7);
  text-align: center;
}

.site-bottom-bar__disclaimer {
  margin: 0 0 4px;
  font-size: 11px;
  line-height: 1.45;
  color: var(--ft-text-secondary, #718096);
}

.contact-card {
  margin-bottom: 16px;
  padding: 14px 16px;
  border-radius: 12px;
  background: #f6f4ff;
  color: #1a1a2e;
  line-height: 1.7;
}

.contact-card p {
  margin: 0;
}

.contact-qr-row {
  display: flex;
  gap: 20px;
  margin-top: 12px;
}

.contact-qr {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #5b5675;
}

.contact-qr img {
  width: 120px;
  height: 120px;
  object-fit: contain;
  background: #fff;
  border-radius: 8px;
}

.site-bottom-bar__meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: center;
  gap: 6px 10px;
  font-size: 11px;
  line-height: 1.4;
  color: var(--ft-text-secondary, #718096);
}

.site-bottom-bar__copy,
.site-bottom-bar__text {
  color: inherit;
}

.site-bottom-bar__link {
  color: inherit;
  text-decoration: none;
  transition: color 0.2s;
}

.site-bottom-bar__link:hover {
  color: var(--ft-primary, #10b981);
}

.site-bottom-bar__sep {
  opacity: 0.45;
}

.legal-content {
  max-height: 60vh;
  overflow-y: auto;
  line-height: 1.7;
  font-size: 14px;
}

.legal-content :deep(h2) {
  margin-top: 0;
}
</style>
