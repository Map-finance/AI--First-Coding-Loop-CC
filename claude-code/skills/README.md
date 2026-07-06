# Skills(v2)

> 把项目知识从 prompt 字符串升级为可发现、可命名调用、按域拆分的 Skill 体系。
> 灵感:Addy Osmani《Loop Engineering》第 3 块积木;格式参考 Codex / Claude Code 的 `SKILL.md` 规范。

## 在你的项目里怎么放

- **用 Claude Code**:把 `skills/` 整个移到 `.claude/skills/`
- **用 Codex CLI**:移到 `.codex/skills/`
- **用其他 agent / MCP**:保留 `skills/`,在调用 prompt 里显式 `Read skills/<name>/SKILL.md`

## 当前 skills

> **完整包清单(66 个 skill / 12 个 pack)见 [`PACKS.md`](PACKS.md)** —— 按技术栈(go/node/java/rust/python/frontend)与业务域(finance/web3-solidity)分包,install.sh 按 `--stacks/--domains` 或探测选装。下表仅列常驻/通用核心 skill。

| 名字 | 何时用 | 谁触发 |
|---|---|---|
| **`task-decomposer`** ★v2.6 | **主 session 收到需求第一件事**——判断可否并行分解,输出 DAG | 主 session |
| **`parallel-orchestrator`** ★v2.6 | 拿 DAG 后用 Task tool 真并行 fan-out → fan-in → 整合 | 主 session |
| **`agent-coding-discipline`** ★v2.4 | **任何写码 agent 动手前必读**(9 规则 + 4 失败模式 + 8 项 pre-submit) | 所有 implementer/explorer/verifier |
| `architect-task-writer` | 把模糊想法变成结构化任务 prompt | 架构师 |
| `pr-investigator` | 给 triage 自动工单做根因调查 | triage cron / 操作员 |
| `feature-flag-setup` | 给新功能加一个完整 flag | implementer agent |
| `api-endpoint-creator` | 加新 HTTP 端点的标准做法 | implementer agent |
| `triage-severity-scorer` | 九维严重度打分规则 | triage_engine.py 自动 |
| `weekly-comprehension-check` | 架构师每周自检——反认知投降护栏 | **人**(不是 agent) |
| `sql-optimization` | 查询优化（索引/N+1/全表/分页） | implementer / review |
| `secure-coding` | 应用级安全判断 | implementer / review |
| `performance-review` | 性能+韧性+可观测性 | implementer / review |
| `financial-numerics` | 金额/数值安全（金融产品） | implementer |
| `naming-convention` | 命名语义 | implementer / review |
| `commenting` | 注释解释 why | implementer / review |
| `design-patterns` | 设计模式取舍/防过度设计 | implementer / review |
| `clean-code` | 整洁度/职责单一/去重 | implementer / review |
| `testing-standards` | 测试覆盖与质量 | implementer / review |
| `api-doc-output` | 改接口同步产出接口文档（落点见项目 CLAUDE.md） | implementer |
| `data-model-output` | 改数据模型同步产出数据模型文档（落点见项目 CLAUDE.md） | implementer |
| `go-logging` | Go slog 结构化日志规范（禁 zap、风暴防护、脱敏） | implementer / review |
| `go-error-handling` | Go 错误处理（哨兵错误、errors.Is/As、资金保护模式） | implementer / review |
| `go-observability` | Go 可观测性（OTel span + Prometheus 埋点位置） | implementer |
| `changelog-output` | 任意功能变更后产出 CHANGELOG 条目 | implementer |

## SKILL.md 写法约定

每个 skill 顶部 YAML front-matter 必须含:

```yaml
---
name: <kebab-case>
description: <一段紧凑、无聊、可被 LLM 解析的功能描述>
when_to_use: <触发条件,具体>
when_NOT_to_use: <反触发条件,防止越界>
---
```

**description 要无聊、要紧凑、要描述能力而不是夸赞**——Addy 反复强调"一段紧凑无聊的 description 比聪明的 description 更容易被准确触发"。

## 加一个新 skill

1. 在 `skills/<category>/<subpack>/<name>/` 下建目录(按 pack 分类,如 `stack/go/`、`frontend/web/`、`universal/`),放 `SKILL.md`
2. 可选:放配套脚本 `scripts/`、参考 `references/`、资产 `assets/`
3. 在本 README 表格里加一行
4. 如果它是被自动化引用的(triage/health/goal_loop),还要在对应 workflow 或脚本里加调用点

## 把 skill 打成 plugin(可选)

跨仓库共享时,把 `skills/<name>/` 打成 zip(扩展名 `.skill`),发布到内部 marketplace。
**skill 是格式,plugin 是分发方式**——这条 Codex 和 Claude Code 一致。
