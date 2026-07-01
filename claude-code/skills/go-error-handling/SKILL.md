---
name: go-error-handling
description: Go错误处理规范——哨兵错误定义、errors.Is/As包装链、禁字符串匹配、资金/账本错误绝不吞须进保护模式。
when_to_use: 新增或修改Go错误处理逻辑，或涉及资金/账本/结算操作时。
when_NOT_to_use: 非Go代码，或与错误处理无关的改动。
---

# Skill: Go 错误处理

## 强制规则

1. **哨兵错误** — 用包级 `var ErrXxx = errors.New("xxx")` 定义；调用方用 `errors.Is` 判断，禁止字符串匹配
2. **包装保留链** — `fmt.Errorf("context: %w", err)` 保证 `errors.Is` / `errors.As` 可溯源
3. **多错误** — 用 `errors.Join(err1, err2)`，禁止拼接字符串合并错误
4. **资金/账本错误** — 绝对不吞，进保护模式 + 触发告警

## 定义与使用哨兵错误

```go
// errors.go（包级定义）
var (
    ErrOrderNotFound  = errors.New("order not found")
    ErrInsufficientBalance = errors.New("insufficient balance")
    ErrProtectionMode = errors.New("protection mode activated")
)

// 调用方
if errors.Is(err, ErrOrderNotFound) {
    return status.Error(codes.NotFound, "order not found")
}
```

## 资金/账本错误保护模式

```go
if err := ledger.Debit(ctx, amount); err != nil {
    // 1. 指标告警（不采样）
    metrics.ProtectionModeEntered.WithLabelValues("ledger_debit").Inc()
    // 2. 结构化日志（error 级别）
    slog.ErrorContext(ctx, "ledger debit failed — entering protection mode",
        "amount", amount.String(),
        "err",    err,
    )
    // 3. 返回保护模式错误，上层终止流程
    return ErrProtectionMode
}
```

**资金操作错误禁止：**
- ❌ `if err != nil { continue }` — 静默跳过，直接资损
- ❌ `if err != nil { log.Println(err); return nil }` — 吞掉错误
- ❌ `_ = ledger.Debit(...)` — 完全忽略返回值

## 错误包装

```go
// ✅ 包装时保留原始错误
return fmt.Errorf("order service GetByID(%s): %w", id, err)

// ❌ 丢失原始错误
return fmt.Errorf("order service GetByID failed: %v", err)  // %v 不可 Unwrap
```

## 反模式速查
- ❌ `if err.Error() == "not found"` — 字符串匹配，脆弱
- ❌ `_ = dangerousOp()` — 吞错误
- ❌ `errors.New(fmt.Sprintf(...))` — 不可比较，改用 `fmt.Errorf("...: %w", err)`
- ❌ 资金操作 `if err != nil { continue }` — 直接资损
