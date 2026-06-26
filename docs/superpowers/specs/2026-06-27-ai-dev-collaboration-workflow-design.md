# 团队 AI 开发协作工作流 — 设计 Spec

- 日期：2026-06-27
- 状态：待评审
- 基座：AI-First Coding Loop（AIFCL）工程脚手架
- 适用：5 人前后端团队，即将启动的去中心化金融（DeFi）新项目，全流程重构为 AI 协作模式

---

## 1. 目标与非目标

### 1.1 目标
- 以 AIFCL 为基座，扩展并裁剪出一套 5 人团队可直接落地的 AI 开发协作流程。
- 覆盖端到端：需求 → 任务拆解/分配 → AI 辅助开发（强制规范）→ 本地自检 → PR → AI 自动评审 → CTO人工评审 → 合并 → 自动部署 → 测试任务自动生成 → QA 执行 → 测试 agent 审核报告 → 回测闭环。
- 规范"严格执行"的最终保证来自机器门禁（CI + 评审 gate），而非 agent 自觉。
- 跨项目共享文档与接口契约，提高对接效率。

### 1.2 非目标
- 不重新发明一套全新的协作方法论；一切建立在 AIFCL 既有能力上。
- 不在本期固化重型 DeFi 领域规范（合约安全、撮合一致性等），仅保留一个轻量的金额/数值提示 skill；其余作为未来可选扩展。
- 不追求一次性上线全部环节，按阶段推进。

---

## 2. 核心原则

1. **门禁不强制 = 没有门禁**：规范能机器判定的交给 linter/CI/SAST（确定性）；需要判断的交给 AI 评审（概率性，补盲区）。两者叠加，关键项设 required check 且禁止绕过。
2. **建议而非自动执行**：凡产生外部副作用的动作（建 issue、合并、部署、关单），agent 只产出草稿/建议，人确认后才执行。
3. **maker/checker 分离**：写代码的 agent 与判断"是否达标/完成"的 agent 分离。
4. **知识写一份，多处复用**：同一规范 skill 开发期用于"做对"，评审期用于"挑错"。
5. **YAGNI**：领域规范按需引入，不预先堆砌。

---

## 3. 架构决策

### 3.1 仓库拓扑：多仓 + 独立共享 docs 仓
- 不同项目各自独立代码仓库。
- 单独一个 `docs-repo` 共享文档与接口契约。
- 各代码仓通过 **git submodule** 引入 `docs-repo`（推荐），使 agent 在本地即可读到跨端契约与接口文档；备选为 CI 同步只读副本。

### 3.2 任务编排拓扑：编排在管理仓，issue 落代码仓，视图在组织级 Projects
- **关键约束**：GitHub 的 `Closes #N` 自动关闭关键字只能关闭**同仓**的 issue。
- 因此：
  - **管理仓 `team-ops`**：承载每日任务计划文档、`task-splitter` agent、Issue 模板、看板配置、编排脚本。
  - **具体 issue（开发/bug/测试/review）**：建在对应**代码仓**，使 PR 合并 + 测试通过可自动关单。
  - **统一视图**：使用**组织级 GitHub Projects**跨多仓聚合 issue，全团队一个看板看全局进度。

---

## 4. 目录结构

### 4.1 docs 仓（`docs-repo`）
```
docs-repo/
├── backend/
│   ├── architecture/            后端总体架构
│   ├── svc-<name>/              每个子服务一个目录
│   │   ├── architecture.md      子服务架构
│   │   ├── design.md            功能设计
│   │   ├── data-model.md        数据定义
│   │   └── api.md               接口文档
│   └── ...
├── frontend/
│   ├── architecture/
│   └── <module>/                各前端模块
│       ├── design.md
│       └── api.md
└── contracts/                   跨前后端共享的接口契约/类型（对接核心）
```

### 4.2 代码仓（每个项目）
```
<project-repo>/
├── CLAUDE.md                    团队"开发宪法"，agent 进项目必读
├── docs/                        git submodule → docs-repo
├── <src 按项目语言/框架组织>
├── .claude/
│   ├── skills/                  团队规范 skill（随仓下发）
│   ├── agents/                  角色化 agent 定义
│   └── settings.json            hooks（skill 提醒）等配置
├── scripts/                     AIFCL 脚本 + 新增脚本
├── prompts/                     评审/任务/测试用例生成 prompt
└── .github/workflows/           CI / AI 评审 / 部署 / 测试交接 / 每日健康
```

