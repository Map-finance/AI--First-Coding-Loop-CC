---
name: rust-concurrency
pack: stack:rust
description: Rust并发规范——Send/Sync约束，tokio任务管理，禁持锁跨.await，Mutex/RwLock选择，channel解耦，规避编译器保证之外的逻辑竞争。
when_to_use: 新增或修改Rust并发/异步代码、spawn任务、加锁、或跨线程共享状态时。
when_NOT_to_use: 非Rust代码，或纯同步单线程逻辑无共享状态的改动。
---

# Skill: Rust 并发

## 强制规则

1. **禁持锁跨 `.await`** — `std::sync::Mutex` 的 guard 绝不能跨 `.await` 存活；须锁的临界区在 await 前用块 `{}` 释放，或改用 `tokio::sync::Mutex`
2. **spawn 的 future 必须 `Send + 'static`** — `tokio::spawn` 要求任务可跨线程移动；捕获的引用需 `Arc` 化，别捕借用
3. **锁选择** — 短临界区/无 await 用 `std::sync::Mutex`；读远多于写用 `RwLock`；需跨 await 持有才用 `tokio::sync::Mutex`
4. **优先 channel 解耦** — 任务间传递数据优先用 channel（`mpsc`/`oneshot`）而非共享可变状态，从设计上消除竞争

## 禁持锁跨 await

```rust
// ❌ std guard 跨 await：可能死锁，且编译器因 guard 非 Send 报错
async fn bad(state: Arc<std::sync::Mutex<Vec<u64>>>) {
    let mut g = state.lock().unwrap();
    g.push(fetch().await); // guard 横跨 await ——错误
}

// ✅ 临界区收窄，await 前释放锁
async fn good(state: Arc<std::sync::Mutex<Vec<u64>>>) {
    let value = fetch().await;      // 先 await，不持锁
    state.lock().unwrap().push(value); // 再进临界区，同步完成即释放
}
```

## tokio 任务：Send + 'static

```rust
// ✅ 用 Arc 共享，move 进任务，满足 'static + Send
let shared = Arc::new(Config::load());
let handle = tokio::spawn({
    let shared = Arc::clone(&shared);
    async move { serve(shared).await }
});
handle.await??; // 传播 JoinError 与业务错误

// 结构化并发：错误/取消一致处理
let mut set = tokio::task::JoinSet::new();
for id in ids { set.spawn(process(id)); }
while let Some(res) = set.join_next().await { res??; }
```

## Mutex vs RwLock 选择

| 场景 | 选择 |
|------|------|
| 临界区短、不含 await | `std::sync::Mutex` |
| 读远多于写、不含 await | `std::sync::RwLock` |
| 须跨 `.await` 持有锁 | `tokio::sync::Mutex` / `RwLock` |
| 只需跨任务传值、无共享 | channel（无锁） |

## 逻辑竞争（编译器保证之外）

编译器只保证无数据竞争（内存安全），**不保证无逻辑竞争**：

```rust
// ❌ check-then-act 非原子：两任务可能都读到旧值再各自加
let cur = *counter.lock().unwrap();
if cur < LIMIT { *counter.lock().unwrap() = cur + 1; } // 两次加锁间有窗口

// ✅ 单次临界区内完成读-判-改
let mut g = counter.lock().unwrap();
if *g < LIMIT { *g += 1; }
```

## 反模式
- ❌ `Arc<Mutex<T>>` guard 跨 `.await`——死锁风险，非 Send
- ❌ 用 `std::thread::spawn` 跑异步逻辑——用 `tokio::spawn`
- ❌ `spawn` 后不 `await` handle、不入 `JoinSet`——panic/错误被吞
- ❌ 分两次加锁做 check-then-act——逻辑竞争窗口
- ❌ 该用 channel 传值却塞进共享 `Mutex`——徒增锁争用
