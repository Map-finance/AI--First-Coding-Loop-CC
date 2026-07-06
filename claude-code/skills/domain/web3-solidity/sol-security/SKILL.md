---
name: sol-security
pack: domain:web3-solidity
description: Solidity 合约安全审查——重入(CEI+ReentrancyGuard)、访问控制、禁 tx.origin 鉴权、低级 call 必查返回值、DoS、delegatecall 上下文风险。
when_to_use: 编写或审查含转账、外部调用、权限、delegatecall、代付/批处理的合约；review 阶段 security 趟。
when_NOT_to_use: 纯 view/pure 且无外部调用无状态写的函数；纯前端/脚本改动。
---

# Skill: Solidity 合约安全

链上代码不可回滚，一个漏洞 = 全部 TVL 归零。以下每条 BLOCK 级。
应用级通用安全(注入/鉴权≠授权/密钥/日志脱敏)见 `secure-coding`,本 skill 只写链上特有面。

## 强制规则

1. **CEI 顺序** — Checks → Effects → Interactions；状态写在外部调用之前,杜绝重入窗口。
2. **ReentrancyGuard 兜底** — 涉及转账/回调的外部函数加 `nonReentrant`,与 CEI 双保险。
3. **禁 `tx.origin` 鉴权** — 权限判断只用 `msg.sender`;`tx.origin` 会被中间合约钓鱼绕过。
4. **低级 call 必查返回值** — `call/delegatecall/send` 失败不 revert,必须显式检查 `(bool ok, )` 并处理。
5. **拉取优于推送** — 批量分发用户主动 `withdraw`,禁止循环内向外部地址转账(单点 revert 卡死全体 = DoS)。
6. **delegatecall 上下文** — 被 delegatecall 的库不得有自身 storage 布局假设,且目标地址必须可信/不可变。

## 关键实现

```solidity
// ✅ CEI + nonReentrant:先清账,再打钱
function withdraw() external nonReentrant {
    uint256 amount = balances[msg.sender];
    require(amount > 0, "nothing");
    balances[msg.sender] = 0;                 // Effects 先行
    (bool ok, ) = msg.sender.call{value: amount}("");  // Interaction 最后
    require(ok, "transfer failed");           // 低级 call 必查返回值
}

// ✅ 权限用 msg.sender,不用 tx.origin
modifier onlyOwner() { require(msg.sender == owner, "not owner"); _; }
```

## 反模式
- ❌ `msg.sender.call{value: v}(""); balances[msg.sender] = 0;` — 先打钱后清账,经典重入。
- ❌ `require(tx.origin == owner)` — 可被钓鱼合约绕过。
- ❌ `payable(to).call{value: v}("");` 丢弃返回值 — 静默失败。
- ❌ `for (...) recipients[i].transfer(x)` — 任一地址 revert 即全员卡死(DoS);改拉取模式。
- ❌ delegatecall 到用户可控地址 — 等于交出合约 storage 与余额控制权。

## 判定标准
- 有 `.call{value:}`/`transfer`/外部回调却无 `nonReentrant` 且状态写在调用后 → BLOCK。
- 出现 `tx.origin ==`/`tx.origin !=` 用于授权 → BLOCK。
- 低级 `call/delegatecall` 返回值未接收或未 require → BLOCK。
