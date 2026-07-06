---
name: node-error-handling
pack: stack:node
description: Node 后端错误处理规范——区分可运营错误 vs 编程错误、AppError 类 + 错误码、集中错误中间件、禁吞 unhandledRejection/uncaughtException。
when_to_use: 新增或修改 Node/TS 错误处理逻辑、抛错、错误中间件、进程级异常钩子时。
when_NOT_to_use: 前端代码,或与错误处理无关的改动。
---

# Skill: Node 错误处理

## 强制规则

1. **区分可运营错误 vs 编程错误** — 可运营(operational:参数非法、余额不足、404)用 `AppError` 抛出并转成 HTTP 响应;编程错误(bug:`undefined.x`、断言失败)不该 catch 后继续,应让进程崩溃重启。
2. **AppError 类 + 错误码** — 所有可运营错误继承 `AppError`,带稳定 `code`(机器可读)+ `statusCode`;禁裸 `throw new Error('...')` 供上层字符串匹配。
3. **集中错误中间件** — 唯一负责把错误映射成响应体的地方,放路由链最后(见 node-middleware);业务层只抛不转 HTTP。
4. **禁吞进程级异常** — 挂 `unhandledRejection`/`uncaughtException` 钩子,记日志后**优雅退出**让编排器重启,禁空 catch 静默。

## AppError 类

```ts
// errors.ts
export class AppError extends Error {
  constructor(
    public readonly code: string,        // 稳定机器码:'ORDER_NOT_FOUND'
    message: string,
    public readonly statusCode = 400,
    public readonly isOperational = true, // 可运营 → 可安全转响应
  ) {
    super(message);
    Error.captureStackTrace(this, this.constructor);
  }
}

export class NotFoundError extends AppError {
  constructor(res: string) { super(`${res.toUpperCase()}_NOT_FOUND`, `${res} not found`, 404); }
}
// 用法:throw new NotFoundError('order') / new AppError('INSUFFICIENT_BALANCE', '余额不足', 422)
```

## 集中错误中间件(放最后)

```ts
// errorHandler.ts —— app.use(errorHandler) 必须在所有路由之后
export function errorHandler(err: unknown, req: Request, res: Response, _next: NextFunction) {
  if (err instanceof AppError && err.isOperational) {
    req.log.warn({ code: err.code, status_code: err.statusCode }, err.message);
    return res.status(err.statusCode).json({ code: err.code, message: err.message, request_id: req.id });
  }
  // 编程错误:记 error 级 + 返回 500,不泄露内部细节
  req.log.error({ err }, 'unhandled programmer error');
  res.status(500).json({ code: 'INTERNAL', message: 'internal error', request_id: req.id });
}
```

## 进程级异常(禁吞)

```ts
for (const sig of ['unhandledRejection', 'uncaughtException'] as const) {
  process.on(sig, (err) => {
    logger.fatal({ err, sig }, 'fatal — shutting down'); // 记完优雅退出,交给 k8s/pm2 重启
    server.close(() => process.exit(1));
  });
}
```

## 反模式
- ❌ `catch (e) {}` 空 catch — 吞掉编程错误,bug 静默,后续状态错乱。
- ❌ `if (e.message === 'not found')` — 字符串匹配脆弱;判 `e.code === 'ORDER_NOT_FOUND'`。
- ❌ `uncaughtException` 钩子记完继续跑 — 进程带脏状态残喘,更危险。
- ❌ 在业务/repository 层 `res.status(500).send()` — 越权处理 HTTP,应只抛 `AppError` 交中间件。
- ❌ `throw 'string'` / `throw { code }` — 非 Error 实例,丢栈,`instanceof` 失效。
