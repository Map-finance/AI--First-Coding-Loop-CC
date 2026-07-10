<!-- @VARIANT:header -->

---

## 🛑 强制行为纪律(动手前必读)

**任何写码 agent**(implementer / explorer / verifier-quality 等)**动手前**,必须先吃这份:
- [`.claude/skills/agent-coding-discipline/SKILL.md`](.claude/skills/agent-coding-discipline/SKILL.md) — 10 条规则 + 4 个失败模式 + 8 项 pre-submit 自检

## 🛑 并行优先原则(v2.6,主 session 必读)

**主 session 收到任何"加 X / 改 Y / 实现 Z"的需求,第一件事不是写码,而是判断"能不能并行分解"。**

- 先调 [`.claude/skills/task-decomposer/SKILL.md`](.claude/skills/task-decomposer/SKILL.md) 决策并出 DAG
- 可并行 → 调 [`.claude/skills/parallel-orchestrator/SKILL.md`](.claude/skills/parallel-orchestrator/SKILL.md) 用 Task tool **一条消息派 N 个子 agent 真并行**
- 串行 → 直接走 architect-task-writer + implementer

**默认保守**:有疑虑就串行(并行错的代价 ≫ 串行慢)。但对真正可分的任务(N 个独立模块 / 功能 / 服务、各自独立的 provider)**一定要并行,不要傻串行**——这是 v2.6 对"v2.5 比 v2.2 慢"问题的核心解答。

简版(贴墙):

1. **读再写** —— 读完整文件,不要扫
2. **想再做** —— 先说假设和 tradeoff
3. **简单** —— 写眼前问题的最少代码
4. **外科手术式** —— diff 像任务一样小;**不顺手 reformat**
5. **fail-first 测试** —— 修 bug 先写失败的测试再修
6. **goal-driven** —— 成功标准先于代码
7. **debug 不靠猜** —— 读完整 stack、复现、一次只改一处
8. **依赖永久** —— 标准库优先,加新依赖必说理由
9. **沟通** —— 说做了什么、为什么、有什么顾虑;不确定的事**精确**说出来
10. **持续推进** —— 没到需要人工决断前**不中断、一直往下推**;并行时只有卡到人工决断的那个子 session 停,其余照常继续;能自己定的小选择别抛给人(反面=空停)

4 个失败模式(发现 = 停):Kitchen Sink / Wrong Abstraction / Optimistic Path / Runaway Refactor。

PR 描述自动带 pre-submit checklist(见 `.github/pull_request_template.md`)。

---

<!-- @VARIANT:repo-and-layout -->

## Session 开始必读

每次进入项目后，按顺序执行：
1. **读 `graphify-out/GRAPH_REPORT.md`**（若存在）— 了解 god nodes、服务社区、意外依赖（~2-5k token，读一次）
2. **读本文件** — 确认当前技术栈和命令
3. **按需读 skill** — 根据任务类型，参考下方"规范 skill 强制加载"表
4. **BIOS 任务绑定（可选,新对话/新任务开场时问一次)**——主动问用户一句:"这次任务关联哪个 BIOS 工单号?(没有可跳过)"。
   - 用户给了工单号(如 `TES-42`)→ 调用 BIOS MCP 工具 `bios_bind_session`(`issue_key`=用户给的工单号,`session_id`=当前会话 id),把本会话绑定到该工单。绑定后本会话的对话与进度会自动挂到该工单,不用再手动汇报。
   - 用户没给 / 跳过 → 直接开始,不阻塞开发。
   - 可用工具列表里没有 `bios_bind_session`(daemon 未运行,或项目未接入 BIOS)→ 同样跳过,不要报错卡住。

<!-- @VARIANT:local-dev -->

## 编码规范

> ⚠️ **以下"后端"与"前端"小节是示例，必须按项目实际技术栈整节替换。**
> 保留"通用"小节；其他小节若技术栈不同，删除示例内容并填写本项目的约束。
> 详细规则通过对应 skill 承载（见下方"规范 skill 强制加载"表），这里只列核心禁区和跳转指针。

<!-- @VARIANT:coding-standards -->

### 通用
- 日志：结构化（JSON），字段含 `service`、`request_id`、`level`；自愈环依赖这些字段做聚类
- 测试：新代码必须带测试；关键路径必须有集成/E2E 测试

## 安全禁区(BLOCK 级,评审会拦)
- 不得硬编码密钥/token;用环境变量 + secrets。
- 新端点默认必须鉴权;越权(IDOR)零容忍。
- 用户输入到 SQL/shell/模板一律参数化/转义。
- 不得在日志/响应中泄露 PII 或凭证。

## 特性开关(强制)
- **每个新功能必须藏在特性开关后**（见 `[feature-flag 入口文件路径，按项目填写，如 internal/flags/flags.go 或 src/flags/index.ts]`）。
- 新增 flag 时:在代码里用类型安全的 key,并在 PR 描述里写明 flag 名与灰度计划。
- 不要删旧 flag 而不清理其分支逻辑。

