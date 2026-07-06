---
name: sol-arithmetic-safety
pack: domain:web3-solidity
description: Solidity 算术安全——0.8 内建溢出检查、unchecked 的正确边界、定点/精度、除法先乘后除、避免精度损失。金额纪律见 financial-numerics,本 skill 只写 Solidity 算术特有面。
when_to_use: 编写或审查含乘除、比例、利率、定点数、unchecked 块或跨精度换算的合约逻辑。
when_NOT_to_use: 无算术的纯转发/权限/事件逻辑;通用「禁浮点/decimals 来自配置/舍入方向」由 financial-numerics 承担,勿在此重复。
---

# Skill: Solidity 算术安全

Solidity 无浮点,整数除法向零截断,一次误序 = 系统性精度流失或溢出。
金额的通用纪律(禁浮点、明确舍入、单位一致)见 `financial-numerics`;此处只讲 Solidity 层。

## 强制规则

1. **依赖 0.8 内建检查** — pragma ≥0.8 溢出自动 revert;不得为省 gas 盲目 `unchecked` 关掉保护。
2. **unchecked 有边界证明** — 仅当能静态证明不溢出(如循环计数 `++i`、已 require 过的减法)才用,并注释理由。
3. **先乘后除** — `a * b / c`,禁止 `a / c * b`(先除截断丢精度)。
4. **定点用高 scale** — 比例/利率用 `1e18`(WAD)或 `1e27`(RAY)定点表示,乘后按 scale 归一。
5. **除法舍入方向显式** — 涉及资产的除法明确朝对协议保守方向取整(见 financial-numerics 的舍入纪律)。
6. **除零前置校验** — 分母来自输入/状态时先 `require(denom != 0)`,给出可读 revert。

## 关键实现

```solidity
uint256 constant WAD = 1e18;

// ✅ 先乘后除,WAD 定点算比例
function shareOf(uint256 amount, uint256 rateWad) internal pure returns (uint256) {
    return (amount * rateWad) / WAD;      // 先乘再除,精度不丢
}

// ✅ unchecked 仅用于已证明安全的自增,附理由
for (uint256 i; i < n;) {
    // ... body ...
    unchecked { ++i; }                    // i < n 上界保证,永不溢出
}
```

## 反模式
- ❌ `amount / total * reward` — 先除截断,结果偏小甚至为 0。
- ❌ `unchecked { a - b }` 未先 `require(a >= b)` — 下溢绕过保护成天文数字。
- ❌ 用 `uint8`/低 scale 存比例 — 精度不足,舍入误差累积。
- ❌ `x / y` 未校验 `y != 0` — panic revert,无上下文难排查。
- ❌ 为省 gas 把整段业务算术包 `unchecked` — 溢出静默发生。

## 判定标准
- 出现「先除后乘」且两者都是变量 → BLOCK。
- `unchecked` 块内的减法/乘法无静态上界证明或前置 require → BLOCK。
- 比例/利率用整数直算而非定点 scale → 建议改。
