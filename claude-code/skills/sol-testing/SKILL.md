---
name: sol-testing
pack: domain:web3-solidity
description: 智能合约测试规范——Foundry/Hardhat、fuzz/invariant 测试、fork 测试、价格预言机操纵与闪电贷攻击场景、覆盖率门槛。
when_to_use: 为合约写测试、新增涉及资金/预言机/外部协议的逻辑、review 阶段检查合约测试质量。
when_NOT_to_use: 纯脚本/部署配置改动;通用测试纪律(测行为非实现、避免脆弱测试)见 testing-standards,勿在此重复。
---

# Skill: 合约测试

链上不可回滚,测试是最后防线。通用测试原则见 `testing-standards`,此处只讲合约特有面。

## 强制规则

1. **fuzz 覆盖数值边界** — 金额/比例/时间等输入用 fuzz(`forge` 默认属性测试)扫 0、max、溢出边界,不只测魔法值。
2. **invariant 守恒量** — 对协议不变量(如 `sum(balances) == totalSupply`、抵押率 ≥ 阈值)写 invariant 测试,让 fuzzer 随机序列攻击。
3. **fork 测试真实依赖** — 与外部协议/预言机交互的逻辑用主网 fork 测,别 mock 掉真实行为。
4. **必测攻击场景** — 显式编写重入、闪电贷、预言机操纵的攻击测试,断言协议不被套利/掏空。
5. **预言机取价用 TWAP/多源** — 测试证明单笔大额 swap 无法操纵价格喂给协议(现货价可被闪电贷瞬间拉偏)。
6. **覆盖率门槛** — 关键合约行/分支覆盖有下限(如 ≥90%),CI 用 `forge coverage` 卡关。

## 关键实现

```solidity
// ✅ Foundry fuzz + invariant
function testFuzz_deposit(uint96 amount) public {
    vm.assume(amount > 0);
    vault.deposit(amount);
    assertEq(vault.balanceOf(user), amount);   // 任意 amount 都成立
}

function invariant_solvency() public {
    assertGe(token.balanceOf(address(vault)), vault.totalDeposits());  // 永不资不抵债
}

// ✅ 闪电贷操纵预言机的攻击测试
function test_flashloanCannotDrain() public {
    vm.expectRevert("price manipulated");       // 断言防线生效
    attacker.flashloanAttack(1_000_000e18);
}
```

## 反模式
- ❌ 只用固定值断言,不 fuzz 边界(0/max/溢出临界漏测)。
- ❌ mock 掉预言机/外部协议后声称"集成已测"——未跑 fork。
- ❌ 无 invariant 测试,守恒被破坏无人发现。
- ❌ 用现货 `getReserves()` 直接喂价且无操纵攻击测试。
- ❌ 覆盖率无门槛,关键分支(revert/边界)未覆盖。

## 判定标准
- 涉及资金的合约无 invariant 测试 → BLOCK。
- 取价来自现货且无闪电贷操纵攻击测试 → BLOCK。
- 与外部协议交互却全 mock、无 fork 测试 → 建议补。