## 部署(harness 不内置)
- **部署高度项目特定(AWS/Vercel/k8s/Cloud Run 各不同),harness 不提供部署 workflow**,由各项目自行配置或交管理端。
- agent 不应手动操作 prod;合并后的部署由各项目自己的流水线负责。

## 🛑 合并与发布纪律(每次合并进 main 都要,强制)
**任何 PR 合并进 `main` 后,必须立刻做这两件事,缺一不算完成:**
1. **打 tag** —— 给这次合并打一个 git tag 并 push 到远端。命名按项目既有约定(语义化版本 `vX.Y.Z`,或日期 `vYYYY.MM.DD-N`)。tag 是**回滚锚点**。
2. **写合并记录** —— 在 GitHub 基于该 tag 建一个 **Release**,正文写清这次合并**改了什么 / 为什么 / 影响面**(可由 PR 标题+描述生成)。Release 是**人能读的合并审计**。

一条命令同时建 tag + Release:
```bash
gh release create <tag> --target main \
  --title "<tag> — <一句话说明>" \
  --notes "$(printf '改动:...\n原因:...\n影响面:...')"
```
> 铁律:**没打 tag、没写 Release 的合并 = 没合并完。** 不要直推 main 跳过 PR,也不要合了 PR 就走人。

## 给实现 agent 的工作约定
1. **分支纪律(BLOCK 级):禁止直接 commit/push 到 `main`。** 任何改动必须:新建分支 → 提交 → 开 PR → 过门禁(ci-gate/ai-review-gate + 人工评审)→ 合并。
2. **先出计划与风险,再写码。** 列出你识别到的失败模式、安全边界、可能的技术债。
3. 不扩大范围;任务模板(`prompts/architect-task.md`)第 3 节之外的需求,先问架构师。
4. 自带测试,确保本仓的集成/测试命令(见"本地开发"节)通过。
5. 开 PR 时在描述里列出权衡点,并指出需要人类重点看的"战略风险"。
<!-- @VARIANT:work-rule-6 -->
7. **响应评审要批量提交**:修复 PR 评审意见时,**批量修完所有点 + 本地自检通过,再一次性 commit & push**。禁止每修一处就 push——四趟评审跑在每次 push(`synchronize`)上,碎推会频繁重跑评审、刷屏评论、浪费 Actions 配额。改完一批再推一次。
8. **开 PR 前先本地 code review**:跑 `ai_review.py` 四趟(配本地 LLM key)或 `/code-review` 审本分支 diff,BLOCK 项先改再开 PR——省一轮 CI 往返。本地代码评审用 `verifier-*` 那套评审,**不是** `checker`(两者区别见下方 Sub-agents 说明)。
9. **有 BIOS 工单号时,阶段各自出 PR + 阶段末显式报 stage/进度(可选,别攒到最后一次性交)**:需求/方案讨论定稿 → 开一个**计划 PR**(落地方案文档,分支/标题带工单号,如 `docs/plan/<KEY>-slug`,把工单推进到 plan_assign);开发完成 → 开**实现 PR**(`feat/<service>/<KEY>-slug`);测试补齐或修 bug → 开**测试/修复 PR**(`fix/<service>/<KEY>-slug`)。分支名/PR 标题带工单号是 GitHub 事件自动推进工单阶段的锚点(见分支命名节)。
   - **在此基础上,若本会话已绑定该工单(开场用 `bios_bind_session` 拿到了 issue_key)**,每个阶段结束时额外显式调用 `bios_update_stage(issue_key, stage)` 报告 stage(`plan_assign` | `execute` | `verify` | `close` 四阶段):需求/计划阶段定稿、准备开发 → `execute`(计划刚出、还没进开发可先报 `plan_assign`);开发进行中/开完实现 PR → `execute`,进入等待评审 → `verify`;PR 合入 main / 任务完成(如"PR #187 已合入 main")→ `close`,并调 `bios_report_progress(issue_key, note)` 补一句精炼的完成摘要。
   - 这是补 GitHub 事件覆盖不到的阶段(尤其非编码工作,如纯讨论、纯测试)的事实信号,BIOS 侧仲裁里 `source=mcp` 权威,**不代替**上面的 PR 节奏,是额外一步。
   - **前提**:仅当已绑定(拿到了 issue_key)才调;没绑定 / 工具不可用 → 跳过,不阻塞开发,不要报错卡住。
   - 没有工单号 / 未接入 BIOS → 按原节奏走,不强制拆 PR,也不用调这些工具。

