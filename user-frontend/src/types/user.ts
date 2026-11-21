export interface UserInfo {
  id: number
  openid?: string | null
  unionid?: string | null
  phone?: string | null
  email?: string | null
  nickname?: string | null
  avatar?: string | null
  platform: string
  status: string
  is_admin?: boolean
  admin_role?: string | null
  binding_required_phone?: boolean
  binding_required_email?: boolean
  created_at: string
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  user: UserInfo
}

export interface QrcodeCreateResponse {
  ticket: string
  expire_seconds: number
  qrcode_url: string
}

export interface QrcodeStatusResponse {
  status: 'pending' | 'scanned' | 'confirmed' | 'expired'
  access_token?: string
  refresh_token?: string
  user?: UserInfo
}
