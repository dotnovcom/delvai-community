export interface SettingSelectOption {
  label: string
  value: string
}

export interface SettingFieldMeta {
  hint?: string
  placeholder?: string
  options?: SettingSelectOption[]
}

const ENCRYPT_MODE_OPTIONS: SettingSelectOption[] = [
  { label: '安全模式（推荐）', value: 'safe' },
  { label: '兼容模式', value: 'compatible' },
  { label: '明文模式', value: 'plain' },
]

export const SETTING_FIELD_META: Record<string, SettingFieldMeta> = {
  wechat_mp_enabled: {
    hint: '关闭后小程序 code2session 登录不可用。',
  },
  wechat_mp_app_id: {
    hint: '微信公众平台 → 开发管理 → 开发设置。小程序唯一标识，与开发者工具中的 AppID 必须一致。',
    placeholder: 'wx 开头',
  },
  wechat_mp_app_secret: {
    hint: '开发设置中生成，仅服务端 jscode2session 使用，不要写入小程序前端代码。',
  },
  wechat_mp_original_id: {
    hint: '设置 → 基本设置中的原始 ID，格式为 gh_xxxxxxxx。',
    placeholder: 'gh_',
  },
  wechat_mp_env_version: {
    hint: 'URL Link / 加密 URL Scheme / 打开半屏小程序时的默认版本。',
    options: [
      { label: '正式版 release', value: 'release' },
      { label: '体验版 trial', value: 'trial' },
      { label: '开发版 develop', value: 'develop' },
    ],
  },
  wechat_mp_request_legal_domain: {
    hint: '开发设置 → 服务器域名。仅 https，不能是 IP 或 localhost，须 ICP 备案；每月可改 5 次，最多 20 个。只填域名，不要带路径。',
    placeholder: 'https://api.example.com',
  },
  wechat_mp_socket_legal_domain: {
    hint: '仅支持 wss。规则同 request 合法域名。',
    placeholder: 'wss://api.example.com',
  },
  wechat_mp_upload_legal_domain: {
    hint: 'uploadFile 合法域名，仅 https，须 ICP 备案。',
    placeholder: 'https://upload.example.com',
  },
  wechat_mp_download_legal_domain: {
    hint: 'downloadFile 合法域名，仅 https，须 ICP 备案。',
    placeholder: 'https://cdn.example.com',
  },
  wechat_mp_udp_legal_domain: {
    hint: '开发设置中的 UDP 合法域名，按需填写。',
  },
  wechat_mp_tcp_legal_domain: {
    hint: '开发设置中的 TCP 合法域名，按需填写。',
  },
  wechat_mp_business_domain: {
    hint: 'web-view 业务域名，须 ICP 备案；需下载校验文件放到域名根目录。每月最多改 5 次，最多 20 个。',
    placeholder: 'https://www.example.com',
  },
  wechat_mp_msg_push_url: {
    hint: '开发设置 → 消息推送。须以 http:// 或 https:// 开头，常用 80/443 端口，用于接收小程序消息与事件。',
    placeholder: 'https://your-domain.com/api/v1/wechat/mp/callback',
  },
  wechat_mp_msg_token: {
    hint: '由开发者自行填写，须与公众平台消息推送 Token 一致，用于签名校验。',
  },
  wechat_mp_msg_encoding_aes_key: {
    hint: '43 位字符。安全模式必填，用于消息体加解密。',
  },
  wechat_mp_msg_encrypt_mode: {
    hint: '官方推荐安全模式。明文不加密；兼容同时支持明文与密文；安全仅密文。',
    options: ENCRYPT_MODE_OPTIONS,
  },
  wechat_mp_msg_data_format: {
    hint: '小程序消息推送推荐 JSON，也可选 XML。',
    options: [
      { label: 'JSON（推荐）', value: 'JSON' },
      { label: 'XML', value: 'XML' },
    ],
  },
  wechat_mp_subscribe_template_ids: {
    hint: '功能 → 订阅消息中的模板 ID，每行一个，供服务端下发订阅消息。',
  },
  wechat_official_enabled: {
    hint: '关闭后公众号网页授权与 PC 扫码登录不可用。',
  },
  wechat_official_app_id: {
    hint: '公众平台 → 设置与开发 → 账号设置 / 基本配置。网页授权与扫码登录使用此 AppID。',
    placeholder: 'wx 开头',
  },
  wechat_official_app_secret: {
    hint: '基本配置中重置，仅服务端网页授权换票使用，请妥善保管。',
  },
  wechat_official_original_id: {
    hint: '账号设置中的原始 ID，格式为 gh_xxxxxxxx。',
    placeholder: 'gh_',
  },
  wechat_official_type: {
    hint: '仅认证服务号可使用网页授权（snsapi_userinfo）、自定义菜单等能力；订阅号能力受限。',
    options: [
      { label: '服务号（网页授权 / 扫码登录）', value: 'service' },
      { label: '订阅号', value: 'subscription' },
    ],
  },
  wechat_official_qr_url: {
    hint: '用于前台展示的公众号关注二维码。可在账号设置中下载。',
  },
  wechat_official_server_url: {
    hint: '基本配置 → 服务器配置。须公网可访问，用于接收公众号消息与事件推送。',
    placeholder: 'https://your-domain.com/api/v1/wechat/official/callback',
  },
  wechat_official_token: {
    hint: '与公众平台服务器配置中的 Token 保持一致，用于签名验证。',
  },
  wechat_official_encoding_aes_key: {
    hint: '43 位字符。官方推荐安全模式，此项必填。',
  },
  wechat_official_encrypt_mode: {
    hint: '官方推荐安全模式。公众号消息体为 XML。',
    options: ENCRYPT_MODE_OPTIONS,
  },
  wechat_official_oauth_domain: {
    hint: '功能设置 → 网页授权域名。只填域名，不要加 http:// 或路径。须覆盖扫码登录回调域名。',
    placeholder: 'your-domain.com',
  },
  wechat_official_jsapi_domains: {
    hint: '功能设置 → JS 接口安全域名。每行一个，不含协议与路径。',
    placeholder: 'your-domain.com',
  },
  wechat_official_ip_whitelist: {
    hint: '基本配置 → IP 白名单。填写调用微信接口的服务器出口公网 IP，每行一个。',
    placeholder: '1.2.3.4',
  },
  pc_enabled: {
    hint: '关闭后隐藏 PC 端配置页。站点地址与 SEO 仍保留。',
  },
  pc_site_url: {
    hint: 'PC 站点完整地址，含协议、不含末尾斜杠。用于扫码登录回调、开放平台跳转与 canonical。',
    placeholder: 'https://www.example.com',
  },
  pc_seo_title: {
    hint: '写入 <title>、og:title。留空则使用基础配置中的 SEO 标题。',
  },
  pc_seo_keywords: {
    hint: '英文逗号分隔。留空则使用基础配置关键词。',
    placeholder: '法律AI,法规检索,合同审查',
  },
  pc_seo_description: {
    hint: '建议 70–160 字。写入 meta description 与 og:description。留空则使用基础配置描述。',
  },
  pc_og_image: {
    hint: '社交分享预览图，建议 1200×630。留空则使用基础配置分享图。',
  },
  pc_robots: {
    hint: '搜索引擎抓取策略。生产站通常使用 index, follow。',
    options: [
      { label: 'index, follow（允许收录）', value: 'index, follow' },
      { label: 'noindex, follow', value: 'noindex, follow' },
      { label: 'noindex, nofollow（禁止收录）', value: 'noindex, nofollow' },
    ],
  },
  pc_baidu_site_verification: {
    hint: '百度搜索资源平台「站点验证」提供的 content 值。',
  },
  pc_google_site_verification: {
    hint: 'Google Search Console 站点验证码。',
  },
  h5_enabled: {
    hint: '关闭后隐藏 H5 端配置页。邀请链接等仍可读取已保存地址。',
  },
  h5_site_url: {
    hint: 'H5 站点完整地址，含协议、不含末尾斜杠。用于移动网页与分享回跳。',
    placeholder: 'https://m.example.com',
  },
  h5_seo_title: {
    hint: 'H5 页面标题。留空则沿用全站 SEO 标题。',
  },
  h5_seo_keywords: {
    hint: 'H5 关键词，英文逗号分隔。留空则沿用全站关键词。',
  },
  h5_seo_description: {
    hint: 'H5 页面描述。留空则沿用全站描述。',
  },
  h5_share_title: {
    hint: '微信 / 浏览器分享标题。留空则使用 H5 SEO 标题。',
  },
  h5_share_desc: {
    hint: '微信 / 浏览器分享摘要。留空则使用 H5 SEO 描述。',
  },
  h5_og_image: {
    hint: 'H5 分享图，建议正方形 300×300 以上。',
  },
  h5_theme_color: {
    hint: '写入 theme-color，影响移动浏览器地址栏颜色。',
    placeholder: '#10b981',
  },
  h5_apple_touch_icon: {
    hint: 'iOS「添加到主屏幕」图标，建议 180×180 PNG。',
  },
  h5_pwa_name: {
    hint: '添加到主屏幕时显示的名称。留空则使用平台名称。',
  },
  h5_robots: {
    hint: 'H5 搜索引擎抓取策略。',
    options: [
      { label: 'index, follow（允许收录）', value: 'index, follow' },
      { label: 'noindex, follow', value: 'noindex, follow' },
      { label: 'noindex, nofollow（禁止收录）', value: 'noindex, nofollow' },
    ],
  },
  douyin_mp_enabled: {
    hint: '关闭后隐藏抖音小程序配置页，code2session 登录不可用。',
  },
  douyin_mp_app_name: {
    hint: '与抖音开放平台小程序名称保持一致。',
  },
  douyin_mp_original_id: {
    hint: '开放平台账号信息中的原始 ID。',
  },
  douyin_mp_server_domain: {
    hint: '开发配置 → 服务器域名 → request。只填域名，不要加 https:// 或路径。须备案，不能是 IP。',
    placeholder: 'api.example.com',
  },
  douyin_mp_upload_legal_domain: {
    hint: 'uploadFile 合法域名，每行一个，不含协议。',
  },
  douyin_mp_download_legal_domain: {
    hint: 'downloadFile 合法域名，每行一个，不含协议。',
  },
  douyin_mp_socket_legal_domain: {
    hint: 'socket 合法域名，每行一个，不含协议。',
  },
  douyin_mp_webview_domain: {
    hint: 'webview 业务域名，须完成备案校验。',
  },
  douyin_mp_msg_url: {
    hint: '消息与推送服务器地址，须公网 HTTPS 可访问。',
    placeholder: 'https://your-domain.com/api/v1/douyin/mp/callback',
  },
  douyin_mp_msg_token: {
    hint: '与开放平台填写的 Token 保持一致。',
  },
  android_enabled: {
    hint: '关闭后隐藏安卓端配置页。',
  },
  android_app_name: {
    hint: '应用市场上显示的应用名称。',
  },
  android_package_name: {
    hint: 'applicationId，须与签名及市场上架包名完全一致。',
    placeholder: 'com.example.app',
  },
  android_min_sdk: {
    hint: 'minSdkVersion，例如 21 表示 Android 5.0。',
  },
  android_min_version: {
    hint: '低于此版本将提示更新。',
    placeholder: '1.0.0',
  },
  android_latest_version: {
    hint: '当前线上最新版本号。',
  },
  android_version_code: {
    hint: '整数，须单调递增。',
  },
  android_force_update: {
    hint: '开启后低于最低版本必须更新才能继续使用。',
  },
  android_update_message: {
    hint: '更新弹窗文案。',
  },
  download_url_android: {
    hint: 'APK 或应用商店下载地址。',
    placeholder: 'https://',
  },
  android_sha256_cert: {
    hint: '应用签名证书 SHA-256，用于 App Links / 开放平台校验。',
  },
  android_applink_host: {
    hint: 'Android App Links 域名，不含协议与路径。',
    placeholder: 'www.example.com',
  },
  ios_enabled: {
    hint: '关闭后隐藏 iOS 端配置页。',
  },
  ios_app_name: {
    hint: 'App Store 显示名称。',
  },
  ios_bundle_id: {
    hint: '须与 Xcode / App Store Connect 完全一致。',
    placeholder: 'com.example.app',
  },
  ios_app_store_id: {
    hint: 'App Store Connect 中的数字 ID，用于生成商店链接。',
  },
  ios_team_id: {
    hint: 'Apple Developer Team ID，Universal Links  entitlements 需要。',
  },
  ios_min_version: {
    hint: '低于此版本将提示更新。',
  },
  ios_latest_version: {
    hint: '当前 App Store 最新版本号。',
  },
  ios_build_number: {
    hint: 'CFBundleVersion，须递增。',
  },
  ios_force_update: {
    hint: '开启后低于最低版本必须更新才能继续使用。',
  },
  ios_update_message: {
    hint: '更新弹窗文案。',
  },
  download_url_ios: {
    hint: 'App Store 链接，例如 https://apps.apple.com/app/idxxxxxxxx。',
    placeholder: 'https://apps.apple.com/app/id',
  },
  ios_universal_link: {
    hint: 'Associated Domains 中的 applinks 域名，不含协议。',
    placeholder: 'www.example.com',
  },
}

export function getSettingFieldMeta(key: string): SettingFieldMeta {
  return SETTING_FIELD_META[key] ?? {}
}
