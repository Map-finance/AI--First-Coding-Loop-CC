# 规范 Skill 体系与三层加载 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 AIFCL 脚手架仓内新增一套"判断层"开发规范 skill，并把它们通过三层机制（描述驱动自动触发 + CLAUDE.md/required_skills 强制 + hook 提醒）强制加载到每个同事的 agent，配套一个幂等的 skill 安装脚本。

**Architecture:** 全部为新增文件（`claude-code/skills/<name>/SKILL.md`）+ 少量增量修改既有文件（`implementer.toml`、`CLAUDE.md.template`、`install.sh`、`skills/README.md`）。规范分两层：能机器判定的交给 linter/CI（不在本 plan），需要判断的写成 skill。每个 skill 开发期用于"做对"、评审期被 Plan B 的评审 prompt 引用用于"挑错"。

**Tech Stack:** Markdown（SKILL.md，frontmatter: name/description/when_to_use/when_NOT_to_use）+ TOML（agent）+ Bash（install/ensure_skills）+ JSON（.claude/settings.json hook）

---

## File Structure

新增 skill（`claude-code/skills/<name>/SKILL.md`）：
- `sql-optimization/` — SQL/ORM 查询优化（索引、N+1、全表、分页）
- `secure-coding/` — 注入/越权/密钥/PII 等代码级安全判断
- `performance-review/` — 性能 + 韧性 + 可观测性（超时/重试/熔断/幂等/限流/埋点/日志）
- `financial-numerics/` — 金额/数值轻量提示（金融产品专用）
- `naming-convention/` — 命名语义
- `commenting/` — 注释解释 why
- `design-patterns/` — 设计模式取舍、防过度设计
- `clean-code/` — 函数职责单一、抽象层级、去重
- `testing-standards/` — 测什么、边界、不测实现细节
- `api-doc-output/` — 改接口时同步产出 `docs/api`
- `data-model-output/` — 改数据模型时同步产出 `docs/data-model`

修改既有文件：
- `claude-code/agents/implementer.toml` — 扩展 `required_skills` / `optional_skills`
- `claude-code/CLAUDE.md.template` — 新增"规范 skill 强制加载"段
- `claude-code/skills/README.md` — 登记新 skill
- `tools/install.sh` — 调用 ensure_skills + 分发 `.claude/settings.json`

新增机制文件：
- `claude-code/settings.json.template` — UserPromptSubmit hook（skill 提醒）
- `tools/ensure_skills.sh` — 幂等安装 superpowers + 校验团队 skill

---

## Task 1: 建立 skill 编写基线 + sql-optimization skill

**Files:**
- Create: `claude-code/skills/sql-optimization/SKILL.md`

- [ ] **Step 1: 创建 sql-optimization skill（内容即产物，给出完整内容）**

```markdown
---
name: sql-optimization
description: 审查与编写数据库查询时避免性能陷阱——确保命中索引、消除 N+1、禁止全表扫描与 SELECT *、强制分页、控制事务范围。涉及 SQL/ORM 的改动必走。
when_to_use: implementer 写涉及数据库查询/ORM 的代码时；review 阶段 PR 触及 SQL、Repository、DAO、迁移脚本时。
when_NOT_to_use: 纯前端、纯文档、与持久层无关的改动。
---

# Skill: SQL / 查询优化

数据库是大多数后端性能与故障的根源。改动任何查询前后，逐条核对下面规则。

## 必查规则
1. **命中索引**：WHERE/JOIN/ORDER BY 涉及的列必须有索引；新查询若无可用索引，要么加索引迁移，要么说明为何不需。
2. **消除 N+1**：循环里查库 = N+1。用 JOIN / IN 批量 / ORM 的 eager load（如 `select_related`/`Include`/`Preload`）一次取回。
3. **禁止全表扫描**：无 WHERE 或 WHERE 不走索引的大表查询，BLOCK。用 EXPLAIN 验证执行计划。
4. **禁止 `SELECT *`**：只取需要的列，减少 IO 与序列化开销。
5. **强制分页**：列表查询必须有 LIMIT/OFFSET 或游标分页；禁止一次取回无界结果集。
6. **事务范围最小**：事务内不做网络调用/外部 IO；长事务持锁会拖垮并发。
7. **参数化**：永不字符串拼接 SQL（注入风险，见 secure-coding）。

## 正例 / 反例
- ❌ `for id in ids: db.query("... WHERE x=?", id)` → ✅ `db.query("... WHERE x IN (?)", ids)`
- ❌ `SELECT * FROM orders` → ✅ `SELECT id, status FROM orders WHERE user_id=? LIMIT 50`

## 反模式
- ❌ 用 ORM 默认懒加载遍历关联对象（隐形 N+1）
- ❌ 在事务里 `await httpClient.call()`
- ❌ 加索引却忘了写迁移脚本
```

