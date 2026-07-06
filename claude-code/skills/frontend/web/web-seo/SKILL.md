---
name: web-seo
pack: frontend:web
description: Web SEO 规范——每页唯一 title/description、OG/Twitter 卡、JSON-LD 结构化数据、canonical 去重、sitemap/robots、语义化标签，规避 SPA 客户端渲染导致的抓取空洞。
when_to_use: 新增可被搜索收录的页面、改动 <head> 元数据、或页面收录/富摘要异常时。
when_NOT_to_use: 登录后台/内网工具等 noindex 页面、纯 API。
---

# Skill: Web SEO

爬虫看的是首屏返回的 HTML。客户端才填的内容 = 爬虫眼里的空白页。

## 强制规则

1. **元数据在服务端生成** — Next.js 用 `generateMetadata`（server 端），每页唯一 `title`/`description`；禁止靠 `useEffect` 改 `document.title`
2. **canonical 去重** — 带 UTM/分页/排序参数的页面指向规范 URL，避免重复内容稀释权重
3. **结构化数据** — 商品/文章/面包屑用 JSON-LD（schema.org），字段须与页面可见内容一致（否则判作弊）
4. **语义化 HTML** — 一个 `<h1>`、正确的 `<nav>/<main>/<article>`、图片必带有意义 `alt`；标题层级不跳级
5. **可抓取** — 内容必须出现在 SSR/SSG 的初始 HTML；提供 `sitemap.xml` 与 `robots.txt`

## 代码

```tsx
// app/product/[id]/page.tsx —— server 端生成，含 OG + canonical
export async function generateMetadata({ params }): Promise<Metadata> {
  const p = await getProduct(params.id)
  return {
    title: `${p.name} | 商城`,
    description: p.summary.slice(0, 155),
    alternates: { canonical: `https://shop.com/product/${p.id}` },
    openGraph: { title: p.name, images: [p.cover], type: 'website' },
    twitter: { card: 'summary_large_image' },
  }
}
```

```tsx
// JSON-LD 结构化数据（值与页面可见内容一致）
<script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify({
  '@context': 'https://schema.org', '@type': 'Product',
  name: p.name, image: p.cover,
  offers: { '@type': 'Offer', price: p.price, priceCurrency: 'CNY' },
}) }} />
```

## SPA 的 SEO 陷阱
- 纯 CSR 应用初始 HTML 只有 `<div id="root">` — 依赖 JS 执行才有内容，抓取不稳定/延迟收录
- 客户端路由跳转不触发 `<head>` 更新 → 多页共用同一 title
- 修法：可收录页走 SSR/SSG（Next/Nuxt），或预渲染（prerender）关键路由

## 反模式
- ❌ `useEffect(() => { document.title = ... })` 设标题 — 首屏 HTML 里没有
- ❌ 全站同一个 `title`/`description` — 无法区分收录
- ❌ 无 canonical，`?utm=`、`?page=` 各算独立页 — 权重分散
- ❌ JSON-LD 价格/库存与页面不符 — 触发结构化数据处罚
- ❌ 用 `<div onClick>` 当链接 — 爬虫不跟随，用 `<a href>`
