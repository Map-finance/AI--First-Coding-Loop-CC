---
name: financial-numerics
description: 涉及金额、价格、余额、交易的改动时的数值安全提示——金额禁用浮点（用整数最小单位或定点 BigInt/Decimal）、token decimals 按各自读取不硬编码、明确舍入方向。
when_to_use: 改动涉及金额/价格/余额/手续费/利率/token 数量计算时。
when_NOT_to_use: 与金额无关的改动（这是轻量提示 skill，不要泛用）。
---

# Skill: 金融数值安全（轻量提示）

金融产品里一个精度 bug = 直接资损。涉及金额时务必：

1. **禁用浮点表示金额**：永不用 float/double/JS Number。用整数最小单位（如 wei/分）或定点 BigInt/BigNumber/Decimal。
2. **decimals 不硬编码**：不同 token/币种精度不同（USDC 6、WBTC 8、WETH 18）；按各自 `decimals` 读取换算，禁止默认 18。
3. **明确舍入方向**：每处除法/换算显式声明舍入方式，且朝对系统保守的方向取整，避免被"舍入红利"反复套利。
4. **单位一致**：内部全程用最小单位，仅展示层换算。

## 反模式
- ❌ `const total = price * 0.1`（浮点）
- ❌ `amount / 1e18`（硬编码 18 decimals）
- ❌ 未声明舍入，默认银行家舍入导致对账差异
