import type { AdminIconName } from '../../../components/admin/adminIcons'

export interface SettingsFieldDef {
  key: string
  label?: string
  type?: 'text' | 'secret' | 'textarea' | 'select'
  long?: boolean
  options?: { label: string; value: string }[]
  placeholder?: string
  hint?: string
}

export interface SettingsChannelDef {
  id: string
  name: string
  description: string
  icon: AdminIconName
  enabledKey?: string
  fields: SettingsFieldDef[]
}

export const EMAIL_CHANNELS: SettingsChannelDef[] = [
  {
    id: 'smtp',
    name: 'SMTP 邮件',
    description: '注册、登录、找回密码和绑定邮箱的验证码都从这里发出',
    icon: 'email',
    enabledKey: 'email_enabled',
    fields: [
      { key: 'smtp_host', label: 'SMTP 主机', placeholder: 'smtp.qq.com' },
      { key: 'smtp_port', label: '端口', placeholder: '465（SSL）或 587（STARTTLS）' },
      { key: 'smtp_user', label: '用户名', placeholder: '发信邮箱，如 name@qq.com' },
      { key: 'smtp_password', label: '密码 / 授权码', type: 'secret', placeholder: '留空则不修改' },
      {
        key: 'smtp_from',
        label: '发件人地址',
        placeholder: '需与用户名一致',
        hint: '端口 465 使用 SSL。QQ 邮箱主机 smtp.qq.com，密码填授权码。',
      },
      {
        key: 'smtp_use_tls',
        label: '启用 TLS',
        type: 'select',
        options: [
          { label: '开启', value: 'true' },
          { label: '关闭', value: 'false' },
        ],
      },
    ],
  },
]

export const SMS_CHANNELS: SettingsChannelDef[] = [
  {
    id: 'sms_global',
    name: '短信全局策略',
    description: '启用渠道、验证码有效期与发送频率',
    icon: 'settings',
    fields: [
      {
        key: 'sms_active_provider',
        label: '当前启用渠道',
        type: 'select',
        options: [
          { label: '阿里云短信', value: 'aliyun' },
          { label: '腾讯云短信', value: 'tencent' },
        ],
      },
      { key: 'sms_code_expire_seconds', label: '验证码有效期(秒)', placeholder: '300' },
      { key: 'sms_rate_limit_seconds', label: '发送间隔(秒)', placeholder: '60' },
    ],
  },
  {
    id: 'aliyun_sms',
    name: '阿里云短信',
    description: '登录、注册、找回密码和绑定手机使用的阿里云短信模板',
    icon: 'cloud',
    fields: [
      { key: 'aliyun_sms_access_key_id', label: 'AccessKeyId', type: 'secret', placeholder: '留空则不修改' },
      { key: 'aliyun_sms_access_key_secret', label: 'AccessKeySecret', type: 'secret', placeholder: '留空则不修改' },
      { key: 'aliyun_sms_sign_name', label: 'SignName', placeholder: '已审核签名' },
      { key: 'aliyun_sms_tpl_login', label: 'TemplateCode（登录）', placeholder: 'SMS_xxx' },
      { key: 'aliyun_sms_tpl_register', label: 'TemplateCode（注册）', placeholder: 'SMS_xxx' },
      { key: 'aliyun_sms_tpl_reset_password', label: 'TemplateCode（找回密码）', placeholder: 'SMS_xxx' },
      { key: 'aliyun_sms_tpl_bind_phone', label: 'TemplateCode（绑定手机）', placeholder: 'SMS_xxx' },
    ],
  },
  {
    id: 'tencent_sms',
    name: '腾讯云短信',
    description: '登录、注册、找回密码和绑定手机使用的腾讯云短信模板',
    icon: 'sms',
    fields: [
      { key: 'tencent_sms_secret_id', label: 'SecretId', type: 'secret', placeholder: '留空则不修改' },
      { key: 'tencent_sms_secret_key', label: 'SecretKey', type: 'secret', placeholder: '留空则不修改' },
      { key: 'tencent_sms_region', label: 'Region', placeholder: 'ap-guangzhou' },
      { key: 'tencent_sms_sdk_app_id', label: 'SmsSdkAppId', placeholder: '控制台应用管理' },
      { key: 'tencent_sms_sign_name', label: 'SignName', placeholder: '已审核签名' },
      {
        key: 'tencent_sms_template_param_count',
        label: 'TemplateParamSet 个数',
        type: 'select',
        options: [
          { label: '1（仅验证码）', value: '1' },
          { label: '2（验证码 + 有效分钟）', value: '2' },
        ],
      },
      { key: 'tencent_sms_tpl_login', label: 'TemplateId（登录）' },
      { key: 'tencent_sms_tpl_register', label: 'TemplateId（注册）' },
      { key: 'tencent_sms_tpl_reset_password', label: 'TemplateId（找回密码）' },
      { key: 'tencent_sms_tpl_bind_phone', label: 'TemplateId（绑定手机）' },
    ],
  },
]