### 4.3 管理仓（`team-ops`）
```
team-ops/
├── daily/                       每日任务计划文档（按日期归档）
├── ownership.md                 项目级/子服务级责任人归属
├── scripts/task_splitter/       任务拆解 agent 与脚本
├── issue-templates/             各类 issue 的 Issue Form（YAML）
└── projects/                    组织级 Projects 看板配置
```

---

## 5. 角色与 Agent 映射（5 人团队）

| 人 / 角色 | 使用的 agent / skill | 关键约束 |
|---|---|---|
| CTO / PM（你） | `architect-task-writer` skill + 新增 `task-splitter` | 制定 + 多层拆解每日任务，产出草稿待确认 |
| 前端 / 后端同事 | `implementer`（写码，强制自带测试 + 输出文档）+ `checker`（本地自检） | maker/checker 分离 |
| CTO（评审） | `verifier-quality` / `verifier-security` / `verifier-performance` / `verifier-dependency` + 人工 review task | 四趟 AI 评审 + CTO人工评审 |
| 测试同事 | 新增 `qa-generator`（生成用例）+ `qa-reviewer`（审报告） | 测试闭环 |

> 5 人团队的项目级/子服务级责任归属用 CODEOWNERS + `ownership.md` 固化（相对静态）；每日任务才是动态拆解。

---

## 6. 端到端流程管线

```
需求
 │ architect-task-writer 写结构化任务规约
 ▼
任务拆解（task-splitter，按当日进度生成 → 产出草稿）
 │ 你确认后 → 在对应代码仓建 issue + 进组织级 Projects
 ▼
同事领取 → implementer 开发
 │ 强制 CLAUDE.md 宪法 + 规范 skill（命名/注释/安全/性能/SQL/韧性/整洁/financial-numerics）
 │ 同步产出：接口文档→docs/api、DB 定义→docs/data-model、模块说明
 ▼
本地自检（checker，独立判断）→ 通过才允许提 PR
 ▼
提交 PR
 │ 触发四趟 AI 评审（quality/security/performance/dependency）→ ai-review-gate
 │ 触发 CI 门禁（lint/类型/SAST/覆盖率/契约类型/bundle）→ ci-gate
 │ 自动建 review 任务 issue 指派CTO
 ▼
CTO领取 review task → 按标准评审 → 批准
 ▼
两个 gate 全绿 + CTO批准 → 合并 main
 ▼
自动部署（deploy.yml 六阶段）
 │ qa-generator：读本次 diff → 生成测试用例 + 测试流程 + 验收标准
 │ → 自动建 qa-task issue 进测试看板
 ▼
测试同事领取 → 按规范执行 → 按 Issue 模板提交测试报告
 ▼
qa-reviewer 审核报告（覆盖全部验收点？有证据？）
 │ PASS → 关单 + 记账    BLOCK → 打回 / 重开 dev 任务（回测）
 ▼
闭环 + 每日健康报告（进度 / token 账单 / 反认知投降三指标）
```

---

## 7. 任务拆解三层模型

| 层级 | 频率 | 载体 |
|---|---|---|
| ① 项目级分工（前端/后端） | 一次性 | CODEOWNERS + `ownership.md` |
| ② 子服务级归属（具体到人） | 里程碑 | CODEOWNERS + `ownership.md` |
| ③ 每日任务拆解与分配 | 每天 | `task-splitter` agent：按当日进度生成 → 草稿 → 人确认 → 建 issue |

`task-splitter` 每日产出两样东西：
- 当日任务计划文档（特定格式，存 `team-ops/daily/`）
- 待建 issue 清单（特定格式草稿）—— **人确认后**才真正创建。

---

## 8. Issue 类型体系

每种类型 = 一个 label + 一个 Issue Form（YAML，强制结构化字段）。

| type label | 用途 | 谁创建 | 关闭条件 |
|---|---|---|---|
| `daily-task` | 每日任务分配 | task-splitter（你确认后） | 关联 PR 合并 + 测试通过 |
| `feature` | 功能开发 | 拆解产出 | PR `Closes` |
| `bug` | bug 修复 | 人 / 自愈环 triage | 修复 PR 合并 |
| `qa-task` | 测试任务 | gen_test_tasks（合并后） | qa-reviewer 审核 PASS |
| `review` | CTO评审任务 | PR 打开时自动建 | CTO批准 |

