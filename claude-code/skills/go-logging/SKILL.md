---
name: go-logging
description: 涉及Go日志输出的改动时的结构化日志规范——只用slog，禁zap/zerolog/fmt.Print*，字段snake_case，context贯穿，慢路径固定格式，风暴防护，PII脱敏。
when_to_use: 新增或修改任何Go日志输出代码时。
when_NOT_to_use: 非Go项目，或与日志无关的改动。
---

# Skill: Go 结构化日志 (slog)

## 强制规则

1. **只用 `log/slog`** — 禁 `zap`、`zerolog`、`fmt.Print*`、`log.Print*`（旧标准库）
2. **context 贯穿** — 用 `slog.InfoContext(ctx, ...)` 而非 `slog.Info(...)`；handler 从 ctx 自动提取 trace/request ID
3. **字段名 snake_case** — `request_id`、`correlation_id`、`causation_id`、`trace_id`、`user_id`、`order_id`、`duration_ms`
4. **脱敏** — 密钥、账号、金额 PII 通过 `ReplaceAttr` 钩子掩码，禁止明文出现在日志中

## 慢路径固定格式

慢操作必须用固定字段，便于监控系统聚类：

```go
slog.WarnContext(ctx, "slow operation",
    "kind",         "db_query",       // db_query | grpc_call | kafka_produce | http_call
    "op",           "order.GetByID",
    "duration_ms",  elapsed.Milliseconds(),
    "threshold_ms", 100,
)
```

必须字段：`kind` / `op` / `duration_ms` / `threshold_ms`，缺一不可。

## 日志风暴防护

激增场景（重试风暴、连接抖动）必须限流 + 采样，**监控指标不采样，日志可采样**：

```go
// 只在首次和每 N 次记录
if attempt == 0 || attempt%100 == 0 {
    slog.ErrorContext(ctx, "connection failed",
        "attempt", attempt,
        "err",     err,
    )
}
// 同时无论如何更新 metrics（不采样）
metrics.ConnectionErrors.Inc()
```

## 日志级别约定

| Level | 场景 |
|-------|------|
| `Debug` | 开发调试，生产默认关闭 |
| `Info`  | 正常业务事件（订单成交、用户登录） |
| `Warn`  | 慢路径、降级、重试中 |
| `Error` | 操作失败，需人工介入或告警 |

## 反模式
- ❌ `zap.L().Info("...")` — 禁用 zap
- ❌ `fmt.Printf("order %d failed", id)` — 不结构化，不可查询
- ❌ `log.Println(err)` — 旧标准库，无结构，无 context
- ❌ `slog.Info("login", "account", user.BankAccount)` — 泄露 PII
- ❌ `slog.Error("failed", "err", err)` — 缺少 context，改用 `slog.ErrorContext(ctx, ...)`
