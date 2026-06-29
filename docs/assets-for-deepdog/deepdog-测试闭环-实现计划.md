# deepdog 测试闭环 — 实现计划与需求(自包含交接文档)

> **给接手这份文档的 AI**:你在 **deepdog-BIOS** 仓(`/Users/luis/work/luis/ai/deepdog-BIOS`)工作。这份文档自包含你需要的全部上下文——你**不需要**访问任何其他仓库。目标是在 deepdog 里实现一条"测试闭环"。
>
> **重要前提**:文档中的"deepdog 现状"基于 2026-06 的**只读源码调查**,文件路径已给出。**实现前请先打开这些文件核实**(代码可能已演进),并严格遵循 deepdog 既有的 handler/service/migration/sqlc 模式。
>
> **建议流程**:不要直接盲写。先 ① 读 §3 列出的现状文件核实 → ② 就 §7 的设计决策做一轮 brainstorming 与人对齐 → ③ writing-plans 出逐步实现计划 → ④ 分阶段实现(Go + 迁移 + 测试)。

---

## 1. 背景:为什么这个功能落在 deepdog

团队有两套系统:
- **客户端 harness**(AI-First Coding Loop):装在执行机/代码仓,负责"按规范开发 + CI 四趟 AI 评审"。
- **管理端 deepdog-BIOS**(本仓):AI workforce 控制塔,负责项目/任务/issue/agent 派发/验证/进度。

"测试闭环"原型曾在 harness 用独立 Python 脚本实现(`gen_test_tasks.py` 读 diff 生成测试用例、`qa_review.py` 审核测试报告),但它建 GitHub issue、与 deepdog 的 issue 中心打架,且管理端才是它的正确归宿(有 DB/UI/派发/webhook)。**因此 harness 已移除该实现,把核心逻辑以 prompt 形式交接给 deepdog**(见 §6 内嵌的两个 prompt)。本任务 = 在 deepdog 把这条闭环原生实现出来。

---

## 2. 要实现的测试闭环(端到端需求)

```
PR 提交/更新(或合并)
  │
  ① 读取本次代码改动 diff
  ▼
  ② LLM 读 diff → 生成「测试用例 + 测试流程 + 验收标准」(用 §6.1 prompt)
  ▼
  ③ 建「测试任务」并指派(测试人 / QA agent),验收标准写入结构化字段
  ▼
  QA 执行测试 → 提交「测试报告」(逐条对应验收标准 + 证据)
  ▼
  ④ LLM 审核报告 → VERDICT: PASS | BLOCK(用 §6.2 prompt,缺判定保守 BLOCK)
  ▼
  ⑤ 人工确认签字(AI 预审 + 人确认)
  ▼
  PASS → 推进 issue 到 close   /   BLOCK → 回测(打回重测 / 重入队 execute)
```

核心价值:把 deepdog 现有的"CI + 人工签字"验证,升级为"**自动生成测试内容 + AI 预审报告 + 人确认**"的完整闭环。

---

## 3. deepdog 现状(可复用的基础设施 + 文件路径)

技术栈:Go 1.26(Chi router / sqlc / gorilla-ws) + Next.js + PostgreSQL(pgvector) + Redis + daemon。

| 能力 | 现状 | 关键文件 |
|---|---|---|
| GitHub webhook | 已收 `pull_request`/`check_suite`,记录 PR metadata + diff **统计**(增删行数),但**不读 diff 内容** | `server/internal/handler/github.go` |
| LLM 集成 | 已有,用于 agent 执行任务/思维链/工具调用 | `server/pkg/agent/claude.go` |
| issue 模型 | `issue` 表;`acceptance_criteria` JSONB、`context_refs` JSONB **字段已存在但 dormant(无代码自动填)**;`origin_type`(autopilot/quick_create/conversation) | `server/migrations/001_init.up.sql`(约 52–72 行) |
| issue 创建 | autopilot 可建普通 issue(模板渲染);对话蒸馏→草稿→人确认 | `server/internal/service/autopilot.go`(`dispatchCreateIssue`)、`handler/conversation_promote.go` |
| 任务派发 | `agent_task_queue`(queued→dispatched→running→done)+ daemon WebSocket | `handler/daemon_ws.go`、`handler/task_lifecycle.go` |
| 验证网关 | **计算驱动,无显式表**;状态从 issue+PR+check_suite 派生(no_pr/blocked/waiting/ready/pending_verification/pending_close/closed) | `server/internal/handler/verification_gate.go` |
| 人工签字 | `POST /api/issues/{id}/verify` → 写 `metadata.deepdog_verified_by/_at` + activity_log;`DELETE` 取消 | `server/internal/handler/issue_verify.go` |
| 工作循环 | 阶段 plan_assign→execute→verify→close;停止条件 auto/human/hybrid;自主性 full_auto/checkpointed/human_led;**回测靠 `engineRedispatch` 重入队 execute** | `server/internal/workloop/workloop.go`、`server/internal/service/autonomy_engine.go`、`packages/core/issues/work-stage.ts` |
| 成员角色 | 仅 owner/admin/member(**无 QA/tester 角色**) | `server/migrations/001_init.up.sql`(约 26–33 行) |

