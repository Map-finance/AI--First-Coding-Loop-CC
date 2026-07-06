---
name: java-error-handling
pack: stack:java
description: Java错误处理规范——受检vs非受检异常边界、禁吞异常、自定义业务异常、try-with-resources、Spring全局异常处理器。
when_to_use: 新增或修改Java异常处理逻辑，或涉及资源管理/业务错误建模时。
when_NOT_to_use: 非Java代码，或与错误处理无关的改动。
---

# Skill: Java 错误处理

## 强制规则

1. **业务错误用非受检异常** — 自定义业务异常继承 `RuntimeException`，不用受检异常污染整条调用链的签名
2. **禁吞异常** — `catch` 块必须做处理之一：重抛、包装重抛、记录并降级；空 `catch {}` 或只 `printStackTrace` 一律禁止
3. **包装保留 cause** — `throw new XxxException("context", e)`，禁 `throw new XxxException(e.getMessage())`（丢堆栈链）
4. **资源用 try-with-resources** — 所有 `AutoCloseable`（连接、流、锁包装）禁手写 finally close
5. **不 catch 宽泛 `Exception`/`Throwable`** — 只捕获能处理的具体异常；`Throwable` 会吞掉 `Error`（OOM 等）

## 自定义业务异常

```java
public class BusinessException extends RuntimeException {
    private final ErrorCode code;               // 枚举，携带 HTTP 状态 + 业务码

    public BusinessException(ErrorCode code, String message) {
        super(message);
        this.code = code;
    }
    public BusinessException(ErrorCode code, String message, Throwable cause) {
        super(message, cause);                  // 保留 cause 链
        this.code = code;
    }
    public ErrorCode getCode() { return code; }
}

// 抛出
if (balance.compareTo(amount) < 0) {
    throw new BusinessException(ErrorCode.INSUFFICIENT_BALANCE, "余额不足");
}
```

## try-with-resources

```java
// ✅ 自动关闭，异常也不泄漏资源
try (var conn = dataSource.getConnection();
     var stmt = conn.prepareStatement(SQL_GET_ORDER)) {
    stmt.setString(1, orderId);
    return map(stmt.executeQuery());
}
// ❌ 手写 finally，易漏、易吞关闭异常
```

## Spring 全局异常处理器

```java
@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(BusinessException.class)
    public ResponseEntity<ApiError> handleBusiness(BusinessException ex) {
        log.warn("business error: {}", ex.getMessage());      // 业务异常 warn，不打堆栈
        return ResponseEntity.status(ex.getCode().httpStatus())
                             .body(ApiError.of(ex.getCode(), ex.getMessage()));
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<ApiError> handleUnexpected(Exception ex) {
        log.error("unexpected error", ex);                    // 未预期异常 error + 堆栈
        return ResponseEntity.status(500).body(ApiError.internal());
    }
}
```

## 反模式
- ❌ `catch (Exception e) {}` — 静默吞异常，问题消失无踪
- ❌ `catch (Exception e) { e.printStackTrace(); }` — 绕过日志系统，等于吞
- ❌ `throw new BizException(e.getMessage())` — 丢 cause 堆栈链
- ❌ `catch (Throwable t)` — 吞掉 `Error`（OOM/StackOverflow），应崩溃的没崩
- ❌ 业务异常继承 `Exception`（受检）— 强迫上层层层 `throws`，污染签名
