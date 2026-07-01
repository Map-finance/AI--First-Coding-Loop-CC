---
name: financial-numerics
description: 涉及金额、价格、余额、交易、token数量的改动时的数值安全规范——禁用浮点，Go用Decimal18+Dec两类型，token.Decimals来自DB不硬编码，明确舍入方向。
when_to_use: 改动涉及金额/价格/余额/手续费/利率/token数量计算，或前端展示金额时。
when_NOT_to_use: 与金额无关的改动（这是轻量提示 skill，不要泛用）。
---

# Skill: 金融数值安全

金融产品里一个精度 bug = 直接资损。

## 通用规则

1. **禁用浮点** — 永不用 float/double/JS Number 表示金额
2. **decimals 来自 DB** — 不同 token 精度不同（USDC=6、WBTC=8、ETH=18）；从 `tokens.decimals` 字段读取，禁止硬编码
3. **明确舍入方向** — 每处除法/换算显式声明舍入，且朝对系统保守的方向取整
4. **单位一致** — 内部全程用最小单位，仅展示层换算

## Go 实现（Decimal18 + Dec）

两个类型，职责严格分离：

| 类型 | 用途 | 限制 |
|------|------|------|
| `money.Decimal18` | 存储/边界，scale 恒=18 | 只做加减，不能乘除 |
| `money.Dec` | 中间计算，全精度 | 乘除后必须 `Quantize18(mode)` 收敛 |

```go
// ✅ 边界入境：任意 token → 内部 Decimal18
token, _ := tokenRepo.Get(ctx, tokenID)           // token.Decimals 来自 DB
internal := money.FromMinorUnits(raw, token.Decimals)

// ✅ 中间计算用 Dec
fee := order.Amount.ToDec().Mul(feeRate)          // Dec 做乘法
settled := fee.Quantize18(decimal.RoundFloor)     // 朝对系统保守方向取整，收回 Decimal18

// ✅ 边界出境：Decimal18 → 链上原始单位
onChain := settled.ToMinorUnits(token.Decimals)
```

**golangci-lint forbidigo 已配置，违反以下规则 CI 直接拦截：**
- ❌ `decimal.NewFromFloat(...)` — 禁止，用 `decimal.NewFromString`
- ❌ `amount / 1e18` — 硬编码 decimals
- ❌ `float64(amount)` — 浮点转换

## 前端（React）

```ts
// ✅ API 返回 string，前端用 BigInt 或专用库展示
const display = formatTokenAmount(apiResponse.amount, token.decimals)

// ❌ 禁止
const price = parseFloat(response.price) * quantity  // 浮点运算
```

## 反模式速查
- ❌ `const total = price * 0.1`（浮点）
- ❌ `amount / 1e18`（硬编码 18 decimals）
- ❌ `Decimal18` 直接乘除（应先 `.ToDec()`）
- ❌ 未调 `Quantize18` 就存 DB（精度溢出）
- ❌ 未声明舍入方向（默认银行家舍入导致对账差异）
