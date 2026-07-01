---
name: go-observability
description: Go可观测性规范——OTel span和Prometheus埋点位置在adapter/middleware层，业务层domain/app不直接写trace/metrics代码。
when_to_use: 新增服务、新增外部调用（DB/gRPC/Kafka/HTTP）、或修改请求处理链路时。
when_NOT_to_use: 纯业务逻辑修改且不涉及新的外部调用或新请求路径。
---

# Skill: Go 可观测性 (OTel + Prometheus)

## 核心原则：埋点不进业务层

```
HTTP/gRPC handler
  → middleware / interceptor   ← OTel span + Prometheus histogram 在这里
      → usecase (app 层)       ← 纯业务逻辑，无 trace/metrics 代码
          → repository adapter ← OTel span + DB query histogram 在这里
              → DB / Kafka / 外部服务
```

## OTel Span（adapter 层）

```go
// repository/order_repo.go — adapter 层，不是 usecase
func (r *OrderRepo) GetByID(ctx context.Context, id ulid.ULID) (*domain.Order, error) {
    ctx, span := r.tracer.Start(ctx, "order.repository.GetByID")
    defer span.End()

    span.SetAttributes(attribute.String("order.id", id.String()))

    order, err := r.db.QueryOne(ctx, sqlGetOrder, id)
    if err != nil {
        span.RecordError(err)
        span.SetStatus(codes.Error, err.Error())
        return nil, fmt.Errorf("order.repository.GetByID: %w", err)
    }
    return order, nil
}
```

## Prometheus 埋点位置

| 指标 | 埋在哪层 |
|------|---------|
| HTTP 请求耗时 / 状态码 | HTTP middleware（自动，不手写） |
| gRPC 请求耗时 / 状态码 | gRPC interceptor（自动，不手写） |
| DB 查询耗时 | repository adapter |
| Kafka produce / consume 延迟 | `platform/kafka` wrapper 内部（已封装） |
| 业务计数（成交量、订单数） | app 层事件，通过事件驱动而非直接调 Prometheus |

## 维度标签约定

```go
labels := prometheus.Labels{
    "service": "matching-engine",
    "method":  "PlaceOrder",
    "status":  "ok",            // ok | error
}
// matching engine 专用
labels["shard_id"] = strconv.Itoa(shardID)
```

## 反模式
- ❌ 在 `domain/` 或 `app/` 层直接 `tracer.Start(...)` — 污染业务逻辑
- ❌ 每个 usecase 方法手写 `prometheus.Counter.Inc()` — 改在 middleware/wrapper 统一收
- ❌ 忘记 `defer span.End()` — span 永不关闭，内存泄漏
- ❌ span 名用动词过去式 `"OrderCreated"` — 用 `"order.service.Create"` (对象.层.动作)
