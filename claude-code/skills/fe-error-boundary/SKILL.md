---
name: fe-error-boundary
pack: frontend:common
description: 处理前端运行时错误时的规范——用错误边界隔离崩溃、提供降级 UI、捕获异步/事件错误(边界抓不到)、禁静默吞错、错误上报到监控。
when_to_use: 新增可能崩溃的组件树、数据渲染、异步操作,或搭建全局错误处理/上报时。
when_NOT_to_use: 纯静态文案/样式、无运行时逻辑的组件。
---

# Skill: 前端错误边界

## 强制规则
1. **错误边界隔离崩溃** — 用 Error Boundary 包住风险子树,单个组件抛错不白屏整页;路由级至少一个边界。
2. **降级 UI 有意义** — fallback 要给用户可操作项(重试、返回),而非空白或死循环。
3. **异步错误单独处理** — Error Boundary 只抓渲染期错误;`fetch`/`setTimeout`/事件回调里的错误要自己 `try/catch` 或用 react-query 的 `error`。
4. **禁静默吞错** — 空 `catch {}` 是重罪;至少上报 + 给用户反馈。见 secure-coding 的日志脱敏(上报别带 PII)。
5. **上报到监控** — `componentDidCatch`/`onError` 里发 Sentry 等,带上下文(路由、用户匿名 id),不脱敏就是泄露。

## 示例

```tsx
// react-error-boundary
<ErrorBoundary
  fallbackRender={({ error, resetErrorBoundary }) => (
    <div role="alert"><p>出了点问题</p><button onClick={resetErrorBoundary}>重试</button></div>
  )}
  onError={(error, info) => reportToSentry(error, { componentStack: info.componentStack })}
>
  <Dashboard />
</ErrorBoundary>
```

异步错误(边界抓不到):

```tsx
const { data, error } = useQuery({ queryKey: ['x'], queryFn: fetchX });
if (error) return <Retry onClick={refetch} />; // 显式处理,别让它悄悄消失
```

## 反模式
- ❌ 静默吞错:
  ```tsx
  try { await save(); } catch {}  // 用户以为成功了,数据没存,无人知晓
  ```
- ❌ 无边界:顶层组件一处抛错 → React 卸载整棵树 → 白屏。
- ❌ 指望边界抓异步:
  ```tsx
  onClick={async () => { await risky(); }}  // 抛错逃逸边界,页面无反应
  ```
- ❌ 上报带敏感信息:把整个 user 对象(含邮箱/token)发给监控 —— 泄露 PII。

## 判定标准
制造一个渲染期抛错和一个接口 500,前者是否被边界拦成降级 UI、后者是否有可见错误态与重试,且两者都上报?任一悄无声息即不合格。Vue 等价:`onErrorCaptured` 钩子 + `errorHandler` 全局上报。