export const STORAGE_CHANNELS: SettingsChannelDef[] = [
  {
    id: 'aliyun_oss',
    name: '阿里云 OSS',
    description: 'AccessKey、Endpoint、Bucket 与自定义域名',
    icon: 'cloud',
    fields: [
      { key: 'aliyun_oss_access_key_id', label: 'AccessKey ID', type: 'secret', placeholder: '留空则不修改' },
      { key: 'aliyun_oss_access_key_secret', label: 'AccessKey Secret', type: 'secret', placeholder: '留空则不修改' },
      { key: 'aliyun_oss_region', label: 'Region', placeholder: 'oss-cn-hangzhou' },
      { key: 'aliyun_oss_endpoint', label: 'Endpoint', placeholder: 'oss-cn-hangzhou.aliyuncs.com' },
      { key: 'aliyun_oss_bucket', label: 'Bucket' },
      { key: 'aliyun_oss_base_url', label: '自定义访问域名（可选）' },
    ],
  },
  {
    id: 'tencent_cos',
    name: '腾讯云 COS',
    description: 'SecretId、Region、Bucket 与自定义域名',
    icon: 'tencent',
    fields: [
      { key: 'tencent_cos_secret_id', label: 'SecretId', type: 'secret', placeholder: '留空则不修改' },
      { key: 'tencent_cos_secret_key', label: 'SecretKey', type: 'secret', placeholder: '留空则不修改' },
      { key: 'tencent_cos_region', label: 'Region', placeholder: 'ap-guangzhou' },
      { key: 'tencent_cos_bucket', label: 'Bucket' },
      { key: 'tencent_cos_base_url', label: '自定义访问域名（可选）' },
    ],
  },
  {
    id: 'qiniu_kodo',
    name: '七牛云 Kodo',
    description: 'AccessKey、空间名、存储区域与访问域名',
    icon: 'qiniu',
    fields: [
      { key: 'qiniu_access_key', label: 'AccessKey', type: 'secret', placeholder: '留空则不修改' },
      { key: 'qiniu_secret_key', label: 'SecretKey', type: 'secret', placeholder: '留空则不修改' },
      { key: 'qiniu_bucket', label: '空间 Bucket' },
      {
        key: 'qiniu_region',
        label: '存储区域',
        type: 'select',
        options: [
          { label: '华东 z0', value: 'z0' },
          { label: '华北 z1', value: 'z1' },
          { label: '华南 z2', value: 'z2' },
          { label: '北美 na0', value: 'na0' },
          { label: '东南亚 as0', value: 'as0' },
        ],
      },
      { key: 'qiniu_domain', label: '访问域名' },
    ],
  },
]

export const PAYMENT_CHANNELS: SettingsChannelDef[] = [
  {
    id: 'wechat_pay',
    name: '微信支付',
    description: '保存后端已读取的微信 AppID、商户号和证书。社区版没有会员下单页面。',
    icon: 'wechat',
    enabledKey: 'wechat_pay_enabled',
    fields: [
      { key: 'wechat_pay_app_id', label: '微信 AppID' },
      { key: 'wechat_mch_id', label: '微信商户号' },
      { key: 'wechat_api_v3_key', label: 'APIv3 密钥', type: 'secret', placeholder: '留空则不修改' },
      { key: 'wechat_cert_serial_no', label: '商户证书序列号' },
      { key: 'wechat_mch_private_key', label: '商户私钥(PEM)', type: 'secret', long: true, placeholder: '留空则不修改' },
      { key: 'wechat_pay_public_key_pem', label: '微信支付公钥(PEM)', type: 'textarea' },
      { key: 'wechat_pay_public_key_id', label: '微信支付公钥 ID' },
      { key: 'wechat_platform_cert_pem', label: '微信支付平台证书(PEM)', type: 'textarea' },
      { key: 'wechat_pay_notify_url', label: '支付回调 URL' },
    ],
  },
  {
    id: 'alipay',
    name: '支付宝',
    description: '保存后端已读取的支付宝 AppID 和密钥。社区版没有会员下单页面。',
    icon: 'alipay',
    enabledKey: 'alipay_enabled',
    fields: [
      { key: 'alipay_app_id', label: '支付宝 AppID' },
      { key: 'alipay_private_key', label: '应用私钥(RSA2)', type: 'secret', long: true, placeholder: '留空则不修改' },
      { key: 'alipay_public_key', label: '支付宝公钥', type: 'textarea' },
      { key: 'alipay_notify_url', label: '支付回调 URL' },
    ],
  },
]

export function allSettingsKeys(channels: SettingsChannelDef[]): string[] {
  const keys = new Set<string>()
  for (const channel of channels) {
    if (channel.enabledKey) keys.add(channel.enabledKey)
    for (const field of channel.fields) keys.add(field.key)
  }
  return [...keys]
}
