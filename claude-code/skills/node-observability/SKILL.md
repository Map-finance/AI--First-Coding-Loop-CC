---
name: node-observability
pack: stack:node
description: Node 后端可观测性规范——OTel span 和 prom-client 指标埋点在 middleware/adapter 层,业务层(service/usecase)不直接写 trace/metrics 代码。
when_to_use: 新增服务、新增外部调用(DB/HTTP/RPC/队列)、或修改请求处理链路时。
when_NOT_to_use: 纯业务逻辑修改且不涉及新的外部调用或新请求路径。
---

# Skill: Node 可观测性 (OTel + prom-client)

## 核心原则:埋点不进业务层(对齐 go-observability)

```
HTTP handler
  → middleware              ← OTel span + prom-client histogram 在这里
      → service / usecase   ← 纯业务逻辑,无 trace/metrics 代码
          → repository / client adapter ← OTel span + DB/HTTP 耗时直方图在这里
              → DB / 队列 / 外部服务
```

## OTel 自动埋点 + adapter 手动 span

```ts
// tracing.ts —— 进程启动最先 require,自动插桩 http/express/pg
import { NodeSDK } from '@opentelemetry/sdk-node';
import { getNodeAutoInstrumentations } from '@opentelemetry/auto-instrumentations-node';
new NodeSDK({ instrumentations: [getNodeAutoInstrumentations()] }).start();
```

```ts
// order.repository.ts —— adapter 层显式 span,不是 service 层
import { trace, SpanStatusCode } from '@opentelemetry/api';
const tracer = trace.getTracer('order-repo');

async getById(id: string): Promise<Order> {
  return tracer.startActiveSpan('order.repository.getById', async (span) => {
    span.setAttribute('order.id', id);
    try {
      return await this.db.one(sqlGetOrder, [id]);
    } catch (err) {
      span.recordException(err as Error);
      span.setStatus({ code: SpanStatusCode.ERROR });
      throw err;
    } finally {
      span.end(); // 必须 end,否则 span 泄漏
    }
  });
}
```

## prom-client 埋点位置

| 指标 | 埋在哪层 |
|------|---------|
| HTTP 请求耗时 / 状态码 | HTTP middleware(见 node-middleware,自动,不手写) |
| DB 查询耗时 | repository adapter |
| 外部 HTTP / RPC 延迟 | client adapter wrapper 内部 |
| 队列 produce/consume 延迟 | 队列 wrapper 内部(已封装) |
| 业务计数(成交量、订单数) | 由 service 发领域事件,监听器统一收,而非 service 直调 counter |

## 反模式
- ❌ 在 `service/`、`usecase/` 里 `tracer.startActiveSpan(...)` — 污染业务逻辑,与 go 一致禁止。
- ❌ 每个 service 方法手写 `counter.inc()` — 改在 middleware/wrapper 统一收,或走领域事件。
- ❌ `startSpan` 后忘记 `span.end()` — span 永不关闭,内存泄漏。
- ❌ span 名用动词过去式 `'OrderCreated'` — 用 `'order.service.create'`(对象.层.动作)。
- ❌ label 用高基数值(order_id、user_id)— 指标爆炸;高基数放 span attribute。
