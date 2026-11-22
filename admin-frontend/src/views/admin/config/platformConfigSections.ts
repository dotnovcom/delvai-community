export interface PlatformConfigSection {
  title: string
  description?: string
  keys: string[]
}

/** 社区版只有电脑端。 */
export const PLATFORM_CONFIG_SECTIONS: PlatformConfigSection[] = [
  {
    title: 'PC 端',
    description: '社区版只提供电脑站点。下面的地址和 SEO 会用于用户端页面标题、分享信息和站点跳转。',
    keys: [
      'pc_enabled',
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
    ],
  },
]

export const PLATFORM_CONFIG_KEYS = [...new Set(PLATFORM_CONFIG_SECTIONS.flatMap((s) => s.keys))]
