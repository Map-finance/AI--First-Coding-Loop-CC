---
name: java-logging
pack: stack:java
description: Java结构化日志规范——slf4j门面+logback/log4j2实现，只用参数化占位符，MDC传request-id，禁System.out.println，级别约定，PII脱敏。
when_to_use: 新增或修改任何Java日志输出代码时。
when_NOT_to_use: 非Java项目，或与日志无关的改动。
---

# Skill: Java 结构化日志 (slf4j)

## 强制规则

1. **只用 slf4j 门面** — `private static final Logger log = LoggerFactory.getLogger(Xxx.class);`；实现层用 logback 或 log4j2，业务代码不依赖具体实现
2. **禁 `System.out.println` / `printStackTrace()`** — 无级别、无结构、绕过采集，一律禁用
3. **参数化占位符** — `log.info("order {} paid, amount={}", id, amount)`，禁字符串拼接 `"order " + id`（省去无用级别的求值开销，且防注入）
4. **MDC 传贯穿标识** — request-id / trace-id 在入口过滤器写入 MDC，日志 pattern 自动带出，业务层不手传
5. **脱敏** — 手机号、身份证、卡号、密钥经掩码后输出，禁明文

## MDC 传 request-id

```java
// 入口 Filter / Interceptor（Web 层，非业务层）
public class MdcFilter extends OncePerRequestFilter {
    @Override
    protected void doFilterInternal(HttpServletRequest req, HttpServletResponse resp,
                                    FilterChain chain) throws ServletException, IOException {
        String requestId = Optional.ofNullable(req.getHeader("X-Request-Id"))
                                   .orElse(UUID.randomUUID().toString());
        MDC.put("request_id", requestId);
        try {
            chain.doFilter(req, resp);
        } finally {
            MDC.clear();   // 必须清理，线程复用会串号
        }
    }
}
```

logback pattern：`%d %-5level [%X{request_id}] %logger{36} - %msg%n`

## 日志级别约定

| Level | 场景 |
|-------|------|
| `TRACE`/`DEBUG` | 开发调试，生产默认关闭 |
| `INFO`  | 正常业务事件（下单成功、用户登录） |
| `WARN`  | 慢路径、降级、重试中、可恢复异常 |
| `ERROR` | 操作失败，需人工介入或告警 |

## 异常日志

```java
// ✅ 异常对象作最后一个参数（不占位符），完整堆栈进日志
log.error("order {} settle failed", orderId, ex);

// ❌ 只打 message，丢堆栈
log.error("settle failed: " + ex.getMessage());
```

## 反模式
- ❌ `System.out.println("order " + id)` — 无级别、无结构、不可采集
- ❌ `e.printStackTrace()` — 输出到 stderr，绕过日志系统
- ❌ `log.info("user login: " + user.getIdCard())` — 拼接且泄露 PII
- ❌ `log.error("failed", ex.getMessage())` — message 被当占位符参数，丢堆栈
- ❌ `log.debug("dump: " + expensiveToString())` — 拼接使 debug 关闭时仍求值，改用占位符
