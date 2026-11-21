import type { RouteLocationNormalized } from 'vue-router'
import type { NewsDetail, PublicConfig } from '../api/cms'
import { WORKSPACE_META, resolveWorkspaceKey } from '../constants/workspaceNav'
import { enterpriseModuleLabel } from '../constants/enterpriseModules'

const SEO_ATTR = 'data-ft-seo'

export const DEFAULT_SITE_TITLE = ''
export const DEFAULT_SITE_DESCRIPTION = ''
export const DEFAULT_SITE_KEYWORDS = '法律AI,法规检索,合同审查,文书生成'

export interface SeoPayload {
  title?: string
  description?: string
  keywords?: string
  image?: string
  shareTitle?: string
  shareDescription?: string
  url?: string
  siteName?: string
  type?: 'website' | 'article'
  robots?: string
  jsonLd?: Record<string, unknown> | Record<string, unknown>[]
  baiduSiteVerification?: string
  googleSiteVerification?: string
}

function upsertMeta(attr: 'name' | 'property', key: string, content: string) {
  const selector = `meta[${attr}="${key}"]`
  let el = document.head.querySelector<HTMLMetaElement>(selector)
  if (!el) {
    el = document.createElement('meta')
    el.setAttribute(attr, key)
    document.head.appendChild(el)
  }
  el.setAttribute(SEO_ATTR, '1')
  el.setAttribute('content', content)
}

function upsertLink(rel: string, href: string) {
  const selector = `link[rel="${rel}"]`
  let el = document.head.querySelector<HTMLLinkElement>(selector)
  if (!el) {
    el = document.createElement('link')
    el.setAttribute('rel', rel)
    document.head.appendChild(el)
  }
  el.setAttribute(SEO_ATTR, '1')
  el.setAttribute('href', href)
}

function removeJsonLd(id: string) {
  document.getElementById(id)?.remove()
}

function setJsonLd(id: string, data: Record<string, unknown> | Record<string, unknown>[]) {
  removeJsonLd(id)
  const script = document.createElement('script')
  script.id = id
  script.type = 'application/ld+json'
  script.setAttribute(SEO_ATTR, '1')
  script.textContent = JSON.stringify(data)
  document.head.appendChild(script)
}

/** 写入 document 与常见 SEO / Open Graph / Twitter 标签 */
export function applySeo(payload: SeoPayload) {
  const title = payload.title?.trim()
  if (title) document.title = title

  const description = payload.description?.trim()
  const keywords = payload.keywords?.trim()
  const image = payload.image?.trim()
  const url = payload.url?.trim()
  const type = payload.type || 'website'
  const robots = payload.robots?.trim() || 'index, follow'

  upsertMeta('name', 'description', description || DEFAULT_SITE_DESCRIPTION)
  upsertMeta('name', 'keywords', keywords || DEFAULT_SITE_KEYWORDS)
  upsertMeta('name', 'robots', robots)

  const shareTitle = payload.shareTitle?.trim() || title || DEFAULT_SITE_TITLE
  const shareDescription = payload.shareDescription?.trim() || description || DEFAULT_SITE_DESCRIPTION
  upsertMeta('property', 'og:title', shareTitle)
  upsertMeta('property', 'og:description', shareDescription)
  upsertMeta('property', 'og:type', type)
  upsertMeta('property', 'og:locale', 'zh_CN')
  if (payload.siteName?.trim()) {
    upsertMeta('property', 'og:site_name', payload.siteName.trim())
  }

  upsertMeta('name', 'twitter:card', image ? 'summary_large_image' : 'summary')
  upsertMeta('name', 'twitter:title', shareTitle)
  upsertMeta('name', 'twitter:description', shareDescription)

  if (image) {
    upsertMeta('property', 'og:image', image)
    upsertMeta('name', 'twitter:image', image)
  }

  if (url) {
    upsertLink('canonical', url)
    upsertMeta('property', 'og:url', url)
  }

  if (payload.jsonLd) {
    setJsonLd('ft-json-ld', payload.jsonLd)
  } else {
    removeJsonLd('ft-json-ld')
  }

  const baidu = payload.baiduSiteVerification?.trim()
  const google = payload.googleSiteVerification?.trim()
  if (baidu) upsertMeta('name', 'baidu-site-verification', baidu)
  if (google) upsertMeta('name', 'google-site-verification', google)
}

/** 生产 HTTPS 页避免 Mixed Content（如后台 pc_site_url 配成 http） */
export function ensureHttpsAssetUrl(url: string): string {
  const u = url.trim()
  if (!u.startsWith('http://')) return u
  if (/localhost|127\.0\.0\.1/i.test(u)) return u
  return `https://${u.slice(7)}`
}

export function applyFavicon(url?: string) {
  if (!url?.trim()) return
  upsertLink('icon', ensureHttpsAssetUrl(url))
}

export function buildPageUrl(path: string, pcSiteUrl?: string): string {
  const normalized = path.startsWith('/') ? path : `/${path}`
  if (pcSiteUrl?.trim()) {
    const base = pcSiteUrl.trim().replace(/\/$/, '')
    return `${base}${normalized}`
  }
  if (typeof window !== 'undefined') {
    return `${window.location.origin}${normalized}`
  }
  return normalized
}

function resolvePageTitle(to: RouteLocationNormalized, cfg: PublicConfig): string {
  if (to.path.startsWith('/chat/')) {
    if (to.params.module) {
      return `${enterpriseModuleLabel(String(to.params.module))} - 企业工作台`
    }
    const key = resolveWorkspaceKey(to.path)
    if (key === 'ai') {
      return (cfg.ai_nav_label || '').trim()
    }
    return WORKSPACE_META[key]?.title || ''
  }
  return String(to.meta.title || '')
}

