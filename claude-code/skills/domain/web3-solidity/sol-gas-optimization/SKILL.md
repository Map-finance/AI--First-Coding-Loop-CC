---
name: sol-gas-optimization
pack: domain:web3-solidity
description: Solidity gas 优化——storage 槽打包、循环内避免 SLOAD/SSTORE、短路求值、calldata 替代 memory、批量操作、事件替代 storage 存储。
when_to_use: 编写或审查高频调用/循环/大数组/结构体的合约,或 gas profiling 后要压成本时。
when_NOT_to_use: 一次性部署脚本、可读性优先的原型,或牺牲安全/正确性去省 gas(安全永远优先)。
---

# Skill: Solidity Gas 优化

storage 操作是最贵的(SSTORE 冷写 22100 gas)。优化不得损害正确性与安全。

## 强制规则

1. **storage 布局打包** — 同槽(32字节)内合并小类型;`uint128+uint128`、`uint64+address+bool` 共槽,顺序相邻才生效。
2. **循环内禁反复 SLOAD/SSTORE** — 把 storage 变量读进 memory 局部量,循环结束一次写回。
3. **短路求值** — `&&`/`||` 把便宜/最可能失败的条件放前,省掉后续昂贵计算。
4. **外部函数参数用 calldata** — 只读数组/bytes 用 `calldata` 而非 `memory`,省一次拷贝。
5. **优先批量** — 批处理函数摊薄固定开销;但循环体内不得含外部转账(与 sol-security DoS 冲突)。
6. **事件替代 storage** — 只供链下索引、链上逻辑不再读的数据,用 `event` 记录,不写 storage。

## 关键实现

```solidity
// ✅ 打包:两个 uint128 共用一个槽
struct Position { uint128 collateral; uint128 debt; }   // 1 slot,而非 2

// ✅ 循环把 storage 提到 memory,末尾一次写回
function sum(uint256[] calldata xs) external {           // calldata 只读
    uint256 acc = total;                                 // 1 次 SLOAD
    for (uint256 i; i < xs.length; ++i) acc += xs[i];    // 循环内纯 memory
    total = acc;                                         // 1 次 SSTORE
}
```

## 反模式
- ❌ 循环内 `total += xs[i]` 直接改 storage — 每轮一次 SSTORE。
- ❌ `struct { bool a; uint256 b; bool c; }` — 布尔各占一槽,浪费两槽。
- ❌ 外部函数 `function f(uint[] memory a)` 只读却用 memory — 多一次拷贝。
- ❌ 把仅链下要读的数据写进 storage 而非 emit event。
- ❌ `require(expensiveCheck() && cheapCheck())` — 昂贵项放前,失败也白算。

## 判定标准
- 循环体内对同一 storage 变量重复读写,可提 memory 却未提 → 建议改。
- 相邻小类型字段未按位宽排序打包 → 建议改。
- 只读 external 参数用 `memory` → 建议改 `calldata`。