## 给 triage agent 的工作约定
- 错误来源：可观测后端（[按项目填：Datadog / Grafana + Prometheus / CloudWatch 等]）+ 错误追踪（[Sentry / Rollbar 等]）。
- 按错误指纹聚类、九维打分(见 `scripts/triage_engine.py` + `skills/triage-severity-scorer/SKILL.md`)。
- 建单前先去重:用 `state/triage-history.jsonl` 识别首次/稳定/回归;已知 flake 自动降权。
- 建议步骤遵循 `skills/pr-investigator/SKILL.md`。

---

## v2 新增:Skills / Agents / State / Loops

### Skills(`.claude/skills/<name>/SKILL.md`)
项目知识按域拆分。agent 看到 `description` 与 `when_to_use` 自动加载相关 skill。
新增 skill:在 `.claude/skills/` 下建目录(目录名即 skill 名,含 SKILL.md;CC 按 frontmatter 的 `name`/`description` 自动发现,无需注册表)。

#### 规范 skill 强制加载（开发与评审的共同底线）

任何 agent 在以下情形**必须先 Read 对应 skill 再动手**（不是"自觉"，是硬规则）：

**所有项目通用（不随技术栈变化）：**

| 情形 | 必须先读 skill |
|------|--------------|
| 涉及 SQL/ORM/DB 迁移 | `sql-optimization` |
| 外部调用/并发/缓存/监控 | `performance-review` |
| 处理用户输入/鉴权/密钥/序列化 | `secure-coding` |
| 改 HTTP/RPC 接口 | `api-doc-output` |
| 改 DB 表结构/字段 | `data-model-output` |
| 任意功能变更完成后（PR 前） | `changelog-output` |
| 任何改动的底线 | `clean-code` + `testing-standards` |
| 新功能 | 额外加 `feature-flag-setup` |

**技术栈相关（按项目实际保留/替换）：**

> Go 后端保留以下行。其他技术栈的 logging/error-handling/observability 等 skill **已按 pack 提供**(stack:node/rust/java/python、frontend:common/web/mobile/desktop),安装时按 `--stacks` 选装,完整清单见 `skills/PACKS.md`。

| 情形 | 必须先读 skill | 适用范围 |
|------|--------------|---------|
| 涉及 Go 日志输出 | `go-logging` | Go 后端 |
| 涉及 Go 错误处理 | `go-error-handling` | Go 后端 |
| 新增服务/外部调用/请求链路 | `go-observability` | Go 后端 |

**领域相关（按项目业务保留/移除）：**

> 金融/资产类项目保留；非金融项目可删除这两行。

| 情形 | 必须先读 skill | 适用范围 |
|------|--------------|---------|
| 涉及金额/价格/余额/token 数量 | `financial-numerics` | 金融/资产类项目 |
| 前端展示金额或精度敏感数值 | `financial-numerics`（前端部分） | 金融/资产类项目 |

这些 skill 同时被 PR 的 AI 评审引用（见 `.github/workflows/ai-review.yml`）。开发期漏掉的，评审期会拦。

#### 文档同步义务（PR 前必须完成）

<!-- @VARIANT:doc-sync -->

**所有相关文档必须在同一 PR 里更新，不允许单独补提。**

### Sub-agents(`agents/<name>.toml`)
角色化的 agent + 模型分层:`explorer`(Haiku)/`implementer`(Sonnet)/三类 `verifier`(分层)/
`triage-scorer`(Sonnet)/`checker`(Sonnet)。**写代码的 agent 不能是判断 done 的 agent**。

> **别混 `checker` 与 `verifier`(两个不同职责)**:
> - `checker` = goal_loop 的**完成度判定**,返回 `done|continue|stuck`——判断"**任务做完没**"。
> - `verifier-quality/security/performance/dependency` = **code review**——评审"**代码好不好**"(质量/安全/性能/依赖)。
> 本地自审(开 PR 前)和 PR 门禁的代码评审,都用 `verifier-*` 那套,**不是 checker**。spec 早期把 checker 当本地自审 reviewer 是角色错位,以本说明为准。

### State(`state/`)
agent 的外置记忆:`triage-history.jsonl`、`token-usage.jsonl`、`comprehension-log.jsonl`、
`tasks/<id>.json`、`known-flakes.txt`。**append-only 优先**,入仓可审计。

### Goal Loops(`scripts/goal_loop.py`)
跑到一个可验证的停止条件成立为止。implementer 推一步 → checker(独立 sub-agent)判定 done。
长任务、回归修复、CI 自愈都套这个范式。

### Worktrees(`scripts/spawn_agent_worktree.sh`)
并行 agent 任务必须用 `git worktree` 隔离 fs + 隔离 docker compose project name,
否则集成测试一定撞车。

### Token 与 Comprehension 报告
- `scripts/token_report.py`:按 day / loop / role / model 聚合花费,集成进每日健康报告
- `scripts/comprehension_metrics.py`:**反认知投降护栏**——comprehension-coverage、
  pr-read-rate、agent-modification-rate 三项指标低于阈值会触发红线告警

---
*保持本文件最新是架构师的职责。它过时一天,agent 就盲一天。*
