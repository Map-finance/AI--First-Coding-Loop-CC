---
name: rust-logging
pack: stack:rust
description: Rust结构化日志规范——只用tracing，字段化事件禁字符串插值，用span和#[instrument]贯穿上下文，级别约定，接可观测后端(OTel)。
when_to_use: 新增或修改任何Rust日志/追踪输出代码时。
when_NOT_to_use: 非Rust代码，或与日志无关的改动。
---

# Skill: Rust 结构化日志 (tracing)

## 强制规则

1. **只用 `tracing`** — 禁 `println!`/`eprintln!`/`log::`(裸用) 输出诊断信息；用 `tracing::{info,warn,error,debug}!`
2. **字段化而非插值** — 用 `field = value` 结构化字段，禁把变量插进消息串
3. **span 贯穿上下文** — 请求/任务用 span 建立作用域，子事件自动继承字段；异步跨 await 用 `#[instrument]`
4. **接后端而非 print** — 通过 `tracing-subscriber` 统一配置输出/过滤，生产接 `tracing-opentelemetry` 导出 trace

## 字段化事件

```rust
use tracing::{info, warn, error};

// ✅ 结构化字段，可被后端索引/查询
info!(order_id = %id, amount, status = "filled", "order settled");

// ❌ 字符串插值，不可查询、无结构
info!("order {id} settled with amount {amount}"); // 反模式
```

`%` = `Display`，`?` = `Debug`；裸 `amount` 表示字段名与变量同名。

## span 与 #[instrument]

```rust
use tracing::{instrument, info};

// 自动创建 span，参数成为字段；skip 掉大/敏感参数
#[instrument(skip(db), fields(order_id = %req.id))]
async fn place_order(db: &Db, req: OrderReq) -> Result<(), OrderError> {
    info!("validating");          // 自动带上 order_id 字段
    db.insert(&req).await?;       // 跨 await，span 上下文不丢失
    info!("placed");
    Ok(())
}
```

## 级别约定

| Level | 场景 |
|-------|------|
| `trace` | 极细粒度，默认关闭 |
| `debug` | 开发调试，生产默认关闭 |
| `info`  | 正常业务事件（下单、登录） |
| `warn`  | 降级、重试、慢路径 |
| `error` | 操作失败，需告警/介入 |

## 接可观测后端

```rust
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt, EnvFilter};

// JSON 结构化 + 环境变量过滤 + OTel 导出
tracing_subscriber::registry()
    .with(EnvFilter::from_default_env())   // RUST_LOG 控制级别
    .with(tracing_subscriber::fmt::layer().json())
    .with(tracing_opentelemetry::layer().with_tracer(tracer))
    .init();
```

## 反模式
- ❌ `println!("processing {id}")` — 无结构、无级别、无 span
- ❌ `info!("user {}", user.password)` — 泄露敏感字段，须 `skip` 或脱敏
- ❌ `#[instrument]` 不 `skip` 大参数（整个 request body）——span 字段爆炸
- ❌ 消息里拼变量而非用字段——后端无法聚合查询
- ❌ 每处 `tracing_subscriber` 各自 init——全局只初始化一次
