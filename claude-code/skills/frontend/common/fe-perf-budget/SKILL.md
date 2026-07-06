---
name: fe-perf-budget
pack: frontend:common
description: 关注前端性能时的规范——设定并守住 bundle 体积预算、路由级代码分割与懒加载、图片优化、消除不必要重渲染、审查新依赖体积。
when_to_use: 引入新依赖、bundle 变大、页面卡顿/重渲染频繁、或做性能优化/review 时。
when_NOT_to_use: 原型验证阶段、内部低频工具页、明确无性能要求的场景。
---

# Skill: 前端性能预算

## 强制规则
1. **有明确预算并 CI 守门** — 首屏 JS gzip 设上限(如 ≤ 170KB),超了 CI 失败;无数字的"注意性能"等于没预算。
2. **路由级代码分割** — 用 `React.lazy` + `Suspense` 按路由/重组件拆包,非首屏代码不进主 chunk。
3. **图片优化** — 用现代格式(WebP/AVIF)、响应式 `srcset`、懒加载 `loading="lazy"`、显式尺寸防 CLS。
4. **消除不必要重渲染** — 稳定引用(`useMemo`/`useCallback`)、`memo` 纯组件、列表用稳定 `key`;派生态别存(见 fe-state-management)。
5. **依赖体积审查** — 加包前查 bundlephobia;能用平台 API(`Intl`/`Date`)就别引 moment 类大库;按需引入(`lodash-es` + tree-shaking)。

## 反模式
- ❌ 首屏塞全部:
  ```tsx
  import Dashboard from './Dashboard'; // 500KB 图表库进主 bundle
  const Dashboard = lazy(() => import('./Dashboard')); // 正确:按需加载
  ```
- ❌ 内联对象/函数 props 致子组件每次重渲染:
  ```tsx
  <List style={{ padding: 8 }} onPick={x => setSel(x)} />  // 每次渲染新引用
  const onPick = useCallback((x) => setSel(x), []);        // 稳定引用
  ```
- ❌ 引整包:`import _ from 'lodash'` —— 拉进整个库;改 `import debounce from 'lodash-es/debounce'`。
- ❌ 图片无尺寸 + 无懒加载:大图直出 `<img src>` —— 阻塞首屏 + 布局抖动(CLS)。

## 判定标准
Lighthouse 性能分、bundle analyzer 的首屏 chunk 大小、React Profiler 的重渲染次数,三者对照预算超标即不合格。用 `<Profiler>` 或 React DevTools 定位无谓重渲染。Vue 等价:`defineAsyncComponent` 懒加载,`v-memo`/`shallowRef` 控重渲染。
