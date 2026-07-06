---
name: web-rendering-strategy
pack: frontend:web
description: Next.js 渲染选型——按数据时效/个性化/SEO 选 SSG/ISR/SSR/CSR，数据尽量在 Server Component 拉，客户端只拉真正客户端专属数据。
when_to_use: 新增页面/路由、决定数据在哪一层获取、或页面首屏慢/SEO 缺失时。
when_NOT_to_use: 纯组件样式改动、无数据获取的静态展示。
---

# Skill: Web 渲染策略选型

在客户端拉本该服务端拉的数据 = 首屏白屏 + 瀑布请求 + SEO 丢失。先定渲染模式，再定取数边界。

## 强制规则

1. **按数据特性选模式** — 用下表判定，不要默认全 CSR
2. **默认 Server Component 取数** — App Router 里数据默认在 server 拉；只有依赖浏览器状态（登录态 token、地理定位、localStorage）才下沉客户端
3. **禁客户端瀑布** — 父组件 `useEffect` 拉完再渲子组件、子组件再 `useEffect` 拉，是串行瀑布；改为 server 端并行 `await Promise.all` 或用 `use()` 并行
4. **动态渲染要显式** — 用了 `cookies()`/`headers()`/`searchParams` 会强制转 dynamic，别在本可静态的页面里误用

## 选型判定

| 数据特性 | 模式 | Next.js 写法 |
|---|---|---|
| 构建期已知、极少变 | SSG | 默认（无 dynamic API） |
| 全局共享、可容忍 N 秒陈旧 | ISR | `export const revalidate = 60` |
| 每请求个性化 / 强实时 | SSR | `cookies()` / `fetch(..., {cache:'no-store'})` |
| 纯交互、无需 SEO、依赖浏览器态 | CSR | `'use client'` + client fetch |

## 代码

```tsx
// ✅ Server Component 直接 await，server 端并行取数，无客户端瀑布
export default async function Page({ params }: { params: { id: string } }) {
  const [product, reviews] = await Promise.all([
    getProduct(params.id),          // 命中 fetch 缓存 → ISR/SSG
    getReviews(params.id),
  ])
  return <ProductView product={product} reviews={reviews} />
}

// ISR：60s 后台再验证
export const revalidate = 60
```

```tsx
// ❌ 反例：本该 server 拉的商品数据放客户端，首屏空 + 无 SEO
'use client'
export default function Page({ params }) {
  const [product, setProduct] = useState(null)
  useEffect(() => { fetch(`/api/product/${params.id}`).then(r=>r.json()).then(setProduct) }, [])
  if (!product) return <Spinner />   // 爬虫与首屏都只看到 spinner
}
```

## 反模式
- ❌ 全站 `'use client'` + `useEffect` 取数 — 丢 SEO、丢首屏、造瀑布
- ❌ 用 SSR(`no-store`) 渲染其实可缓存的列表页 — 白白放弃 CDN 缓存与 TTFB
- ❌ 在 Server Component 里为「加载态」硬拆成 client fetch — 应改用 `loading.tsx`/`<Suspense>`
- ❌ 把鉴权后个性化页做成 SSG — 泄漏/串号