`daily-task` 模板强制字段示例：责任人、所属子服务、验收标准、关联文档、预计工时、依赖项。

---

## 9. 开发规范体系

### 9.1 分层原则
- **机器层（确定性，CI 门禁）**：格式、命名大小写、行长、圈复杂度、import 顺序、覆盖率、SAST（注入/密钥）、契约类型、bundle 体积。基于成熟规则集：ESLint/Airbnb、Prettier、Ruff/PEP8、golangci-lint、SonarQube、OWASP、SQLFluff。
- **判断层（概率性，AI 评审 skill）**：命名语义、设计模式取舍、SQL 优化策略、抽象层级、韧性设计、注释质量等 linter 表达不了的判断。

### 9.2 判断层 skill 清单
通用（6-9 个，双相：开发期 + 评审期复用）：
- `naming-convention`、`commenting`、`secure-coding`、`performance-review`、`design-patterns`、`clean-code`、`sql-optimization`、`testing-standards`、`api-doc-output` / `data-model-output`

领域（轻量，仅提示）：
- `financial-numerics`：涉及金额/价格/交易时提醒——金额禁用浮点（用整数最小单位或定点 BigInt/Decimal）；token decimals 按各自读取，不硬编码；明确舍入方向。

> 合约安全、撮合一致性等重型 DeFi 规范本期不固化，列为未来可选扩展（见附录 B）。

### 9.3 开发期 / 评审期 / 双相
| 类别 | 何时用 | 例子 | 落点 |
|---|---|---|---|
| 纯开发期 | 写码时 | TDD、feature-flag-setup、api-doc-output | implementer 的 `required_skills` / description 触发 |
| 纯评审期 | PR review | 依赖审查、破坏性变更、PR 整体影响、跨文件一致性 | 编码进 ai_review prompt |
| 双相（多数） | 开发"做对"+ 评审"挑错" | sql-optimization、secure-coding、performance、resilience 等 | 同一 skill 两处引用 |

---

## 10. AI 评审与门禁

- 评审四趟（在 AIFCL 三趟基础上扩展）：
  - `quality`（问题库第 1/9/10/12 类）
  - `security`（第 6 类）
  - `performance`（第 2/3/4/5/7 类，新增）
  - `dependency`（第 13 类，已有）
- 每条判定 BLOCK / WARN；BLOCK 进不了主干。
- 团队真实痛点（SQL 无索引/全表、外部接口无超时、无重试/熔断/幂等、无限流、异常埋点缺失、日志不规范）在评审 prompt 中标 **BLOCK 级**。
- 机器门禁与 AI 评审叠加，关键项设 required check + 禁止绕过。

完整 13 类问题库见附录 A。

---

## 11. Skill 加载机制（三层）

1. **描述驱动自动触发（原生）**：每个 `SKILL.md` 的 `description` 写清"何时使用"，Claude 据此自动加载。
2. **CLAUDE.md 硬规则 + agent `required_skills`（强制）**：CLAUDE.md 写死强制规则（涉及 SQL 必用 sql-optimization 等）；`implementer` 的 `required_skills` 启动即挂载。
3. **hook 主动提醒**：在 `.claude/settings.json` 配 UserPromptSubmit hook，开发任务进来时提示相关 skill（团队统一生效）。

软触发负责覆盖面，硬强制负责关键规范不被漏掉。

---

## 12. Skill 安装机制

`scripts/ensure_skills.sh`，幂等，由 `install.sh` 调用：
- 对每个必备 skill：若 `~/.claude/skills/<skill>` 或 `.claude/skills/<skill>` 已存在则跳过（"有了就不用"）；否则安装。
- **superpowers**：社区 skill 集合，经 Claude Code plugin marketplace 或直接 git clone 安装。**确切安装命令在落地时以官方为准（用 claude-code-guide 核实），不凭记忆写死。**
- 团队规范 skill：随代码仓 `.claude/skills/` 下发，clone 即得。
- install 末尾做一次 skill 校验，缺关键项告警，确保全员环境一致。

---

## 13. 人工确认门

凡产生外部副作用的动作，agent 仅产出草稿/建议，人确认后执行：
- 每日任务分配：task-splitter 产出"计划文档 + 待建 issue 草稿" → 你 review → 确认后才 `gh issue create`。
- 合并：门禁是机器否决权，最终放行由人点。
- 部署、关单同理。

---

