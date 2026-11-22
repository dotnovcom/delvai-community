import type { AdminIconName } from '../../../components/admin/adminIcons'

export interface BasicConfigTabDef {

  name: string

  label: string

  icon: AdminIconName

  path: string

  categories?: string[]

  keys?: string[]

  sections?: { title: string; description?: string; keys: string[] }[]

}



export const GENERAL_CONFIG_SECTIONS: { title: string; keys: string[] }[] = [
  {
    title: '站点与品牌',
    keys: ['platform_name', 'ai_nav_label', 'logo_url', 'favicon_url', 'site_title', 'og_image'],
  },
  {
    title: 'SEO 优化',
    keys: ['site_keywords', 'site_description'],
  },
  {
    title: '联系信息',
    keys: ['support_phone', 'support_email', 'company_address', 'support_qr_url'],
  },
  {
    title: '备案信息',
    keys: ['icp_number', 'police_icp_number'],
  },
]



export const GENERAL_CONFIG_KEYS = GENERAL_CONFIG_SECTIONS.flatMap((s) => s.keys)

export const BASIC_CONFIG_TABS: BasicConfigTabDef[] = [

  {

    name: 'general',

    label: '常规配置',

    icon: 'general',

    path: '/admin/hub/system/basic/general',

    keys: GENERAL_CONFIG_KEYS,

    sections: GENERAL_CONFIG_SECTIONS,

  },

  {
    name: 'upload',
    label: '上传配置',
    icon: 'upload',
    path: '/admin/hub/system/basic/upload',
  },

  {

    name: 'cache',

    label: '缓存配置',

    icon: 'cache',

    path: '/admin/hub/system/basic/cache',

    keys: ['cache_provider', 'redis_url', 'cache_default_ttl_seconds'],

  },

  {

    name: 'security',

    label: '安全配置',

    icon: 'security',

    path: '/admin/hub/system/basic/security',

    keys: ['access_token_expire_minutes', 'refresh_token_expire_days', 'login_fail_lock_count', 'admin_session_idle_minutes'],

  },

  {

    name: 'auth',

    label: '登录注册',

    icon: 'security',

    path: '/admin/hub/system/basic/auth',

    sections: [
      {
        title: '登录方式',
        keys: [
          'auth_login_phone_enabled',
          'auth_login_phone_sms_enabled',
          'auth_login_email_enabled',
          'auth_login_email_sms_enabled',
        ],
      },
      {
        title: '注册方式',
        keys: ['auth_register_phone_enabled', 'auth_register_email_enabled', 'auth_invite_code_enabled'],
      },
      {
        title: '账号绑定策略',
        keys: ['auth_require_phone_bind', 'auth_require_email_bind'],
      },
      {
        title: '邮箱验证码',
        keys: ['email_code_expire_seconds', 'email_code_rate_limit_seconds'],
      },
    ],

    keys: [
      'auth_login_phone_enabled',
      'auth_login_phone_sms_enabled',
      'auth_login_email_enabled',
      'auth_login_email_sms_enabled',
      'auth_register_phone_enabled',
      'auth_register_email_enabled',
      'auth_invite_code_enabled',
      'auth_require_phone_bind',
      'auth_require_email_bind',
      'email_code_expire_seconds',
      'email_code_rate_limit_seconds',
    ],

  },

  {

    name: 'version',

    label: '版本配置',

    icon: 'version',

    path: '/admin/hub/system/basic/version',

    keys: ['app_version', 'update_message'],

    sections: [
      {
        title: '站点版本',
        description: '社区版只有电脑站点，这里填写当前版本号和更新说明，不包含手机应用商店。',
        keys: ['app_version', 'update_message'],
      },
    ],

  },

  {

    name: 'feature',

    label: '功能开关',

    icon: 'feature',

    path: '/admin/hub/system/basic/feature',

    keys: ['ai_mock_enabled'],
    sections: [
      {
        title: '法律咨询',
        description: '关闭后，咨询使用「服务集成 → 对话模型」里填写的接口。开启后只返回示例回答，不调用模型。保存即生效。',
        keys: ['ai_mock_enabled'],
      },
    ],

  },

  {

    name: 'billing',

    label: '咨询额度',

    icon: 'billing',

    path: '/admin/hub/system/basic/billing',

    keys: ['free_daily_chat_quota'],

    sections: [
      {
        title: '每日咨询次数',
        description: '社区版按自然日计数，不使用积分、余额或会员套餐。次数用完后，用户需等到次日。',
        keys: ['free_daily_chat_quota'],
      },
    ],

  },

]