- [ ] **Step 2: 验证文件存在且 frontmatter 完整**

Run: `head -6 claude-code/skills/sql-optimization/SKILL.md && grep -c '^when_NOT_to_use:' claude-code/skills/sql-optimization/SKILL.md`
Expected: 打印前 6 行，且 `when_NOT_to_use:` 计数为 1

- [ ] **Step 3: Commit**

```bash
git add claude-code/skills/sql-optimization/SKILL.md
git commit -m "feat(skills): add sql-optimization skill"
```

---

## Task 2: secure-coding skill

**Files:**
- Create: `claude-code/skills/secure-coding/SKILL.md`

- [ ] **Step 1: 创建文件（完整内容）**

```markdown
---
name: secure-coding
description: 审查与编写代码时的应用级安全判断——参数化输入、鉴权与授权分离、越权(IDOR)零容忍、密钥不入代码、日志不泄露 PII/凭证、防 SSRF/CSRF/不安全反序列化。
when_to_use: 任何处理用户输入、鉴权授权、外部请求、序列化、日志输出的改动；review 阶段 security 趟。
when_NOT_to_use: 纯样式/文案/与数据流无关的改动。
---

# Skill: 安全编码

钱与信任在这里被摧毁。下面每条都是 BLOCK 级。

## 必查规则
1. **注入**：用户输入到 SQL/shell/模板/表达式一律参数化或转义，禁止拼接。
2. **鉴权 ≠ 授权**：登录(鉴权)和"能否操作这条资源"(授权)分开判。新端点默认必须鉴权。
3. **越权(IDOR)零容忍**：用资源 owner 校验，不能仅凭前端传的 id 就返回数据。
4. **密钥**：绝不硬编码 token/私钥；用环境变量 + secrets 管理。
5. **日志/响应脱敏**：不打印 PII、凭证、完整卡号、私钥、签名原文。
6. **SSRF**：对用户可控的出站 URL 做白名单/网段校验。
7. **反序列化**：不反序列化不可信数据为可执行对象。

## 反模式
- ❌ `f"SELECT ... WHERE name='{name}'"`
- ❌ `if user.is_logged_in: return order`（缺 owner 校验 → IDOR）
- ❌ `logger.info(f"token={token}")`
- ❌ 把密钥写进 .env 并提交入库
```

- [ ] **Step 2: 验证**

Run: `grep -c '^name: secure-coding' claude-code/skills/secure-coding/SKILL.md`
Expected: 1

- [ ] **Step 3: Commit**

```bash
git add claude-code/skills/secure-coding/SKILL.md
git commit -m "feat(skills): add secure-coding skill"
```

---

## Task 3: performance-review skill（性能 + 韧性 + 可观测性）

**Files:**
- Create: `claude-code/skills/performance-review/SKILL.md`

- [ ] **Step 1: 创建文件（完整内容，覆盖团队真实痛点）**

