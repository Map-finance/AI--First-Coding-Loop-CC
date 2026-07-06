---
name: node-async-discipline
pack: stack:node
description: Node 后端异步纪律——禁未 await 的 promise、并发用有界 Promise.all/p-limit、AbortController 超时、async/await 替回调地狱、禁在事件循环里做同步重活。
when_to_use: 新增或修改任何异步/并发/超时/批处理逻辑,或涉及 CPU 密集操作时。
when_NOT_to_use: 纯同步工具函数,或与异步无关的改动。
---

# Skill: Node 异步纪律

## 强制规则

1. **禁未 await 的 promise** — 每个返回 Promise 的调用要么 `await`,要么显式 `void`/`.catch()` 处理;禁 fire-and-forget 悄悄丢错(未捕获 → unhandledRejection,见 node-error-handling)。
2. **并发要有界** — 批量并发禁裸 `Promise.all(items.map(...))` 打爆下游/连接池,用 `p-limit` 限并发;顺序无关才用 `Promise.all`,禁把独立任务写成 `for await` 串行。
3. **外部调用带超时** — 所有 I/O(HTTP/DB/RPC)用 `AbortController` + timeout,禁无限等待挂死请求。
4. **禁阻塞事件循环** — CPU 密集(大 JSON、加密、压缩、大循环)不在主线程同步跑;拆分、放 `worker_threads` 或流式处理。

## 有界并发(p-limit)

```ts
import pLimit from 'p-limit';

const limit = pLimit(10); // 最多 10 个并发
const results = await Promise.all(
  orderIds.map((id) => limit(() => fetchOrder(id))),
);
```

## AbortController 超时

```ts
async function fetchWithTimeout(url: string, ms = 3000): Promise<Response> {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), ms);
  try {
    return await fetch(url, { signal: ctrl.signal });
  } finally {
    clearTimeout(timer); // 必须清,否则句柄泄漏
  }
}
```

## 显式处理 fire-and-forget

```ts
// ✅ 确实不等待,也要接住错误
void auditLog(event).catch((err) => logger.error({ err }, 'audit log failed'));

// ✅ 需要结果就 await
const order = await placeOrder(input);
```

## 反模式
- ❌ `sendEmail(user)` 无 await 无 catch — 报错变 unhandledRejection,进程可能被拖崩。
- ❌ `Promise.all(tenThousandIds.map(fetch))` — 一次性万级并发打爆连接池 / 触发下游限流。
- ❌ `for (const id of ids) { await fetchOrder(id); }` — 独立任务串行,10 倍慢;应有界并发。
- ❌ `await fetch(url)` 无超时 — 下游挂起时请求永久 pending,连接耗尽。
- ❌ `getData((err, a) => getMore(a, (err, b) => ...))` — 回调地狱;用 `async/await` 拉平。
- ❌ 主线程 `JSON.parse(hugeString)` / 同步 `bcrypt.hashSync` 循环 — 阻塞事件循环,全服务卡顿。