---

## 4. deepdog 缺口(本任务要补的,经源码核实)

| 环节 | 现状 | 缺口 |
|---|---|---|
| ① 读 PR diff 内容 | webhook 只存 diff 统计 | 需拉取 diff 正文(GitHub API) |
| ② 生成测试用例/验收标准 | ❌ 完全没有;无任何"读 diff→LLM→测试"的代码 | 新增生成逻辑(用 §6.1 prompt);把验收标准写入 `acceptance_criteria`(激活 dormant 字段) |
| ③ 测试任务 + 指派 QA | ❌ issue 无 type/kind 区分测试任务;无 QA 角色;验证不走独立测试 issue | 设计测试任务载体 + 指派机制(见 §7 决策) |
| ④ AI 审核测试报告 | ❌ 只有人工签字,无 AI 预审 | 新增 AI 预审 step(用 §6.2 prompt),接到 verify 流程 |
| ⑤ 回测 | ✅ `engineRedispatch` 已有 | 几乎不用改,接上即可 |

> 一句话:deepdog 已有"验证网关 + 回测循环",**缺的正是"自动生成测试内容"(②)和"AI 预审报告"(④)这两步**——也就是 §6 两个 prompt 对应的能力。

---

## 5. 实现方案(映射 deepdog 真实模块)

| 步骤 | 复用 | 新增/改动 |
|---|---|---|
| **A. 拉 PR diff** | `github.go` 已处理 `pull_request` 事件 | 在该 webhook 分支里调 GitHub API 拉 diff 正文(注意大 diff 截断,可设上限字符数) |
| **B. 生成测试内容** | `agent/claude.go` 的 LLM 调用封装 | 新建一个 service(如 `service/test_gen.go`):用 §6.1 prompt + diff 调 LLM → 解析出测试用例/流程/验收标准 → 把验收标准写入对应 issue 的 `acceptance_criteria` JSONB |
| **C. 测试任务 + 指派** | `issue` 表、autopilot 建 issue、`agent_task_queue` 派发 | 见 §7 决策:测试任务用独立 issue(label/kind=`test-task`)或同 issue 阶段;指派测试人/QA agent |
| **D. 报告 + AI 预审** | `issue_verify.go` 的人工签字、verify 阶段 | QA 提交报告(载体见 §7);新增 AI 预审 step:用 §6.2 prompt 审报告 → `VERDICT: PASS\|BLOCK`,记录到 issue;PASS 放行人工签字,BLOCK 阻断并提示补什么 |
| **E. 回测** | `autonomy_engine.go` 的 `engineRedispatch` | BLOCK → 触发回测(打回重测或重入队 execute) |
| **数据模型** | sqlc + migrations 既有模式 | 视 §7 决策可能新增:issue `kind`/label、测试报告载体表/字段、QA 角色 enum、AI 预审结果字段 |

**建议分阶段**:先做 A+B(diff→生成→写 acceptance_criteria,先能看到自动生成的验收标准),再 C(测试任务/指派),再 D(AI 预审),最后 E(回测接线)。每阶段独立可测、可合。

---

## 6. 可复用的核心 prompt(从 harness 交接,直接移植进 deepdog 的 LLM 调用)

### 6.1 测试用例/验收标准生成(用于步骤 B)

````markdown
# 测试任务生成 — qa-generator

你是 QA 测试设计师。下面给你一次「PR」的 **DIFF**。
你要为它产出一份可被测试同事直接执行的测试任务，输出**中文 Markdown**。

## 你的任务
只针对本次 diff 改动的行为面设计测试（不要为未改动的旧功能编用例）。结合
改动的接口/数据/边界，覆盖正常路径、边界、异常与回归风险。

## 输出结构（严格按以下三段，用二级标题）
### 测试用例
逐条编号 `TC1/TC2/...`，每条含：前置条件、输入、操作步骤、**预期结果**。
覆盖：正常路径、边界值、错误输入/异常分支、并发或幂等（若 diff 涉及）、
对既有调用方的兼容性（若改了契约/接口）。

### 测试流程
QA 实际执行的顺序与环境要求（dev/staging、数据准备、依赖服务、回滚注意）。

### 验收标准
逐条可勾选 `- [ ]`，每条是一个**客观可判定**的通过条件（不是"看起来正常"，
而是"接口返回 200 且 X 字段等于 Y""重复提交两次只入账一次"这种可验证陈述）。
qa-reviewer 后续会逐条核对 QA 报告是否覆盖这些验收点，请让它们清晰、原子、可证。