```markdown
---
name: performance-review
description: 审查与编写代码时的性能、韧性与可观测性判断——外部调用必须有超时/重试退避/熔断降级/幂等、接口限流与分页、缓存正确性、并发安全与资源释放、结构化日志与异常埋点。
when_to_use: 涉及外部接口调用、并发/异步、缓存、热路径、日志与监控的改动；review 阶段 performance 趟。
when_NOT_to_use: 纯静态文案、与运行时行为无关的改动。
---

# Skill: 性能 / 韧性 / 可观测性

这是团队历史上最常踩的坑，下面标 ⛔ 的为 BLOCK 级。

## 韧性（外部依赖）
1. ⛔ **超时**：所有外部调用（HTTP/RPC/DB/缓存）必须设显式超时，禁止无限等待。
2. ⛔ **重试 + 退避**：可重试错误用指数退避 + 抖动；不可重试错误不重试。
3. **熔断 / 降级**：依赖持续失败时熔断，提供降级路径，避免级联失败。
4. ⛔ **幂等**：写操作/回调要幂等（用幂等键），防重试导致脏数据。
5. ⛔ **限流**：对外暴露的接口要有速率限制；调用第三方要遵守其限流。

## 性能
6. 热路径避免重复计算/分配；列表查询强制分页（见 sql-optimization）。
7. 缓存：注意击穿/穿透/雪崩；设过期与空值占位。
8. 前端：避免不必要重渲染、控制 bundle 体积、长列表虚拟化、清理订阅防内存泄漏。

## 并发
9. 共享状态加锁或用无锁结构；异步必须 await/处理；释放连接/文件/句柄。

## 可观测性
10. ⛔ **结构化日志**：JSON，含 `service`/`request_id`/`level`；不打 PII。
11. ⛔ **异常埋点**：关键路径异常必须上报监控（不吞异常、错误分级）。
12. 提供健康检查与关键业务指标。

## 反模式
- ❌ `fetch(url)` 不带 timeout / `httpClient` 用默认无限超时
- ❌ catch 后 `pass` / 空 catch 吞掉异常
- ❌ `print()` 或非结构化日志
- ❌ 重试非幂等的写操作
```

- [ ] **Step 2: 验证**

Run: `grep -c '⛔' claude-code/skills/performance-review/SKILL.md`
Expected: 数字 ≥ 6（确认 BLOCK 级条目已写入）

- [ ] **Step 3: Commit**

```bash
git add claude-code/skills/performance-review/SKILL.md
git commit -m "feat(skills): add performance-review skill (perf+resilience+observability)"
```

---

## Task 4: financial-numerics skill（金融产品轻量提示）

**Files:**
- Create: `claude-code/skills/financial-numerics/SKILL.md`

- [ ] **Step 1: 创建文件（完整内容，保持轻量）**

```markdown
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
```

- [ ] **Step 2: 验证**

Run: `grep -c '^name: financial-numerics' claude-code/skills/financial-numerics/SKILL.md`
Expected: 1

- [ ] **Step 3: Commit**

```bash
git add claude-code/skills/financial-numerics/SKILL.md
git commit -m "feat(skills): add financial-numerics lightweight skill"
```

---

## Task 5: naming-convention + commenting skill

**Files:**
- Create: `claude-code/skills/naming-convention/SKILL.md`
- Create: `claude-code/skills/commenting/SKILL.md`

- [ ] **Step 1: 创建 naming-convention（完整内容）**

```markdown
---
name: naming-convention
description: 审查与编写标识符命名——名字要表意（揭示意图与领域术语），与团队词汇表一致，避免缩写歧义与误导性命名。格式类规则（大小写）由 linter 管，本 skill 管语义。
when_to_use: 新增/重命名函数、变量、类型、模块、接口字段时；review 阶段 quality 趟。
when_NOT_to_use: 仅格式调整（交给 linter）。
---

# Skill: 命名语义

linter 管大小写格式，本 skill 管"名字是否表意"。

## 规则
1. 名字揭示意图：`elapsedSeconds` 优于 `t`；`isEligible` 优于 `flag`。
2. 用领域术语，与团队词汇表（见 docs）一致：同一概念全仓一个名字。
3. 避免误导：不要把返回 list 的函数命名为 `getUser`。
4. 布尔用 is/has/can 前缀；集合用复数。
5. 避免无意义缩写（`usr`/`tmp2`），除非是公认领域缩写。

## 反模式
- ❌ `data`/`info`/`manager`/`process` 这类空泛名
- ❌ 同一概念在不同模块叫 `userId` 和 `uid`
```

- [ ] **Step 2: 创建 commenting（完整内容）**

