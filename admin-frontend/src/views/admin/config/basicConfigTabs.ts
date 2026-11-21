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
    title: '会员角标',
    keys: ['member_badge_vip_url', 'member_badge_svip_url', 'member_badge_enterprise_url'],
  },
  {
    title: 'SEO 优化',
    keys: ['site_keywords', 'site_description'],
  },
  {
    title: '联系信息',
    keys: ['support_phone', 'support_email', 'company_address', 'support_qr_url', 'wechat_official_qr_url'],
  },
  {
    title: '备案信息',
    keys: ['icp_number', 'police_icp_number'],
  },
]



export const GENERAL_CONFIG_KEYS = GENERAL_CONFIG_SECTIONS.flatMap((s) => s.keys)

export const BILLING_CONFIG_SECTIONS: { title: string; keys: string[] }[] = [
  {
    title: '积分与扣费',
    keys: [
      'points_display_name',
      'points_default_validity_days',
      'points_to_yuan_rate',
      'billing_consume_order',
    ],
  },
  {
    title: '退款扣回',
    keys: [
      'refund_clawback_enabled',
      'refund_clawback_prefer_balance',
      'refund_clawback_allow_negative_lot',
    ],
  },
  {
    title: '新人礼包',
    keys: ['register_gift_points'],
  },
  {
    title: '每日签到',
    keys: ['checkin_base_points', 'checkin_streak_bonus_per_day', 'checkin_max_streak_bonus_days'],
  },
  {
    title: '推荐计划',
    keys: [
      'referral_register_gift_points',
      'referral_first_recharge_points',
      'referral_first_vip_points',
      'referral_reward_delay_hours',
    ],
  },
  {
    title: '购会员赠分',
    keys: ['membership_default_bonus_points'],
  },
]

export const BILLING_CONFIG_KEYS = BILLING_CONFIG_SECTIONS.flatMap((s) => s.keys)

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
          'auth_login_wechat_enabled',
          'auth_login_douyin_enabled',
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
      'auth_login_wechat_enabled',
      'auth_login_douyin_enabled',
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

    keys: [

      'app_version', 'force_update', 'update_message',

      'download_url_android', 'download_url_ios',

    ],

  },

  {

    name: 'feature',

    label: '功能开关',

    icon: 'feature',

    path: '/admin/hub/system/basic/feature',

    keys: ['feature_voice_enabled', 'feature_video_enabled', 'feature_esign_enabled', 'ai_mock_enabled'],
    sections: [
      {
        title: '前台入口',
        keys: ['feature_voice_enabled', 'feature_video_enabled', 'feature_esign_enabled'],
      },
      {
        title: '开发模式',
        description: '关闭后，法律咨询立即使用服务集成里已配置的通义法睿或 DeepSeek。开启后只返回示例回答，不调用模型。保存即生效，无需重启。',
        keys: ['ai_mock_enabled'],
      },
    ],

  },

  {

    name: 'billing',

    label: '计费配置',

    icon: 'billing',

    path: '/admin/hub/system/basic/billing',

    keys: BILLING_CONFIG_KEYS,

    sections: BILLING_CONFIG_SECTIONS,

  },

  {
    name: 'poster',
    label: '邀请海报',
    icon: 'banner',
    path: '/admin/hub/system/basic/poster',
  },

]


