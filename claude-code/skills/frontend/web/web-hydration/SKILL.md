---
name: web-hydration
pack: frontend:web
description: 修复 hydration 不匹配——server/client 渲染必须一致，禁用 Date.now/random/typeof window 直接进 JSX，善用 Suspense 流式渲染，禁止用 useEffect 掩盖警告。
when_to_use: 出现 "hydration mismatch/Text content did not match" 警告、SSR 页闪烁重渲、或加流式渲染时。
when_NOT_to_use: 纯 CSR 应用（无 SSR，不存在 hydration）。
---

# Skill: Web Hydration

Hydration 是「用 server 返回的 HTML + client 的 JS 重建同一棵树」。两边渲染出的首帧必须逐字节一致，否则 React 丢弃 SSR 结果整块重渲。

## 根因（server 与 client 分歧来源）
- **非确定值**：`Date.now()`、`Math.random()`、`new Date().toLocaleString()`（时区差）直接进 JSX
- **浏览器专属**：`typeof window`、`localStorage`、`matchMedia` 决定首屏渲染分支
- **无效 HTML 嵌套**：`<p>` 里放 `<div>`、`<a>` 套 `<a>`，浏览器纠正后与 React 树不符
- **第三方注入**：扩展/脚本在 hydration 前改 DOM

## 强制规则

1. **首帧确定性** — server 和 client 首次渲染必须产出相同结果；随机/时间/客户端态延到 mount 后
2. **客户端专属值走 mount 后** — 用 `useEffect` 置 `mounted` 后再渲染依赖浏览器的分支（这是正当用法，非掩盖）
3. **Suspense 边界隔离** — 慢/不确定的部分包 `<Suspense>` 流式送达，不阻塞其余首屏
4. **禁止 `suppressHydrationWarning` 灭警告** — 它只关警告不修分歧；仅限已知不可控节点（如时间戳文本）

## 代码

```tsx
// ✅ 客户端专属状态：mount 后再渲，首帧 server/client 一致
'use client'
function Theme() {
  const [mounted, setMounted] = useState(false)
  useEffect(() => setMounted(true), [])
  if (!mounted) return <ThemeToggleSkeleton />        // server 与 client 首帧都渲这个
  return <ThemeToggle value={localStorage.getItem('theme')} />
}

// ✅ 流式渲染：慢数据不阻塞首屏，Suspense 内 await
export default function Page() {
  return (
    <main>
      <Header />
      <Suspense fallback={<FeedSkeleton />}>
        <Feed />   {/* async server component，就绪后流式补齐 */}
      </Suspense>
    </main>
  )
}
```

```tsx
// ❌ 反例：首帧 server(UTC)/client(本地时区) 文本不同 → mismatch
<span>{new Date().toLocaleTimeString()}</span>
```

## 反模式
- ❌ 用 `useEffect` 二次 setState「刷掉」不匹配 — 遮蔽症状，仍有闪烁+重渲开销
- ❌ 全局挂 `suppressHydrationWarning` — 把真实分歧一起吞掉
- ❌ `typeof window !== 'undefined' ? <A/> : <B/>` 决定首屏 — server 恒走 B、client 走 A，必不匹配
- ❌ 无效嵌套 `<p><div/></p>` — 浏览器纠正后树错位
- ❌ 把整页塞进一个 `<Suspense>` — 失去流式收益，退化成一次性等待
