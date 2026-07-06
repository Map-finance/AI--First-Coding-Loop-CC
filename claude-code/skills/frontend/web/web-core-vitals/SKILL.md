---
name: web-core-vitals
pack: frontend:web
description: Core Web Vitals 预算——LCP<2.5s/CLS<0.1/INP<200ms，定位并修复布局抖动、大图未优化、阻塞 JS、字体闪烁(FOIT/FOUT)等常见回归。
when_to_use: 首屏慢、页面跳动、交互卡顿，或 Lighthouse/CrUX 指标回归时。
when_NOT_to_use: 后台内网工具等无性能预算要求的页面。
---

# Skill: Core Web Vitals

三个用户可感知指标，每个都有明确阈值与可复制的修法。

## 预算（p75 目标）

| 指标 | 好 | 主因 |
|---|---|---|
| LCP 最大内容绘制 | < 2.5s | 大图/字体/阻塞资源慢 |
| CLS 累积布局偏移 | < 0.1 | 无尺寸的图/广告/晚插入内容 |
| INP 交互到下次绘制 | < 200ms | 长任务阻塞主线程 |

## 强制规则

1. **图片给显式尺寸** — 用 `next/image` 或写死 `width/height`/`aspect-ratio`，杜绝加载后撑开导致 CLS
2. **首屏大图优先** — LCP 图片 `priority` / `fetchpriority="high"`，非首屏 `loading="lazy"`
3. **字体防闪烁** — `next/font` 或 `font-display: swap` + 预留字形度量（`size-adjust`），避免 FOIT/FOUT 抖动
4. **拆长任务** — 单个 JS 任务 > 50ms 会拖 INP；代码分割、`dynamic(import)` 延迟非关键 JS，重活挪出主线程
5. **给动态内容占位** — 骨架屏/固定高度容器，禁止在已有内容上方插入元素

## 代码

```tsx
// ✅ LCP 图：显式尺寸 + 高优先级，既防 CLS 又抢先加载
import Image from 'next/image'
<Image src={hero} alt="首页横幅" width={1200} height={600} priority />

// ✅ 字体：next/font 内联并预留度量，无闪烁无抖动
import { Inter } from 'next/font/google'
const inter = Inter({ subsets: ['latin'], display: 'swap' })

// ✅ 非关键组件延迟加载，缩短首屏 JS
const Chart = dynamic(() => import('./Chart'), { ssr: false, loading: () => <Skeleton /> })
```

```css
/* ✅ 预留宽高比，图片/嵌入加载不撑动布局 */
.thumb { aspect-ratio: 16 / 9; width: 100%; }
```

## 常见回归 → 修法
- 布局抖动：无尺寸图/广告位 → 显式 `width/height` 或 `aspect-ratio` 占位
- 大图：原图直出 → `next/image` 自动 AVIF/WebP + 响应式 `sizes`
- 阻塞 JS：首屏 bundle 过大 → 分割 + 延迟第三方脚本（`next/script strategy="lazyOnload"`）
- 字体闪烁：默认 `font-display:auto` → `swap` + `size-adjust` 对齐回退字体度量

## 反模式
- ❌ `<img>` 不写宽高 — 加载后跳动，CLS 爆
- ❌ 首屏 LCP 图 `loading="lazy"` — 反而延迟最大内容
- ❌ 同步引第三方分析/聊天 SDK 到 `<head>` — 阻塞渲染与交互
- ❌ 用 `useEffect` 在内容上方插横幅 — 已渲染内容被下推，CLS
