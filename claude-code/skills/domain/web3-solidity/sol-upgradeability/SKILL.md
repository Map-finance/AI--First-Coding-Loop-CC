---
name: sol-upgradeability
pack: domain:web3-solidity
description: 可升级合约规范——UUPS/Transparent 代理模式、storage 布局冲突防护、initializer 替代 constructor、__gap 预留、升级授权与审计。
when_to_use: 编写或审查代理合约、可升级实现、新增 storage 变量、编写 upgrade 脚本,或评审一次合约升级。
when_NOT_to_use: 不可变(non-upgradeable)合约;纯逻辑改动且不触碰 storage 布局与代理机制。
---

# Skill: 合约可升级性

代理把 storage 与逻辑分离,一次布局错位就把用户余额读成别的槽。以下 BLOCK 级。

## 强制规则

1. **initializer 替代 constructor** — 实现合约的初始化逻辑放 `initialize()` 且加 `initializer` 修饰;constructor 里只 `_disableInitializers()`。
2. **storage 只追加不重排** — 已部署实现的状态变量顺序/类型不可改、不可插入、不可删除;新变量只能追加到末尾。
3. **__gap 预留** — 可被继承的可升级基类末尾留 `uint256[N] private __gap;`,给未来变量让出槽位,防子类布局被挤。
4. **升级授权** — UUPS 必须实现 `_authorizeUpgrade` 并加权限(onlyOwner/多签/timelock),否则任何人可替换实现。
5. **升级前跑布局 diff** — 用工具(如 OZ upgrades / storage layout 对比)校验新旧布局兼容,再上链。
6. **禁在实现合约里用不可变 state 假设** — 逻辑合约不持有 storage;常量用 `constant/immutable`,业务状态全走代理槽。

## 关键实现

```solidity
contract Vault is UUPSUpgradeable, OwnableUpgradeable {
    uint256 public totalDeposits;         // 槽 0,升级时顺序不可动
    // 新增变量只能加在这一行之后 ▼

    constructor() { _disableInitializers(); }   // 实现合约禁止被初始化

    function initialize(address owner_) external initializer {
        __Ownable_init(owner_);
        __UUPSUpgradeable_init();
    }

    function _authorizeUpgrade(address) internal override onlyOwner {}  // 升级鉴权

    uint256[49] private __gap;             // 预留槽,防后续布局冲突
}
```

## 反模式
- ❌ 可升级实现里写 `constructor(uint x) { total = x; }` — 代理 delegatecall 不执行 constructor,状态永远为 0。
- ❌ 在已上线实现的 storage 变量中间插入新字段 — 后续所有槽错位,读到脏数据。
- ❌ UUPS 未实现/空实现 `_authorizeUpgrade` 却不加权限 — 任意人升级劫持合约。
- ❌ 可继承基类末尾无 `__gap` — 子类新增变量与父类未来变量撞槽。
- ❌ 升级直接上链未做 storage layout diff。

## 判定标准
- 可升级合约有非空 constructor 初始化 state → BLOCK。
- `_authorizeUpgrade` 缺失或无访问控制 → BLOCK。
- storage 变量被插入/重排/删除(非末尾追加) → BLOCK。