## 14. 文档产出规范

- 每个同事用 agent 开发其负责模块时，强制同步产出/更新：接口文档（`docs/api`）、数据定义（`docs/data-model`）、模块说明、必要的架构决策记录（ADR）。
- CI 检查：代码改动涉及接口/DB 但对应文档未更新 → gate 红。
- 文档存于 `docs-repo`，经 submodule 在各代码仓本地可读。

---

## 15. 分阶段实施计划

| 阶段 | 内容 | 验收 |
|---|---|---|
| 第 0 周：地基 | 各代码仓初始化 + install.sh 铺 AIFCL + docs-repo + submodule + CLAUDE.md 宪法 + 两个 gate 设 required | 空 PR 跑通门禁 |
| 第 1 周：开发侧 | 规范 skill + 四趟评审 + CTO review task + 文档强制检查 + ensure_skills | 真功能走完 开发→自检→PR→评审→CTO批→合并→部署 |
| 第 2 周：任务侧 | task-splitter + 组织级 Projects + Issue 模板 + 每日拆解/进度 + 人工确认门 | 下发任务能自动拆解建单、看板可视 |
| 第 3 周：测试侧 | gen_test_tasks + qa_review + qa-handoff workflow + 测试报告模板 | 合并后自动生成测试任务，QA 领取→报告→agent 审核→回测 |
| 持续：防失控 | daily-health（进度 + token 账单 + 反认知投降三指标） | 团队不退化为"只按 approve" |

---

## 16. 落地时需验证 / 待定项

1. superpowers 的确切安装方式（plugin marketplace vs git clone）—— 用 claude-code-guide 核实最新官方命令。
2. 各代码仓的具体技术栈/语言（影响 linter、CI、覆盖率工具选型）—— 待项目确定。
3. 部署目标环境（影响 deploy.yml 六阶段具体实现）—— 待确定。
4. 组织级 Projects 的自动化字段映射与跨仓自动关单的具体 Actions 实现细节。

---

## 附录 A：通用开发问题库（13 类，评审 checklist）

1. 正确性/逻辑：边界、空值、off-by-one、时区/日期、浮点精度、整数溢出、类型转换
2. 并发/异步：竞态、死锁、共享状态、异步未 await、资源泄漏
3. 数据库/持久层：N+1、缺索引、全表、SELECT *、大/长事务、锁竞争、缺分页、未参数化、迁移不可回滚、数据兼容
4. 外部依赖/韧性：无超时、无重试/退避、无熔断/降级、无幂等、无限流、级联失败/无背压
5. 性能：热路径重复计算、缓存缺失/击穿穿透雪崩、大 payload、序列化；前端重渲染/bundle/内存泄漏/长列表
6. 安全：注入、越权（鉴权 vs 授权）、密钥硬编码、敏感信息进日志、SSRF/CSRF、不安全反序列化、过度权限
7. 错误处理/可观测性：吞异常、错误未分级、缺埋点/监控/告警、缺 trace_id/上下文、日志结构化/级别/脱敏、缺健康检查与指标
8. API/契约：破坏性变更、版本兼容、契约不一致、文档未同步、状态码/错误格式、入参校验
9. 代码质量/可维护：命名、注释 why、复杂度、重复、职责单一、抽象层级、过度设计、魔法值、死代码
10. 测试：覆盖率、边界/异常路径、别测实现细节、缺集成/契约测试、可读性
11. 配置/部署/运维：特性开关、环境隔离、回滚、迁移与代码解耦、资源限制与超时
12. 文档：接口/DB/模块说明随代码更新、ADR
13. 依赖管理：必要性、许可证、体积、维护状态、已知漏洞

## 附录 B：DeFi/Web3 重型规范（未来可选扩展，本期不固化）

仅备查，未来真正做合约/撮合时再按需引入：
- 智能合约安全：重入、访问控制、价格操纵/闪电贷、MEV/抢跑、ERC20 兼容坑、代理升级、随机数、DoS、签名重放、事件、紧急控制
- 链上交互：交易生命周期/nonce/EIP-1559、reorg、幂等、RPC 冗余、私钥 KMS、链上链下对账
- 撮合引擎：价格-时间优先、串行化撮合、复式记账与余额不变量、幂等下单、自成交防护、确定性可重放、对账
- 机器门禁：Slither、Mythril、Foundry invariant/fuzz、主网 fork 测试；合约上线前必须第三方专业审计
