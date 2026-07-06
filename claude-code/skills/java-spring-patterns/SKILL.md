---
name: java-spring-patterns
pack: stack:java
description: Spring分层与注入规范——构造器注入不用@Autowired字段注入、@Transactional边界与自调用/rollbackFor陷阱、controller/service/repository分层、避免循环依赖。
when_to_use: 新增或修改Spring Bean、事务边界、分层结构时。
when_NOT_to_use: 非Spring项目，或纯工具类无框架依赖的改动。
---

# Skill: Spring 分层与依赖注入

## 强制规则

1. **构造器注入** — 依赖用 `final` 字段 + 构造器注入，禁 `@Autowired` 字段注入（不可测、隐藏依赖、易致循环依赖）
2. **分层单向依赖** — `Controller → Service → Repository`，禁反向依赖、禁 Controller 直连 Repository
3. **`@Transactional` 放 Service 层** — 事务边界在 service 方法，不在 controller、不在 repository
4. **`@Transactional` 必标 `rollbackFor`** — 默认只回滚 `RuntimeException`，受检异常不回滚；显式声明避免脏数据
5. **循环依赖是设计错误** — 不用 `@Lazy` 硬绕，重构：抽公共依赖或用事件解耦

## 构造器注入（Lombok 简化）

```java
@Service
@RequiredArgsConstructor          // 为所有 final 字段生成构造器
public class OrderService {
    private final OrderRepository orderRepository;
    private final PaymentClient paymentClient;
    // 无 @Autowired，依赖显式、可 final、单测直接 new
}
```

## @Transactional 陷阱

```java
@Service
@RequiredArgsConstructor
public class OrderService {

    // ✅ 事务在 service，显式 rollbackFor
    @Transactional(rollbackFor = Exception.class)
    public void placeOrder(OrderCmd cmd) {
        orderRepository.save(...);
        this.deductStock(cmd);    // ❌ 陷阱：同类内部自调用，代理失效，@Transactional 不生效
    }

    @Transactional
    public void deductStock(OrderCmd cmd) { ... }
}
```

**两大陷阱**：
- **自调用失效** — 同一个类内 `this.method()` 调用绕过 Spring 代理，注解不生效。拆到另一个 Bean，或注入自身代理。
- **私有方法失效** — `@Transactional` 只对 public 方法（代理）生效，private 方法上无效。

## 分层职责

| 层 | 职责 | 禁止 |
|----|------|------|
| Controller | 参数校验、DTO 转换、调 service | 写业务逻辑、直连 repository |
| Service | 业务逻辑、事务边界、编排 | 处理 HTTP 细节、拼 SQL |
| Repository | 数据访问 | 写业务规则 |

## 反模式
- ❌ `@Autowired private OrderRepository repo;` — 字段注入，不可测、隐藏依赖
- ❌ Controller 里 `@Autowired OrderRepository` 直连 DAO — 跨层
- ❌ `@Transactional` 标在 private 方法 — 代理不生效，静默无事务
- ❌ 同类内 `this.txMethod()` 期望开启事务 — 自调用绕过代理
- ❌ `@Lazy` 打补丁解循环依赖 — 掩盖设计问题，应重构