```markdown
---
name: commenting
description: 审查与编写注释——注释解释"为什么"（决策、权衡、陷阱）而非复述"做什么"；公共 API 有用途说明；删除注释掉的死代码。
when_to_use: 新增/修改有非显然逻辑、权衡决策、外部约束的代码时；review 阶段 quality 趟。
when_NOT_to_use: 自解释的简单代码不必强加注释。
---

# Skill: 注释质量

## 规则
1. 注释解释 **why**：为什么这样做、放弃了什么方案、有什么坑。
2. 不复述 what：`i++ // 自增` 是噪音，删掉。
3. 公共函数/接口写用途、参数语义、副作用。
4. 标注非显然约束：外部 API 限制、并发假设、精度要求。
5. 删除注释掉的死代码（用 git 历史，不要留尸体）。

## 反模式
- ❌ `// 循环用户列表` 放在显然的 for 上面
- ❌ 大段被注释掉的旧实现
```

- [ ] **Step 3: 验证两文件**

Run: `for s in naming-convention commenting; do grep -c "^name: $s" claude-code/skills/$s/SKILL.md; done`
Expected: 两行都是 1

- [ ] **Step 4: Commit**

```bash
git add claude-code/skills/naming-convention/SKILL.md claude-code/skills/commenting/SKILL.md
git commit -m "feat(skills): add naming-convention and commenting skills"
```

---

## Task 6: design-patterns + clean-code + testing-standards skill

**Files:**
- Create: `claude-code/skills/design-patterns/SKILL.md`
- Create: `claude-code/skills/clean-code/SKILL.md`
- Create: `claude-code/skills/testing-standards/SKILL.md`

- [ ] **Step 1: 创建 design-patterns（完整内容）**

```markdown
---
name: design-patterns
description: 审查与设计代码结构——选择恰当的设计模式与抽象，避免过度设计（YAGNI），依赖倒置便于测试，保持模块边界清晰。
when_to_use: 新增模块/服务/较大组件、引入抽象或框架时；review 阶段 quality 趟。
when_NOT_to_use: 小改动、bug 修复。
---

# Skill: 设计模式与抽象

## 规则
1. **YAGNI**：不为假想的未来需求加抽象层；先简单，需要时再抽。
2. 依赖通过接口注入（便于测试与替换），不在业务里 new 具体依赖。
3. 模块边界清晰：一个模块一个职责，对外暴露窄接口。
4. 用恰当模式解决真实问题（策略/工厂/适配器…），不为用模式而用模式。

## 反模式
- ❌ 单一实现就上抽象工厂 + 一堆接口
- ❌ 上帝类 / 万能 util 模块
- ❌ 业务代码直接 new 数据库客户端（无法 mock）
```

- [ ] **Step 2: 创建 clean-code（完整内容）**

```markdown
---
name: clean-code
description: 审查与编写代码整洁度——函数职责单一且短小、控制圈复杂度与嵌套、消除重复(DRY)、统一抽象层级、删除死代码与魔法值。
when_to_use: 任何写码/重构；review 阶段 quality 趟。
when_NOT_to_use: 纯配置/文档。
---

# Skill: 代码整洁

## 规则
1. 函数职责单一、短小；超长函数拆分。
2. 控制嵌套深度，早返回替代深 if。
3. DRY：重复逻辑提取；但避免错误抽象（见 design-patterns 的 YAGNI）。
4. 同一函数内保持一致抽象层级。
5. 魔法值提为具名常量；删除死代码。

## 反模式
- ❌ 一个函数做校验+查库+计算+发通知
- ❌ `if (status == 3)` 魔法数字
```

- [ ] **Step 3: 创建 testing-standards（完整内容）**

```markdown
---
name: testing-standards
description: 审查与编写测试——覆盖边界与异常路径、测行为而非实现细节、避免脆弱测试、关键路径有集成/契约测试、测试可读。
when_to_use: 新增/修改功能时写测试；review 阶段 quality 趟检查测试质量。
when_NOT_to_use: 纯文档改动。
---

# Skill: 测试标准

## 规则
1. 覆盖正常 + 边界 + 异常路径（空、超大、并发、失败）。
2. 测**行为/契约**，不测私有实现细节（实现变测试不该碎）。
3. 避免脆弱测试：不依赖时间/顺序/外部网络（用 fake/mock）。
4. 关键路径必须有集成测试（见 CLAUDE.md 的 make test-integration）。
5. 测试名描述行为：`test_拒绝超额提现`。