## 重要
- 不要复述 diff，不要泛泛而谈；只产出能直接执行的用例与可判定的验收标准。
- 涉及金额/价格/交易时，验收标准要显式覆盖精度与舍入。
- 若 diff 改了数据库/迁移，加入数据兼容与回滚验证用例。
````

> 移植提示:把生成的「验收标准」段解析后写入 issue 的 `acceptance_criteria` JSONB(激活该 dormant 字段);测试用例/流程可放 issue 描述或测试任务正文。

### 6.2 测试报告审核 / AI 预审(用于步骤 D)

````markdown
# 测试报告审核 — qa-reviewer

你是 QA 审核员（maker/checker 分离中的 checker）。下面给你一个测试任务
的正文（含**验收标准**）和 QA 提交的**测试报告**。你判断这份报告是否达标。

## 审核维度
1. **覆盖完整性**：报告是否逐条对应「验收标准」的每一个 `- [ ]`？
   有没有遗漏的验收点？被勾选的点是否真的给了结果说明？
2. **证据充分性**：每个声称通过的点是否附了可信证据（截图链接 / 日志片段 /
   接口响应 / 用例执行记录）？只有"已测试通过"而无证据的，视为未覆盖。
3. **结论一致性**：报告结论与逐点结果是否自洽？有不通过项却给"通过"结论 → BLOCK。

## 输出格式
- 先按上面三维列出发现，指明**缺哪条验收点 / 缺哪条证据**（精确到 TC 编号或验收点）。
- 然后末尾**单独一行**给出判定：`VERDICT: PASS` 或 `VERDICT: BLOCK`。

## 判定规则
- 全部验收点都被覆盖且每条有证据、结论自洽 → `VERDICT: PASS`。
- 任一验收点未覆盖 / 缺证据 / 结论矛盾 → `VERDICT: BLOCK`，并说清要补什么。
- **没把握时保守判 BLOCK**（放过未审核的报告比多打回一次代价更高）。

## 重要
你是闭环门禁，不是建议箱。PASS 会放行关单，BLOCK 会打回重测，所以判定必须有依据。
````

> 移植提示:VERDICT 解析要**保守**——找不到明确判定行,或一行内同时出现 PASS/BLOCK 时,**默认取 BLOCK**(安全方向,测试审核不能误放行)。

---

## 7. 需要先对齐的设计决策(建议 brainstorming 逐条定)

1. **测试任务载体**:独立 issue(label/`kind`=`test-task`,parent_issue_id 指向被测 issue) vs 同一 issue 的 verify 阶段附属?(影响 UI、派发、进度统计)
2. **验收标准存储**:写入 `acceptance_criteria` JSONB(推荐,激活既有字段) vs issue 描述正文?
3. **QA 指派**:新增 `qa`/`tester` 角色 enum vs 复用 `member` + label?(改角色 enum 影响面大,先评估)
4. **测试报告载体**:issue 评论 vs 新建 `test_report` 表/字段?
5. **AI 预审的强制度**:BLOCK 是硬阻断(必须人复核才能签字) vs 仅作建议展示?
6. **生成时机**:PR opened/synchronize 就生成(供 review 阶段参考) vs 合并后生成?(harness 原设计是合并后;deepdog 可更早)
7. **与 stop_condition 的关系**:测试闭环是否只对 `human`/`hybrid` 的 issue 启用?`auto`(纯 CI gated)的 issue 是否也生成测试任务?

---

## 8. 验收标准(本功能做完的判定)

- [ ] PR 改动(按 §7.6 选定的时机)触发 → 对应 issue 自动获得 LLM 生成的测试用例 + 写入 `acceptance_criteria` 的验收标准
- [ ] 能创建测试任务并指派(测试人 / QA agent),测试人能看到用例与验收标准
- [ ] QA 提交测试报告 → AI 预审产出 `PASS`/`BLOCK`(缺判定保守 BLOCK)→ 人工确认 → PASS 推进 close、BLOCK 触发回测
- [ ] 新增逻辑有 Go 单元/集成测试,遵循 deepdog 既有 handler/service/migration/sqlc 模式
- [ ] 不破坏既有验证网关/workloop 行为(回归通过)

---

## 9. 给接手 AI 的执行顺序

1. **核实现状**:打开 §3/§4 列出的文件,确认 webhook、LLM 封装、issue/acceptance_criteria 字段、verify 流程、workloop redispatch 的真实写法。
2. **brainstorming**:就 §7 的 7 个决策与人对齐(尤其测试任务载体、QA 角色、AI 预审强制度)。
3. **writing-plans**:基于对齐结果出逐步实现计划(分 A→B→C→D→E 阶段)。
4. **实现**:按 deepdog 模式逐阶段写 + 加测试 + 自检,分阶段提交/PR。
5. 全程:测试闭环是 deepdog 既有"验证网关 + 回测循环"的**增强**,优先复用,不要另起一套并行机制。
