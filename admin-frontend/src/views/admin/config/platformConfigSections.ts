export interface PlatformConfigSection {
  title: string
  description?: string
  keys: string[]
  /** 有值时：对应开关为 true 才显示该选项卡 */
  enableKey?: string
}

export const PLATFORM_ENABLE_KEYS = [
  'pc_enabled',
  'h5_enabled',
  'wechat_mp_enabled',
  'wechat_official_enabled',
  'douyin_mp_enabled',
  'android_enabled',
  'ios_enabled',
] as const

export const PLATFORM_CONFIG_SECTIONS: PlatformConfigSection[] = [
  {
    title: '端能力',
    description:
      '打开某一端后，右侧会出现对应配置页。关闭后该端配置页隐藏，已填写内容仍保留，保存后即时生效。',
    keys: [...PLATFORM_ENABLE_KEYS],
  },
  {
    title: 'PC 端',
    enableKey: 'pc_enabled',
    description:
      '对应电脑站点。手机浏览器打开此域名时，可按下方开关跳到 H5 站点地址，域名取自本页配置，不在代码里写死。',
    keys: [
      'pc_site_url',
      'pc_seo_title',
      'pc_seo_keywords',
      'pc_seo_description',
      'pc_share_title',
      'pc_share_desc',
      'pc_og_image',
      'pc_robots',
      'pc_baidu_site_verification',
      'pc_google_site_verification',
      'pc_redirect_mobile_enabled',
    ],
  },
  {
    title: 'H5 端',
    enableKey: 'h5_enabled',
    description:
      'H5 站点地址用于移动网页、邀请链接与分享回跳。电脑浏览器打开此域名时，可按下方开关跳到 PC 站点地址。',
    keys: [
      'h5_site_url',
      'h5_seo_title',
      'h5_seo_keywords',
      'h5_seo_description',
      'h5_share_title',
      'h5_share_desc',
      'h5_og_image',
      'h5_theme_color',
      'h5_apple_touch_icon',
      'h5_pwa_name',
      'h5_robots',
      'h5_redirect_desktop_enabled',
    ],
  },
  {
    title: '微信小程序',
    enableKey: 'wechat_mp_enabled',
    description:
      '对应微信公众平台「开发 → 开发管理 → 开发设置」。服务器域名须 HTTPS/WSS、已 ICP 备案，不能填写 IP 或 localhost。微信支付请到「服务集成」配置。',
    keys: [
      'wechat_mp_app_id',
      'wechat_mp_app_secret',
      'wechat_mp_original_id',
      'wechat_mp_env_version',
      'wechat_mp_request_legal_domain',
      'wechat_mp_socket_legal_domain',
      'wechat_mp_upload_legal_domain',
      'wechat_mp_download_legal_domain',
      'wechat_mp_udp_legal_domain',
      'wechat_mp_tcp_legal_domain',
      'wechat_mp_business_domain',
      'wechat_mp_msg_push_url',
      'wechat_mp_msg_token',
      'wechat_mp_msg_encoding_aes_key',
      'wechat_mp_msg_encrypt_mode',
      'wechat_mp_msg_data_format',
      'wechat_mp_subscribe_template_ids',
    ],
  },
  {
    title: '微信公众号',
    enableKey: 'wechat_official_enabled',
    description:
      '对应微信公众平台「设置与开发 → 账号设置 / 基本配置 / 功能设置」。网页授权与 PC 扫码登录需认证服务号；回调路径为 /api/v1/auth/wechat-oauth/qr-callback。微信支付请到「服务集成」配置。',
    keys: [
      'wechat_official_app_id',
      'wechat_official_app_secret',
      'wechat_official_original_id',
      'wechat_official_type',
      'wechat_official_qr_url',
      'wechat_official_server_url',
      'wechat_official_token',
      'wechat_official_encoding_aes_key',
      'wechat_official_encrypt_mode',
      'wechat_official_oauth_domain',
      'wechat_official_jsapi_domains',
      'wechat_official_ip_whitelist',
    ],
  },
  {
    title: '抖音小程序',
    enableKey: 'douyin_mp_enabled',
    description:
      '对应抖音开放平台「开发 → 开发配置」。服务器域名须 HTTPS，不能使用 IP 或 localhost，须完成备案。抖音支付请到「服务集成」配置。',
    keys: [
      'douyin_mp_app_id',
      'douyin_mp_app_secret',
      'douyin_mp_app_name',
      'douyin_mp_original_id',
      'douyin_mp_sandbox_enabled',
      'douyin_mp_server_domain',
      'douyin_mp_upload_legal_domain',
      'douyin_mp_download_legal_domain',
      'douyin_mp_socket_legal_domain',
      'douyin_mp_webview_domain',
      'douyin_mp_msg_url',
      'douyin_mp_msg_token',
      'auth_login_douyin_enabled',
    ],
  },
  {
    title: '安卓端',
    enableKey: 'android_enabled',
    description:
      '包名须与应用市场上架及 Android App Links 一致。下载地址也可在「基础配置 → 版本」维护。',
    keys: [
      'android_app_name',
      'android_package_name',
      'android_min_sdk',
      'android_min_version',
      'android_latest_version',
      'android_version_code',
      'android_force_update',
      'android_update_message',
      'download_url_android',
      'android_sha256_cert',
      'android_applink_host',
    ],
  },
  {
    title: 'iOS 端',
    enableKey: 'ios_enabled',
    description:
      'Bundle ID、Team ID 须与 Apple Developer / App Store Connect 一致。下载地址一般为 App Store 链接。',
    keys: [
      'ios_app_name',
      'ios_bundle_id',
      'ios_app_store_id',
      'ios_team_id',
      'ios_min_version',
      'ios_latest_version',
      'ios_build_number',
      'ios_force_update',
      'ios_update_message',
      'download_url_ios',
      'ios_universal_link',
    ],
  },
]

export const PLATFORM_CONFIG_KEYS = [...new Set(PLATFORM_CONFIG_SECTIONS.flatMap((s) => s.keys))]
