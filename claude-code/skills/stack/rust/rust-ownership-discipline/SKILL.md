---
name: rust-ownership-discipline
pack: stack:rust
description: Rust所有权/借用/生命周期纪律——避免无谓clone，参数优先借用，&str优于String，读多写少用Cow，共享所有权才用Rc/Arc。
when_to_use: 新增或修改Rust函数签名、数据结构、或出现clone/生命周期/借用相关改动时。
when_NOT_to_use: 非Rust代码，或与所有权无关的改动。
---

# Skill: Rust 所有权纪律

## 强制规则

1. **参数优先借用** — 只读取数据的函数收 `&T` / `&str` / `&[T]`，而非 `T` / `String` / `Vec<T>`，除非需要所有权
2. **避免无谓 `clone`** — `.clone()` 前先问"能否借用"；不要用 clone 绕过借用检查器
3. **`&str` 优于 `String`** — 函数参数、只读字段优先 `&str`；`String` 仅用于需要拥有/可变增长的场景
4. **共享才 `Rc`/`Arc`** — 单一所有权别套 `Rc`；跨线程共享用 `Arc`，单线程用 `Rc`；可变共享配 `RefCell`/`Mutex`

## 参数：借用而非取所有权

```rust
// ✅ 只读，借用即可，调用方保留所有权
fn greeting(name: &str) -> String {
    format!("hello, {name}")
}

// ❌ 强夺所有权，逼调用方 clone 或交出变量
fn greeting(name: String) -> String { format!("hello, {name}") }
```

## Cow：读多写少，仅偶尔需拥有

```rust
use std::borrow::Cow;

// 大多数输入合法直接借用，仅非法时才分配新 String
fn sanitize(input: &str) -> Cow<'_, str> {
    if input.contains(' ') {
        Cow::Owned(input.replace(' ', "_")) // 需修改，分配
    } else {
        Cow::Borrowed(input)                // 无需修改，零拷贝
    }
}
```

## 何时用 Rc / Arc

| 场景 | 选择 |
|------|------|
| 单一所有者 | 直接 `T`，别包裹 |
| 单线程多所有者、只读 | `Rc<T>` |
| 单线程多所有者、可变 | `Rc<RefCell<T>>` |
| 跨线程多所有者、只读 | `Arc<T>` |
| 跨线程多所有者、可变 | `Arc<Mutex<T>>` / `Arc<RwLock<T>>` |

## 生命周期常见误用

```rust
// ❌ 返回悬垂引用：借用了函数内局部变量
fn bad() -> &str {
    let s = String::from("tmp");
    &s // s 在函数结束即析构
}

// ✅ 返回所有权，或让生命周期绑定到输入
fn ok(input: &str) -> &str { input.trim() }
```

## 反模式
- ❌ 用 `x.clone()` 消除借用检查器报错——多半说明结构该改，而非该 clone
- ❌ 结构体字段用 `String` 存只读常量键——考虑 `&'static str` 或 `Arc<str>`
- ❌ 到处 `Arc<Mutex<T>>` 却从不跨线程——单线程徒增开销
- ❌ 循环里对同一切片反复 `to_vec()` / `to_string()`——把分配提到循环外或改借用
- ❌ 显式标注可省略的生命周期（能被省略规则推断的）——增噪
