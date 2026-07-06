---
name: node-logging
pack: stack:node
description: 涉及 Node 后端日志输出的改动时的结构化日志规范——只用 pino,禁 console.log,request-id 贯穿,字段 snake_case,PII 脱敏,级别约定,风暴采样。
when_to_use: 新增或修改任何 Node/TS 后端日志输出代码时。
when_NOT_to_use: 前端浏览器代码,或与日志无关的改动。
---

# Skill: Node 结构化日志 (pino)

## 强制规则

1. **只用 `pino`** — 禁 `console.log/error/warn`、`console.dir`、`util.inspect` 打日志、`morgan` 裸文本;开发期人类可读用 `pino-pretty`(仅 dev)。
2. **request-id 贯穿** — 每请求生成/透传 `x-request-id`,用 child logger 绑定,贯穿整条调用链(见 node-middleware 的 request-id 中间件)。
3. **字段名 snake_case** — `request_id`、`trace_id`、`user_id`、`order_id`、`duration_ms`、`status_code`;禁把整个 `req`/`res`/`error` 对象直接塞进日志。
4. **PII 脱敏** — 用 pino `redact` 掩码密钥、token、账号、金额、手机号,禁明文入日志(见 secure-coding)。

## 基础配置(TypeScript)

```ts
// logger.ts —— 单例,全应用共享
import pino from 'pino';

export const logger = pino({
  level: process.env.LOG_LEVEL ?? 'info',
  redact: {
    paths: ['req.headers.authorization', 'password', 'token', '*.card_no', '*.bank_account'],
    censor: '[REDACTED]',
  },
  formatters: { level: (label) => ({ level: label }) },
});
```

## request-id child logger

```ts
// 中间件里(见 node-middleware),把 child logger 挂到 req 上贯穿全链路
const requestId = req.header('x-request-id') ?? crypto.randomUUID();
req.log = logger.child({ request_id: requestId, trace_id: req.traceId });

// 业务/adapter 层统一用 req.log,不再引全局 logger
req.log.info({ order_id: order.id, duration_ms: elapsed }, 'order placed');
```

## 日志级别约定

| Level | 场景 |
|-------|------|
| `debug` | 开发调试,生产默认关闭 |
| `info`  | 正常业务事件(下单成功、登录) |
| `warn`  | 慢路径、降级、重试中 |
| `error` | 操作失败,需人工介入或告警 |
| `fatal` | 进程不可恢复,即将退出 |

## 日志风暴采样

激增场景(重试风暴、连接抖动)必须采样,**监控指标不采样,日志可采样**(对齐 go-logging):

```ts
if (attempt === 0 || attempt % 100 === 0) {
  req.log.error({ attempt, err: err.message }, 'upstream connect failed');
}
metrics.upstreamErrors.inc(); // 指标始终 +1(见 node-observability)
```

## 反模式
- ❌ `console.log('order', order)` — 无结构、无 level、无 request-id、生产不可查询。
- ❌ `logger.info('user ' + user.phone + ' login')` — 字符串拼接 + 泄露 PII。
- ❌ `logger.error(err)` 只传 Error 对象无消息 — 无上下文;应 `logger.error({ err, order_id }, 'msg')`。
- ❌ 每请求 `pino()` 新建实例 — 应全局单例 + `child()`。
- ❌ 循环里逐条 `info` 无采样 — 风暴刷爆日志盘。