## 反模式
- ❌ 只测 happy path
- ❌ 断言内部调用次数而非外部可观察结果
- ❌ 真连第三方 API 的"单测"
```

- [ ] **Step 4: 验证三文件**

Run: `for s in design-patterns clean-code testing-standards; do grep -c "^name: $s" claude-code/skills/$s/SKILL.md; done`
Expected: 三行都是 1

- [ ] **Step 5: Commit**

```bash
git add claude-code/skills/design-patterns/SKILL.md claude-code/skills/clean-code/SKILL.md claude-code/skills/testing-standards/SKILL.md
git commit -m "feat(skills): add design-patterns, clean-code, testing-standards skills"
```

---

## Task 7: api-doc-output + data-model-output skill（强制文档产出）

**Files:**
- Create: `claude-code/skills/api-doc-output/SKILL.md`
- Create: `claude-code/skills/data-model-output/SKILL.md`

- [ ] **Step 1: 创建 api-doc-output（完整内容）**

```markdown
---
name: api-doc-output
description: 改动 HTTP/RPC 接口时强制同步更新接口文档——在 docs/api（经 submodule 指向 docs-repo）记录路径、方法、入参/出参、错误码、鉴权要求。CI 会检查接口改了文档没改则拦。
when_to_use: 新增/修改/删除任何对外接口、请求或响应结构、错误码时。
when_NOT_to_use: 仅内部函数重构、不影响对外契约。
---

# Skill: 接口文档产出

改接口必须同步更新 `docs/<backend|frontend>/<svc>/api.md`，否则 CI 拦截。

## 每个接口需记录
1. 路径 + 方法 + 简述
2. 鉴权要求（是否需登录、需要的权限）
3. 入参（字段、类型、必填、约束）
4. 出参（成功结构）
5. 错误码与含义
6. 跨端共享的类型放 docs-repo 的 `contracts/`，前后端引用同一份

## 反模式
- ❌ 改了响应字段不更新文档（前端按旧契约对接 → 线上故障）
- ❌ 接口文档与 contracts/ 类型不一致
```

- [ ] **Step 2: 创建 data-model-output（完整内容）**

```markdown
---
name: data-model-output
description: 改动数据库表结构/数据模型时强制同步更新数据定义文档——在 docs/data-model 记录表/字段/类型/索引/约束/迁移说明。CI 会检查 DB 改了文档没改则拦。
when_to_use: 新增/修改表、字段、索引、约束、迁移脚本时。
when_NOT_to_use: 不涉及持久层结构的改动。
---

# Skill: 数据定义产出

改数据模型必须同步更新 `docs/<backend>/<svc>/data-model.md`。

## 每处变更需记录
1. 表用途 + 字段（名/类型/可空/默认/含义）
2. 索引（列、唯一性、用途）
3. 约束与外键
4. 迁移说明（是否可回滚、数据兼容性、是否需回填）

