---
name: rust-error-handling
pack: stack:rust
description: Rust错误处理规范——Result/?传播，库用thiserror、应用用anyhow，可恢复路径禁unwrap/expect，错误带上下文，明确panic边界。
when_to_use: 新增或修改Rust错误处理逻辑、定义错误类型、或涉及可能失败的操作时。
when_NOT_to_use: 非Rust代码，或与错误处理无关的改动。
---

# Skill: Rust 错误处理

## 强制规则

1. **用 `?` 传播** — 可失败函数返回 `Result<T, E>`，用 `?` 上抛，禁止手写 `match` 后 `return Err(e)` 样板
2. **库用 `thiserror`** — 库/领域层定义具体枚举错误，实现 `std::error::Error`，让调用方能匹配处理
3. **应用用 `anyhow`** — 二进制/顶层 handler 用 `anyhow::Result`，配 `.context()` 附加语义
4. **可恢复路径禁 `unwrap`/`expect`** — 只允许在测试、初始化不变量、或已证明不可能失败处使用，且 `expect` 必须写清"为何不可能失败"

## 库错误：thiserror

```rust
use thiserror::Error;

#[derive(Debug, Error)]
pub enum OrderError {
    #[error("order not found: {0}")]
    NotFound(OrderId),
    #[error("insufficient balance: need {need}, have {have}")]
    InsufficientBalance { need: u64, have: u64 },
    #[error("db error")]
    Db(#[from] sqlx::Error), // #[from] 自动转换 + 保留来源链
}

pub fn get_order(id: OrderId) -> Result<Order, OrderError> {
    let row = query_order(id)?;              // sqlx::Error 经 #[from] 自动转 OrderError
    row.ok_or(OrderError::NotFound(id))
}
```

## 应用错误：anyhow + context

```rust
use anyhow::{Context, Result};

fn run(cfg_path: &Path) -> Result<()> {
    let raw = fs::read_to_string(cfg_path)
        .with_context(|| format!("reading config {}", cfg_path.display()))?;
    let cfg: Config = toml::from_str(&raw)
        .context("parsing config as TOML")?;   // 出错时消息链清晰可读
    start_server(cfg).context("starting server")?;
    Ok(())
}
```

## panic 边界

- panic 只用于**不可恢复的程序 bug**（违反不变量、逻辑错误），不用于预期的运行时失败
- 库代码不应 panic 穿透到调用方；长期运行服务的任务边界须 catch，避免单请求 panic 拖垮进程

```rust
// ✅ 已证明不可能失败，且注明理由
let port: u16 = "8080".parse().expect("hardcoded port literal is valid");

// ❌ 可恢复路径直接 unwrap，用户输入非法即崩溃
let port: u16 = user_input.parse().unwrap();
```

## 反模式
- ❌ `result.unwrap()` 处理用户输入 / IO / 网络等可恢复错误
- ❌ `map_err(|e| MyError::Generic(e.to_string()))` — 丢失来源链，改用 `#[from]` 或 `#[source]`
- ❌ 库里返回 `anyhow::Error` — 调用方无法按变体匹配处理
- ❌ `.expect("")` 空消息 — panic 时无从定位
- ❌ `if let Err(_) = op() {}` — 静默吞错误
