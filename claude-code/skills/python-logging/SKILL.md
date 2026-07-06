---
name: python-logging
pack: stack:python
description: Python结构化日志规范——logging/structlog，禁print，request-id经contextvars/绑定注入，参数化不用f-string拼message，级别约定，PII脱敏。
when_to_use: 新增或修改任何Python日志输出代码时。
when_NOT_to_use: 非Python项目，或与日志无关的改动。
---

# Skill: Python 结构化日志 (structlog)

## 强制规则

1. **用 `logging` / `structlog`，禁 `print`** — `print` 无级别、无结构、绕过采集，一律禁用
2. **模块级 logger** — `logger = structlog.get_logger(__name__)`，不用 root logger
3. **结构化字段传参，禁 f-string 拼 message** — `logger.info("order paid", order_id=id, amount=amt)`，不写 `f"order {id} paid"`（否则不可查询、级别关闭仍求值）
4. **request-id 用 contextvars 绑定** — 入口中间件 `bind_contextvars`，日志自动带出，业务层不手传
5. **脱敏** — 手机号、身份证、卡号、密钥经 processor 掩码后输出，禁明文

## request-id 绑定（中间件层）

```python
import structlog
from structlog.contextvars import bind_contextvars, clear_contextvars

async def request_id_middleware(request, call_next):
    clear_contextvars()
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    bind_contextvars(request_id=request_id)   # 该请求内所有日志自动带 request_id
    try:
        return await call_next(request)
    finally:
        clear_contextvars()                   # 必须清理
```

## structlog 结构化输出

```python
logger = structlog.get_logger(__name__)

# ✅ 字段作 kwargs，机器可查询
logger.info("order settled", order_id=order.id, amount=str(order.amount))

# ❌ f-string 拼进 message，不可查询、debug 关闭时仍求值
logger.info(f"order {order.id} settled amount {order.amount}")
```

## 日志级别约定

| Level | 场景 |
|-------|------|
| `DEBUG` | 开发调试，生产默认关闭 |
| `INFO`  | 正常业务事件（下单成功、任务完成） |
| `WARNING` | 慢路径、降级、重试中、可恢复异常 |
| `ERROR` | 操作失败，需人工介入或告警 |

## 异常日志

```python
try:
    settle(order)
except SettleError:
    # ✅ logger.exception 自动附带堆栈（等价 error + exc_info=True）
    logger.exception("settle failed", order_id=order.id)
    raise
```

## 反模式
- ❌ `print(f"order {id} failed")` — 无级别、无结构、不可采集
- ❌ `logging.info("user " + user.id_card)` — 拼接且泄露 PII
- ❌ `logger.error(f"failed: {e}")` — 丢堆栈，改用 `logger.exception(...)`
- ❌ 用 root logger `logging.info(...)` — 无法按模块配置级别
- ❌ `logger.debug(f"dump {expensive()}")` — f-string 使 debug 关闭时仍求值