## 反模式
- ❌ 加字段不写文档与迁移说明
- ❌ 迁移脚本不可回滚却未标注
```

- [ ] **Step 3: 验证两文件**

Run: `for s in api-doc-output data-model-output; do grep -c "^name: $s" claude-code/skills/$s/SKILL.md; done`
Expected: 两行都是 1

- [ ] **Step 4: Commit**

```bash
git add claude-code/skills/api-doc-output/SKILL.md claude-code/skills/data-model-output/SKILL.md
git commit -m "feat(skills): add api-doc-output and data-model-output skills"
```

---

## Task 8: 在 skills/README.md 登记全部新 skill

**Files:**
- Modify: `claude-code/skills/README.md`（在"当前 skills"表格追加行）

- [ ] **Step 1: 在表格末尾（`weekly-comprehension-check` 行之后）追加 11 行**

把下列行插入到 README 表格的最后一行数据之后：

```markdown
| `sql-optimization` | 查询优化（索引/N+1/全表/分页） | implementer / review |
| `secure-coding` | 应用级安全判断 | implementer / review |
| `performance-review` | 性能+韧性+可观测性 | implementer / review |
| `financial-numerics` | 金额/数值安全（金融产品） | implementer |
| `naming-convention` | 命名语义 | implementer / review |
| `commenting` | 注释解释 why | implementer / review |
| `design-patterns` | 设计模式取舍/防过度设计 | implementer / review |
| `clean-code` | 整洁度/职责单一/去重 | implementer / review |
| `testing-standards` | 测试覆盖与质量 | implementer / review |
| `api-doc-output` | 改接口同步产出 docs/api | implementer |
| `data-model-output` | 改数据模型同步产出 docs/data-model | implementer |
```

- [ ] **Step 2: 验证**

Run: `grep -c 'implementer / review' claude-code/skills/README.md`
Expected: 7

- [ ] **Step 3: Commit**

```bash
git add claude-code/skills/README.md
git commit -m "docs(skills): register 11 governance skills in README"
```

---

## Task 9: 扩展 implementer.toml 强制挂载规范 skill（第 2 层加载）

**Files:**
- Modify: `claude-code/agents/implementer.toml:11-12`

- [ ] **Step 1: 替换 required_skills / optional_skills 两行**

把现有第 11-12 行：

```toml
required_skills = ["feature-flag-setup"] # 任何新功能强制走这个
optional_skills = ["api-endpoint-creator"]
```

替换为：

```toml
# 任何改动都强制挂载的规范底线（开发期"做对"）
required_skills = ["feature-flag-setup", "secure-coding", "clean-code", "testing-standards"]
# 按改动内容由 description 自动触发：涉及 SQL→sql-optimization、外部调用→performance-review、
# 金额→financial-numerics、接口→api-doc-output、数据模型→data-model-output 等
optional_skills = [
  "api-endpoint-creator", "sql-optimization", "performance-review", "financial-numerics",
  "naming-convention", "commenting", "design-patterns", "api-doc-output", "data-model-output",
]
```

- [ ] **Step 2: 验证 TOML 合法**

Run: `python3 -c "import tomllib; tomllib.load(open('claude-code/agents/implementer.toml','rb')); print('ok')"`
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add claude-code/agents/implementer.toml
git commit -m "feat(agents): implementer requires governance skills, lists optional ones"
```

---

## Task 10: 扩展 CLAUDE.md.template 写死规范加载硬规则（第 2 层）

**Files:**
- Modify: `claude-code/CLAUDE.md.template`（在第 76 行"### Skills"段后追加）

- [ ] **Step 1: 在 `### Skills(...)` 段落（第 75-77 行）之后插入新段**

在 CLAUDE.md.template 第 77 行（`新增 skill：在 skills/ 下建目录，登记到 skills/README.md。`）之后，插入：

```markdown

#### 规范 skill 强制加载（开发与评审的共同底线）
任何 agent 在以下情形**必须先 Read 对应 skill 再动手**（不是"自觉"，是硬规则）：
- 涉及 SQL/ORM/迁移 → `sql-optimization`
- 外部调用/并发/缓存/日志/监控 → `performance-review`
- 处理用户输入/鉴权/密钥/序列化 → `secure-coding`
- 金额/价格/余额/交易 → `financial-numerics`
- 改接口 → `api-doc-output`；改数据模型 → `data-model-output`
- 任何改动的底线：`clean-code` + `testing-standards` + 新功能 `feature-flag-setup`

这些 skill 同时被 PR 的 AI 评审引用（见 `.github/workflows/ai-review.yml`）。开发期漏掉的，评审期会拦。
```

- [ ] **Step 2: 验证**

Run: `grep -c '规范 skill 强制加载' claude-code/CLAUDE.md.template`
Expected: 1

- [ ] **Step 3: Commit**

```bash
git add claude-code/CLAUDE.md.template
git commit -m "feat(claude-md): add mandatory governance-skill loading rules"
```

---

## Task 11: settings.json hook 模板（第 3 层：主动提醒）

**Files:**
- Create: `claude-code/settings.json.template`

- [ ] **Step 1: 创建文件（完整内容）**