function siteBrand(cfg: PublicConfig): string {
  return cfg.platform_name?.trim() || ''
}

function pcSeoTitle(cfg: PublicConfig): string {
  return cfg.pc_seo_title?.trim() || cfg.site_title?.trim() || DEFAULT_SITE_TITLE
}

function pcSeoKeywords(cfg: PublicConfig): string {
  return cfg.pc_seo_keywords?.trim() || cfg.site_keywords?.trim() || DEFAULT_SITE_KEYWORDS
}

function pcSeoDescription(cfg: PublicConfig): string {
  return cfg.pc_seo_description?.trim() || cfg.site_description?.trim() || DEFAULT_SITE_DESCRIPTION
}

function pcSeoImage(cfg: PublicConfig): string {
  return cfg.pc_og_image?.trim() || cfg.og_image?.trim() || ''
}

function pcShareTitle(cfg: PublicConfig): string {
  return cfg.pc_share_title?.trim() || pcSeoTitle(cfg)
}

function pcShareDescription(cfg: PublicConfig): string {
  return cfg.pc_share_desc?.trim() || pcSeoDescription(cfg)
}

function pcRobots(cfg: PublicConfig, fallback = 'index, follow'): string {
  return cfg.pc_robots?.trim() || fallback
}

function buildDocumentTitle(pageTitle: string, cfg: PublicConfig, to: RouteLocationNormalized): string {
  if (to.path === '/') {
    return pcSeoTitle(cfg)
  }
  if (!pageTitle) {
    return pcSeoTitle(cfg)
  }
  const brand = siteBrand(cfg)
  return brand ? `${pageTitle} | ${brand}` : pageTitle
}

function buildWebSiteJsonLd(cfg: PublicConfig, pageUrl: string) {
  return {
    '@context': 'https://schema.org',
    '@type': 'WebSite',
    name: siteBrand(cfg),
    description: pcSeoDescription(cfg),
    url: pageUrl,
    inLanguage: 'zh-CN',
  }
}

export function buildArticleSeo(
  article: NewsDetail,
  cfg: PublicConfig,
  fullPath: string,
): SeoPayload {
  const brand = siteBrand(cfg)
  const pageUrl = buildPageUrl(fullPath, cfg.pc_site_url)
  const description =
    article.summary?.trim() ||
    stripHtml(article.content).slice(0, 160) ||
    cfg.site_description?.trim() ||
    pcSeoDescription(cfg) ||
    DEFAULT_SITE_DESCRIPTION
  const image = article.cover_url?.trim() || pcSeoImage(cfg)

  return {
    title: brand ? `${article.title} | ${brand}` : article.title,
    description,
    keywords: pcSeoKeywords(cfg),
    image,
    url: pageUrl,
    siteName: brand,
    type: 'article',
    jsonLd: {
      '@context': 'https://schema.org',
      '@type': 'NewsArticle',
      headline: article.title,
      description,
      image: image ? [image] : undefined,
      datePublished: article.published_at || undefined,
      url: pageUrl,
      publisher: {
        '@type': 'Organization',
        name: brand,
      },
    },
  }
}

function pcVerification(cfg: PublicConfig) {
  return {
    baiduSiteVerification: cfg.pc_baidu_site_verification?.trim(),
    googleSiteVerification: cfg.pc_google_site_verification?.trim(),
  }
}

export function resolveRouteSeo(
  to: RouteLocationNormalized,
  cfg: PublicConfig,
): SeoPayload {
  const pageUrl = buildPageUrl(to.fullPath, cfg.pc_site_url)
  const description = pcSeoDescription(cfg)
  const keywords = pcSeoKeywords(cfg)
  const image = pcSeoImage(cfg)
  const brand = siteBrand(cfg)

  const siteName = brand

  if (to.path.startsWith('/admin')) {
    return {
      title: `${to.meta.title || '运营后台'} | ${brand}`,
      description,
      keywords,
      url: pageUrl,
      siteName,
      robots: 'noindex, nofollow',
    }
  }

  if (to.meta.guest) {
    const pageTitle = resolvePageTitle(to, cfg)
    return {
      title: buildDocumentTitle(pageTitle, cfg, to),
      description,
      keywords,
      image,
      url: pageUrl,
      siteName,
      robots: 'noindex, follow',
    }
  }

  const pageTitle = resolvePageTitle(to, cfg)

  if (to.path === '/') {
    return {
      title: pcSeoTitle(cfg),
      description,
      shareTitle: pcShareTitle(cfg),
      shareDescription: pcShareDescription(cfg),
      keywords,
      image,
      url: pageUrl,
      siteName,
      type: 'website',
      robots: pcRobots(cfg),
      jsonLd: buildWebSiteJsonLd(cfg, pageUrl),
      ...pcVerification(cfg),
    }
  }

  if (to.name === 'NewsDetail') {
    return {
      title: buildDocumentTitle(pageTitle || '资讯详情', cfg, to),
      description,
      keywords,
      image,
      url: pageUrl,
      siteName,
      type: 'article',
      robots: pcRobots(cfg),
      ...pcVerification(cfg),
    }
  }

  return {
    title: buildDocumentTitle(pageTitle, cfg, to),
    description,
    keywords,
    image,
    url: pageUrl,
    siteName,
    type: 'website',
    robots: pcRobots(cfg),
    ...pcVerification(cfg),
  }
}

function stripHtml(html: string): string {
  const text = html.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim()
  return text
}
