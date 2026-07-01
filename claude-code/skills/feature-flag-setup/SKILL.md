---
name: feature-flag-setup
description: 给一个新功能加一个完整的特性开关——登记 flag、设保守默认值、依赖注入而非吃单例、配灰度规则、文档化 kill switch、合并前写一条证明 kill 生效的测试。每个新功能上线前必走。
when_to_use: implementer agent 收到带 flag 约束的任务时；架构师任务模板提到新 flag 时；或 review 阶段发现 PR 没把功能藏在开关后时。
when_NOT_to_use: 改的是已有 flag 的灰度参数（那是 ops 动作，不走 PR）。
---

# Skill: Feature Flag Setup

每个新功能**必须**藏在特性开关后——这是 harness 的"可反悔权"。

> 本 skill 描述**语言无关的原则与步骤**。下方代码块是 TypeScript 参考实现，
> 其他技术栈（Go / Python / Java 等）遵循同样步骤，用本栈的等价写法。
> 具体的 flag 登记文件路径、配置约定见本项目 CLAUDE.md。

## 步骤（原子动作，不可省略）

### 1. 登记 flag

在本项目的 flag 登记表里加一个新 key，**默认值务必保守（关闭）**——fail-safe：即使配置缺失，功能也是关的。

> 示例（TypeScript，其他栈用等价的常量表 + 默认值映射）：
> ```ts
> export const FLAGS = {
>   NEW_GREETING: 'new_greeting',   // key 用 snake_case
> } as const;
>
> const FLAG_DEFAULTS = {
>   [FLAGS.NEW_GREETING]: false,    // 默认务必 false
> };
> ```

### 2. 业务代码用依赖注入，不要直接吃 flag 单例

直接调用全局 flag 单例会让测试无法覆盖开/关两条分支。应让服务/组件**接收** flag 查询能力（`isEnabled` / `getVariant`），生产环境由启动入口注入真实实现。

- ❌ 业务函数内部 `if (globalFlags.isEnabled(X))` —— 测试无法注入
- ✅ 依赖从外部传入，测试可注入假 provider 覆盖两条分支

### 3. 配灰度规则

按本项目的配置机制设置分环境灰度（dev 全开、prod 小流量起步）。若项目用"多份环境模板 KEY 必须一致"的校验（如 CI env-parity），确保各份模板都加了该 key。

> 示例（每环境一份配置，值不同）：
> ```
> # dev
> FLAG_new_greeting = { enabled: true,  rolloutPct: 100 }
> # prod
> FLAG_new_greeting = { enabled: true,  rolloutPct: 5 }
> ```

### 4. 在 PR 描述里写明灰度计划

```
## Feature flag
- Key: NEW_GREETING
- Default: false (fail-safe)
- 灰度: teamOnly → 5% → 25% → 100%（每档观察 24h）
- Kill switch: 把该 flag 置为 disabled（无需重新部署）
- 观测指标: <CTR / 转化 / 错误率等>
```

### 5. 验收（PR 合之前）：写一行测试证明 kill 起作用

注入"关闭"状态，断言功能确实不生效。

> 示例（TypeScript / 任意测试框架，其他栈同理）：
> ```ts
> test('kill switch turns the feature off', async () => {
>   const provider = fakeProvider({ NEW_GREETING: { enabled: false } });
>   expect(await provider.isEnabled('new_greeting')).toBe(false);
> });
> ```

## 托管 flag 平台（可选，项目特定）

Day 0 用本地 provider（配置文件 / 环境变量）就够。团队变大或需要可视化看板时，
可接入托管平台（LaunchDarkly / Statsig / Unleash / GrowthBook 等）——业务代码因为走了
依赖注入（步骤 2），切换 provider 时零改动。具体选型见本项目 CLAUDE.md / tech-stack。

## 反模式

- ❌ flag 默认开启——失去 fail-safe
- ❌ flag 直接吃全局单例、不注入——测试覆不到
- ❌ kill 步骤写"redeploy"——失去"无需部署即时关闭"的能力
- ❌ 灰度配置在某个环境模板漏了 key——配置校验会拦你（若项目启用）