`UserPromptSubmit` hook 在每次任务进来时注入一段 skill 提醒（与本仓 brainstorming/TDD 提醒同款机制）。

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "printf '%s' '[skill-reminder] 按改动内容显式 Read 对应规范 skill：SQL→sql-optimization；外部调用/并发/日志→performance-review；用户输入/鉴权/密钥→secure-coding；金额/交易→financial-numerics；改接口→api-doc-output；改数据模型→data-model-output；新功能→feature-flag-setup；底线→clean-code + testing-standards。涉及才用，不涉及忽略。'"
          }
        ]
      }
    ]
  }
}
```

- [ ] **Step 2: 验证 JSON 合法**

Run: `python3 -c "import json; json.load(open('claude-code/settings.json.template')); print('ok')"`
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add claude-code/settings.json.template
git commit -m "feat(hooks): add UserPromptSubmit skill-reminder settings template"
```

---

## Task 12: ensure_skills.sh 幂等安装脚本

**Files:**
- Create: `tools/ensure_skills.sh`
- Test: `tools/ensure_skills.test.sh`

- [ ] **Step 1: 写失败测试**

```bash
#!/usr/bin/env bash
# tools/ensure_skills.test.sh — 验证幂等安装脚本的核心行为
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# 造一个假的 target 仓，预置 4 个团队 skill 但缺 superpowers
mkdir -p "$TMP/.claude/skills/secure-coding" "$TMP/.claude/skills/clean-code"
mkdir -p "$TMP/.claude/skills/testing-standards" "$TMP/.claude/skills/sql-optimization"

# 用 DRY_RUN 跑（不真正 git clone），断言它报告"superpowers 缺失、将安装"且"团队 skill 已存在、跳过"
OUT="$(DRY_RUN=1 bash "$SCRIPT_DIR/ensure_skills.sh" "$TMP" 2>&1)"
echo "$OUT" | grep -q 'superpowers: 缺失' || { echo "FAIL: 未检测到 superpowers 缺失"; exit 1; }
echo "$OUT" | grep -q 'secure-coding: 已存在' || { echo "FAIL: 未跳过已存在 skill"; exit 1; }
echo "PASS"
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `bash tools/ensure_skills.test.sh`
Expected: FAIL，报错 `ensure_skills.sh: No such file or directory`（脚本还没写）

- [ ] **Step 3: 写最小实现**

```bash
#!/usr/bin/env bash
# =============================================================================
# ensure_skills.sh — 幂等确保必备 skill 就位（团队规范 skill + superpowers）
# 用法: bash ensure_skills.sh <target-repo-dir>
# 环境: DRY_RUN=1 只检测与报告，不真正安装
# 设计: 已存在则跳过（"有了就不用"）；缺失才安装。
# =============================================================================
set -euo pipefail

TARGET="${1:?用法: bash ensure_skills.sh <target-repo-dir>}"
TARGET="$(cd "$TARGET" && pwd)"
DRY_RUN="${DRY_RUN:-0}"

say() { printf '\033[1;36m▶ %s\033[0m\n' "$*"; }
ok()  { printf '\033[1;32m✓ %s\033[0m\n' "$*"; }

# 团队规范 skill 随代码仓 .claude/skills/ 下发，这里只校验存在性
TEAM_SKILLS=(secure-coding clean-code testing-standards sql-optimization performance-review financial-numerics)

say "校验团队规范 skill"
missing_team=0
for s in "${TEAM_SKILLS[@]}"; do
  if [ -d "$TARGET/.claude/skills/$s" ] || [ -d "$TARGET/.codex/skills/$s" ]; then
    ok "$s: 已存在"
  else
    printf '\033[1;33m∅ %s: 缺失（应随仓下发，请检查 install.sh）\033[0m\n' "$s"
    missing_team=1
  fi
done

# superpowers：用户级或项目级任一存在即视为已装
say "检查 superpowers"
if [ -d "$HOME/.claude/skills/superpowers" ] || [ -d "$TARGET/.claude/skills/superpowers" ] \
   || [ -d "$HOME/.claude/plugins/superpowers" ]; then
  ok "superpowers: 已存在，跳过"
else
  echo "superpowers: 缺失"
  if [ "$DRY_RUN" = "1" ]; then
    echo "  (DRY_RUN) 将安装 superpowers"
  else
    echo "  请用官方方式安装（plugin marketplace 或 git clone 到 ~/.claude/skills/superpowers）。"
    echo "  落地时用 claude-code-guide 核实当前官方命令；本脚本不写死可能过期的命令。"
  fi
fi

