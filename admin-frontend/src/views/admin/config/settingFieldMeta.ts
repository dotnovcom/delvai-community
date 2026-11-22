export interface SettingSelectOption {
  label: string
  value: string
}

export interface SettingFieldMeta {
  hint?: string
  placeholder?: string
  options?: SettingSelectOption[]
}

export const SETTING_FIELD_META: Record<string, SettingFieldMeta> = {
  pc_enabled: {
    hint: '关闭后用户端仍可打开，但不再使用本页的站点地址。',
  },
  pc_site_url: {
    hint: '电脑站点完整地址，含协议、不含末尾斜杠。本地社区版一般是 http://localhost:18180。',
    placeholder: 'http://localhost:18180',
  },
  pc_seo_title: {
    hint: '写入页面标题。留空则使用基础配置里的 SEO 标题。',
  },
  pc_seo_keywords: {
    hint: '英文逗号分隔。留空则使用基础配置关键词。',
  },
  pc_seo_description: {
    hint: '写入页面描述。留空则使用基础配置描述。',
  },
  pc_og_image: {
    hint: '分享预览图。留空则使用基础配置里的分享图。',
  },
  pc_robots: {
    hint: '搜索引擎抓取策略。',
    options: [
      { label: 'index, follow（允许收录）', value: 'index, follow' },
      { label: 'noindex, follow', value: 'noindex, follow' },
      { label: 'noindex, nofollow（禁止收录）', value: 'noindex, nofollow' },
    ],
  },
  pc_baidu_site_verification: {
    hint: '百度搜索资源平台站点验证码。',
  },
  pc_google_site_verification: {
    hint: 'Google Search Console 站点验证码。',
  },
  sms_active_provider: {
    hint: '登录、注册和找回密码的短信从这里选择的渠道发出。',
    options: [
      { label: '阿里云短信', value: 'aliyun' },
      { label: '腾讯云短信', value: 'tencent' },
    ],
  },
  free_daily_chat_quota: {
    hint: '每个用户每个自然日可发起的咨询次数。',
  },
  ai_mock_enabled: {
    hint: '开启后咨询返回示例回答，不读取对话模型密钥。',
  },
}

export function getSettingFieldMeta(key: string): SettingFieldMeta {
  return SETTING_FIELD_META[key] ?? {}
}
