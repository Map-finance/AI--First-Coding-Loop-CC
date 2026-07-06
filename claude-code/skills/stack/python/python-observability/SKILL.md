---
name: python-observability
pack: stack:python
description: Python可观测性规范——OpenTelemetry+prometheus_client埋点位置在装饰器/中间件层，业务函数不直接写span/metric代码，指标命名带单位后缀，trace跨async传播。
when_to_use: 新增服务、新增外部调用（DB/HTTP/MQ）、或修改请求处理链路时。
when_NOT_to_use: 纯业务逻辑修改且不涉及新的外部调用或新请求路径。
---

# Skill: Python 可观测性 (OTel + prometheus_client)

## 核心原则：埋点不进业务层

```
Route handler
  → 中间件 / 装饰器          ← OTel span + Prometheus Histogram 在这里
      → service (业务逻辑)    ← 纯业务，无 span/metric 代码
          → repository / client  ← DB/HTTP span（多数用 OTel instrumentation 自动埋）
              → DB / 外部服务
```

优先用 `opentelemetry-instrumentation-*`（FastAPI/requests/psycopg 自动埋点），装饰器只补业务维度。

## 装饰器埋点（不进函数体）

```python
import time
from functools import wraps
from prometheus_client import Histogram

SERVICE_DURATION = Histogram(
    "app_service_duration_seconds",       # 单位后缀 _seconds
    "service method duration",
    ["method", "status"],                 # 低基数标签
)

def observed(method: str):
    def deco(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            status = "ok"
            start = time.perf_counter()
            try:
                return fn(*args, **kwargs)
            except Exception:
                status = "error"
                raise
            finally:
                SERVICE_DURATION.labels(method, status).observe(
                    time.perf_counter() - start)
        return wrapper
    return deco

@observed("order.place")                  # 业务函数只加装饰器，体内干净
def place_order(cmd): ...
```

## 指标命名与标签

- **单位后缀**：耗时 `_seconds`、字节 `_bytes`、计数 `_total`（Counter 自动补 `_total`）
- **低基数标签**：`method` / `status(ok|error)` / `endpoint`；禁 `order_id`、`user_id`（基数爆炸拖垮 Prometheus）
- **Counter/Histogram/Gauge 用对**：累加计数用 Counter，分布用 Histogram，瞬时值用 Gauge

## trace 跨 async 传播

```python
# OTel context 随 asyncio 自动传播（contextvars），但线程池要显式带上
loop.run_in_executor(pool, otel_context.attach_wrapper(work))
# 或用 opentelemetry.context 手动 attach/detach
```

## 反模式
- ❌ 在 service 函数体内 `counter.inc()` / `tracer.start_span()` — 污染业务逻辑，改用装饰器/中间件
- ❌ 指标标签用 `order_id` / `user_id` — 高基数，Prometheus 内存爆炸
- ❌ 指标名无单位后缀 `duration` — 应 `duration_seconds`
- ❌ 手动 `start_span` 忘记 `end()` / 未用 `with tracer.start_as_current_span()` — span 泄漏、断链
- ❌ 每次请求 `Histogram(...)` 在函数内重建 — 指标应模块级定义一次
