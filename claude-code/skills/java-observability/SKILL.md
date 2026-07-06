---
name: java-observability
pack: stack:java
description: Java可观测性规范——Micrometer+OTel埋点位置在AOP切面/adapter层，业务service不直接写trace/metrics代码，指标命名点分层，trace跨线程/异步传播。
when_to_use: 新增服务、新增外部调用（DB/HTTP/MQ）、或修改请求处理链路时。
when_NOT_to_use: 纯业务逻辑修改且不涉及新的外部调用或新请求路径。
---

# Skill: Java 可观测性 (Micrometer + OTel)

## 核心原则：埋点不进业务层

```
Controller
  → AOP 切面 / Filter        ← Micrometer Timer + OTel span 在这里
      → Service (业务逻辑)    ← 纯业务，无 Timer/Tracer 代码
          → Repository / Client adapter  ← DB/HTTP span 在这里（多数由 starter 自动埋）
              → DB / 外部服务
```

Spring Boot Actuator + `micrometer-tracing-bridge-otel` 已自动埋 HTTP/JDBC/RestClient，**优先用自动埋点**，切面只补业务维度。

## AOP 切面埋点（不进 service 方法体）

```java
@Aspect
@Component
@RequiredArgsConstructor
public class MetricsAspect {
    private final MeterRegistry registry;

    @Around("@annotation(Timed)")   // 只需在 service 方法上标 @Timed 注解
    public Object timed(ProceedingJoinPoint pjp) throws Throwable {
        Timer.Sample sample = Timer.start(registry);
        String method = pjp.getSignature().toShortString();
        String status = "ok";
        try {
            return pjp.proceed();
        } catch (Throwable t) {
            status = "error";
            throw t;
        } finally {
            sample.stop(registry.timer("app.service.duration",
                    "method", method, "status", status));
        }
    }
}
```

## 指标命名与标签

- **命名点分层**：`app.order.placed.total`、`app.service.duration`、`http.server.requests`（点分小写，全局唯一）
- **单位后缀约定**：计数 `.total`，耗时用 Timer（自带 `_seconds`），字节 `.bytes`
- **标签低基数**：`method` / `status(ok|error)` / `service`；禁把 `order_id`、`user_id` 当标签（基数爆炸拖垮 TSDB）

## trace 跨线程 / 异步传播

```java
// ❌ 裸线程池丢失 trace 上下文（span 断链）
executor.submit(() -> handle(order));

// ✅ 用 context-propagation 包装，或直接用 Micrometer 的 ContextSnapshot
ContextSnapshot snapshot = ContextSnapshotFactory.builder().build().captureAll();
executor.submit(snapshot.wrap(() -> handle(order)));
```

## 反模式
- ❌ 在 `service` 方法体内 `registry.counter(...).increment()` — 污染业务逻辑，改用切面/注解
- ❌ 指标标签用 `orderId` / `userId` — 高基数，TSDB 内存爆炸
- ❌ 手动 span 忘记 `span.end()` / 未 try-finally — span 泄漏、trace 断链
- ❌ `@Async` / 线程池里直接跑而不传播 context — trace 断链，跨线程无法关联
- ❌ 指标名用驼峰 `orderPlacedCount` — 应点分小写 `app.order.placed.total`