[ "$missing_team" = "0" ] && ok "全部团队 skill 就位" || true
```

- [ ] **Step 4: 运行测试，确认通过**

Run: `bash tools/ensure_skills.test.sh`
Expected: `PASS`

- [ ] **Step 5: Commit**

```bash
chmod +x tools/ensure_skills.sh
git add tools/ensure_skills.sh tools/ensure_skills.test.sh
git commit -m "feat(tools): add idempotent ensure_skills.sh with test"
```

---

## Task 13: install.sh 集成 settings.json 分发 + ensure_skills 调用

**Files:**
- Modify: `tools/install.sh`（在 claude-code 分发块内 + 安装结尾）

- [ ] **Step 1: 在 CLAUDE.md 处理块后（install.sh 第 119-120 行 `fi` 之前）追加 settings.json 分发**

在 install.sh 第 119 行（`  fi`，即 CLAUDE.md 的 if 结束）之前、第 118 行 skip 语句之后，插入：

```bash
  # .claude/settings.json：仅在目标仓没有时装（含 skill-reminder hook）
  if [ ! -f "$TARGET/$CC_DIR/settings.json" ]; then
    safe_cp "$SOURCE_DIR/claude-code/settings.json.template" "$TARGET/$CC_DIR/settings.json"
  else
    skip "$CC_DIR/settings.json 已存在，跳过（请手动 merge hook）"
  fi
```

- [ ] **Step 2: 在结尾 here-doc 之前（第 138 行 `cat <<EOF` 之前）调用 ensure_skills**

```bash
# === 确保必备 skill 就位 ===
if [ "$NO_SKILLS" = "0" ]; then
  bash "$SCRIPT_DIR/ensure_skills.sh" "$TARGET" || skip "ensure_skills 有告警，请查看上方输出"
fi
```

- [ ] **Step 3: 验证 install.sh 语法**

Run: `bash -n tools/install.sh && echo ok`
Expected: `ok`

- [ ] **Step 4: 端到端冒烟（装到一个临时空仓）**

Run:
```bash
TMP="$(mktemp -d)" && bash tools/install.sh "$TMP" >/tmp/inst.log 2>&1; \
ls "$TMP/.claude/skills/" | grep -c secure-coding; \
test -f "$TMP/.claude/settings.json" && echo "settings ok"; \
rm -rf "$TMP"
```
Expected: 打印 `1` 和 `settings ok`

- [ ] **Step 5: Commit**

```bash
git add tools/install.sh
git commit -m "feat(install): distribute settings.json and run ensure_skills"
```

---

## Self-Review

对照 spec 覆盖检查：

- **spec §9.2 判断层 skill 清单**：Task 1–7 创建全部 11 个 skill（通用 10 + financial-numerics 1）。✅
- **spec §11 三层加载机制**：第 1 层=每个 SKILL.md 的 description（Task 1-7）；第 2 层=implementer.toml required_skills（Task 9）+ CLAUDE.md 硬规则（Task 10）；第 3 层=settings.json hook（Task 11）。✅
- **spec §12 ensure_skills 幂等安装**：Task 12（脚本+测试）+ Task 13（install 集成）。✅"已存在则跳过"由 Task 12 实现，superpowers 安装命令不写死（落地用 claude-code-guide 核实）。✅
- **spec §9.3 双相复用**：每个 skill 的 when_to_use 同时覆盖"写码"与"review 趟"，并在 CLAUDE.md（Task 10）声明被评审引用——具体评审接线在 Plan B。✅
- **spec §14 文档产出强制**：api-doc-output / data-model-output（Task 7）；CI 检查接线在后续 plan/项目 CI。✅

类型/命名一致性：skill 名在 README（Task 8）、implementer.toml（Task 9）、CLAUDE.md（Task 10）、settings.json（Task 11）、ensure_skills（Task 12）中全部一致（secure-coding/clean-code/testing-standards/sql-optimization/performance-review/financial-numerics/naming-convention/commenting/design-patterns/api-doc-output/data-model-output）。

无占位符：所有 skill、hook、脚本均给出完整内容。

文件清单（交付物）：11 个新 SKILL.md + settings.json.template + ensure_skills.sh(+test) + 改 implementer.toml/CLAUDE.md.template/skills-README/install.sh。
