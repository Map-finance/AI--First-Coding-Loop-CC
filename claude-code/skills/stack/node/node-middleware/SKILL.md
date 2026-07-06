---
name: node-middleware
pack: stack:node
description: Node 后端中间件规范——固定执行顺序(request-id→日志→鉴权→校验→路由→错误中间件最后)、鉴权前置、输入校验、错误中间件收尾、禁在中间件里做重业务。
when_to_use: 新增或调整 Express/Nest 中间件、拦截器、guard、请求处理链顺序时。
when_NOT_to_use: 纯业务逻辑或与请求链无关的改动。
---

# Skill: Node 中间件

## 强制规则

1. **顺序固定** — request-id → 请求日志 → body 解析 → 鉴权 → 授权 → 输入校验 → 业务路由 → **错误中间件(最后)**;顺序错会导致未鉴权就落库、错误未被捕获。
2. **鉴权前置** — 认证(你是谁)和授权(你能不能)在业务 handler 之前完成,失败即短路 401/403;禁在业务里才查权限(见 secure-coding)。
3. **输入校验独立** — 用 `zod`/`class-validator` 在中间件/DTO 层校验并收窄类型,handler 只收干净数据;禁在业务逻辑里散落 `if (!req.body.x)`。
4. **错误中间件放最后** — 四参 `(err, req, res, next)` 唯一,注册在所有路由之后(见 node-error-handling);中间件里抛错必须 `next(err)` 而非自行响应。
5. **中间件保持轻** — 只做横切关注(auth/log/校验/限流);禁在中间件里写下单、结算等重业务或多次 DB 调用。

## 顺序示例(Express)

```ts
app.use(requestIdMiddleware);          // 1. 生成/透传 x-request-id
app.use(pinoHttp({ logger }));         // 2. 请求日志(见 node-logging)
app.use(express.json({ limit: '1mb' }));// 3. body 解析(限大小)
app.use(authenticate);                 // 4. 鉴权(见 secure-coding)
app.use('/orders', authorize('order:write'), validate(CreateOrderDto), orderRouter); // 5-6-7
app.use(errorHandler);                 // 8. 错误中间件,必须最后
```

## 校验中间件(zod)

```ts
export const validate = (schema: ZodSchema) =>
  (req: Request, _res: Response, next: NextFunction) => {
    const parsed = schema.safeParse(req.body);
    if (!parsed.success) return next(new AppError('VALIDATION_ERROR', parsed.error.message, 422));
    req.body = parsed.data; // 收窄后的干净数据交给 handler
    next();
  };
```

## 异步中间件的错误传递

```ts
// ✅ 异步中间件抛错必须进 next,否则错误中间件收不到
app.use(async (req, res, next) => {
  try { req.user = await loadUser(req); next(); }
  catch (err) { next(err); }
});
```

## 反模式
- ❌ 校验/鉴权放在路由 handler 之后 — 未授权请求已触达业务甚至落库。
- ❌ 错误中间件写在路由之前 — Express 永不进入,错误裸奔成 500 无格式。
- ❌ 异步中间件抛错不 `next(err)` — 请求挂起直到超时,错误中间件失效。
- ❌ 中间件里 `await ledger.debit()` 做结算 — 横切层混业务,不可测、顺序脆弱。
- ❌ 每个路由重复写鉴权 `if` — 抽成 `authorize()` 中间件复用。
