# Mono-Repo + AI 工作流设计

**日期:** 2026-07-01  
**状态:** 已批准,待实现  
**范围:** 新单仓项目脚手架 + harness 更新 + deepdog-BIOS 服务路由

---

## 背景与目标

新项目采用单仓(mono-repo)结构,多个微服务共存一仓。目标:

1. 统一目录约定,让 agent 和人都能快速定位任意服务的代码、文档、测试
2. 分支/提交/PR 命名携带服务信息,BIOS 自动路由任务给对应 agent/人
3. 测试用例文档与代码同步维护(开发阶段,同一 PR)
4. 自动化测试发现 bug 后直接回写 BIOS,不经 GitHub Issues 中转
5. 集成 graphify 知识图谱,降低 agent 导航 token 消耗,自动生成 PR 影响范围

---

## 1. 目录结构

```
<repo-root>/
├── apps/
│   └── web/                        # 前端应用（TypeScript + pnpm）
├── services/                       # Go 后端（多服务共一 Go module，hexagonal arch）
│   ├── cmd/                        # 各服务 main 入口（每个子目录编译为一个二进制）
│   │   ├── api/
│   │   ├── matching-engine/
│   │   └── indexer/
│   ├── internal/
│   │   ├── services/               # 各微服务实现
│   │   │   ├── api/                # hexagonal: domain/ ports/ adapters/ app/ bootstrap/
│   │   │   ├── matching-engine/
│   │   │   └── indexer/
│   │   └── shared/                 # 跨服务共享包（money、ulid、kafka、db 等）
│   ├── api/
│   │   ├── proto/                  # Protobuf 定义（buf 管理）
│   │   └── gen/                    # 生成代码（buf generate，提交到仓库）
│   ├── migrations/                 # DB 迁移脚本（sqlc + migrate）
│   ├── go.mod
│   ├── go.sum
│   └── Makefile                    # 内层执行 Makefile（verify/proto/db/fmt/build）
├── docs/
│   ├── architecture/               # 整体架构（全局，不分服务）
│   │   ├── overview.md             # 系统架构图 + 各服务职责说明
│   │   ├── service-map.md          # 服务间依赖与通信关系
│   │   └── tech-stack.md           # 技术选型及理由
│   ├── modules/                    # 各模块功能设计（每服务一份）
│   │   ├── web.md
│   │   ├── api.md
│   │   ├── matching-engine.md
│   │   └── indexer.md
│   ├── feature-list.md             # 功能清单（全局，记录已上线/开发中/规划功能）
│   ├── api/                        # HTTP/RPC 接口文档（每服务一份）
│   │   ├── api.md
│   │   └── ...
│   ├── data-model/                 # 数据库表结构 + 字段说明（每服务一份）
│   │   ├── api.md
│   │   └── matching-engine.md
│   ├── changelogs/                 # 每个服务独立 changelog
│   │   ├── web/CHANGELOG.md
│   │   ├── api/CHANGELOG.md
│   │   ├── matching-engine/CHANGELOG.md
│   │   └── indexer/CHANGELOG.md
│   ├── specs/                      # 设计决策文档（高层，跨服务）
│   ├── plans/                      # 实现计划
│   └── test-cases/                 # 测试用例 MD（按服务分目录）
│       ├── web/
│       ├── api/
│       ├── matching-engine/
│       └── indexer/
├── auto-tests/
│   ├── e2e/                        # Playwright 前端 E2E 测试
│   ├── api/                        # 接口集成测试
│   └── load/                       # 压测脚本（k6 等）
├── graphify-out/                   # 知识图谱（提交到仓库，随代码更新）
│   ├── GRAPH_REPORT.md             # 1页摘要：god nodes + 社区结构（agent 每 session 读一次）
│   ├── graph.json                  # 完整图谱（agent 按需查询，不整体读）
│   └── cache/                      # SHA256 缓存（只重处理变更文件）
├── .claude/                        # harness 安装点（skills/、agents/、settings/）
├── .github/                        # CI/CD 工作流
└── Makefile                        # 根级委托 Makefile（services-* / web-* / infra-up）
```

### 1.1 Hexagonal 微服务内部结构

每个 `services/internal/services/<svc>/` 目录遵循 hexagonal architecture：

```
<svc>/
├── domain/          # 纯业务逻辑：实体、值对象、领域服务（无框架依赖）
├── ports/           # 接口定义：输入端口（use cases）+ 输出端口（仓储/消息接口）
├── adapters/        # 接口实现：HTTP handler、gRPC server、DB repo、Kafka consumer
├── app/             # 应用服务：编排 use case，注入依赖
└── bootstrap/       # 启动装配：从 cmd/ 调用，构建依赖图，启动服务
```

**层级规则（严格，CI lint 强制）:**
- `domain/` 不得 import `adapters/`、`app/`、`bootstrap/`，也不得 import 任何外部框架
- `ports/` 只能 import `domain/`
- `adapters/` 可 import `domain/` + `ports/`，不得 import `app/`
- `app/` 可 import `domain/` + `ports/`，不得 import `adapters/`
- 跨服务共享类型放 `shared/`，不在服务间直接 import

### 1.2 Makefile 分层

**根级 `Makefile`（委托层，不含业务逻辑）:**

| Target | 说明 |
|--------|------|
| `make setup` | 安装所有依赖（services + web + graphify） |
| `make check` | 全量检查（services verify + web typecheck + web test） |
| `make infra-up` | 启动本地基础设施（Postgres、Kafka、Redis 等） |
| `make services-verify` | → `cd services && make verify`（fmt + vet + lint + test） |
| `make services-proto` | → `cd services && make proto`（buf lint + buf generate） |
| `make services-db` | → `cd services && make db`（sqlc generate） |
| `make services-fmt` | → `cd services && make fmt`（gofmt -w） |
| `make web-dev` | → `cd apps/web && pnpm dev` |
| `make web-test` | → `cd apps/web && pnpm test` |
| `make web-typecheck` | → `cd apps/web && pnpm typecheck` |

**`services/Makefile`（执行层，CI 与根级均调用此层）:**

| Target | 说明 |
|--------|------|
| `make verify` | fmtcheck + go vet + golangci-lint + `go test -race ./...` |
| `make proto` | buf lint + buf generate（结果写入 api/gen/，需提交） |
| `make db` | sqlc generate（从 migrations/ 生成 DB 层代码） |
| `make fmt` | `gofmt -w cmd internal` |
| `make build` | `go build ./cmd/...`（验证全量可编译） |

> CI 的 `go-quality` job 和 `proto-quality` job 直接在 `services/` 目录执行对应 make target，不经根级 Makefile。

**合法服务名**（`<service>` 字段的合法值，按实际项目列表填写）:
`web` | `api` | `matching-engine` | `indexer`

> `shared/` 包不作为独立服务，不参与分支/commit 命名中的 `<service>` 段。

### 1.3 Go 编码规范

> 以下规范同步体现在 harness skills 中（见第 5 节）。agent 动手前必须先读对应 skill。

#### 金额与精度

| 类型 | 用途 | 底层 |
|------|------|------|
| `Decimal18` | DB 存储 + JSON 序列化 | `NUMERIC(38,18)`，scale 固定 18 |
| `Dec` | 所有中间运算 | `shopspring/decimal` |

- 禁止 `decimal.NewFromFloat()`（lint 强制，浮点精度不可控）；改用 `decimal.NewFromString()` 或 `decimal.New()`
- **Web3 token 精度**：`token.Decimals` 从 DB 读取，绝不硬编码（不同 token 精度可能是 6、8、18 等）
  - 入链（链上 raw → 内部 Decimal18）：`money.FromMinorUnits(rawAmount, token.Decimals)`
  - 出链（内部 Decimal18 → 链上 raw）：`money.ToMinorUnits(token.Decimals)`
- 账本/结算字段 DB 类型升级为 `NUMERIC(78,18)`（防止高频撮合溢出）

#### ID 规范

- 跨服务主键：ULID（`oklog/ulid/v2`），禁止自增 int ID 跨服务引用
- 单服务内部可使用自增 ID，但不得暴露至接口层或其他服务

#### 日志

- 只用 `log/slog`，禁 zap / zerolog / `fmt.Print*`
- 所有日志调用必须传 `ctx`：`slog.InfoContext(ctx, "msg", "key", val)`
- 字段名用 snake_case：`user_id`、`order_id`、`duration_ms`
- 慢路径固定字段：`kind`、`op`、`duration_ms`、`threshold_ms`
- **Log storm 防护**：循环体内 sample（每 N 次记一条）；metrics 永不 sample
- PII 脱敏：通过 `slog.HandlerOptions.ReplaceAttr` 统一过滤，不在业务代码散点处理

#### 错误处理

- 哨兵错误：`var ErrXxx = errors.New("...")`，用 `errors.Is` / `errors.As` 判断，禁止字符串比较
- 多错误合并：`errors.Join(err1, err2)`
- 资金/结算操作错误：绝不吞掉 → 进入 protection mode + 触发告警（宁可停服，不可静默损失）

#### 可观测性

- OTel span：只在 `adapters/` 层创建；`domain/` 和 `app/` 层不引入 OTel 依赖
- Prometheus metrics：在 middleware / interceptor 层收集，不在业务逻辑层埋点
- Prometheus label 约定：`service`、`method`、`status`、`shard_id`（基数可控，禁止用 user_id 做 label）

#### 配置

- 配置库：`koanf`，禁 viper
- 启动时 fail-fast：必填配置缺失直接 `panic`，不静默降级

#### 规范 ↔ Skill 对照

| 规范 | 对应 harness skill | 强制时机 |
|------|-------------------|---------|
| 金额 / token 精度 | `financial-numerics` | 涉及金额、价格、余额、token 数量时 |
| 日志 | `go-logging` | 涉及任何 Go 日志输出时 |
| 错误处理 | `go-error-handling` | 涉及错误返回、资金操作时 |
| 可观测性 | `go-observability` | 新增服务 / 外部调用 / 请求链路时 |

---

## 2. 命名规范

### 2.1 分支命名

```
<type>/<service>/<short-desc>
```

- `type`: `feat` | `fix` | `refactor` | `docs` | `chore` | `test`
- `service`: 合法服务名之一(见上)
- `short-desc`: 小写连字符,不超过 40 字符

**示例:**
```
feat/api/add-jwt-refresh
fix/matching-engine/order-fill-race
docs/web/update-onboarding-guide
chore/sdk/upgrade-grpc-v2
test/api/auth-integration
```

### 2.2 Commit 格式

```
<type>(<service>): <短描述>
```

与分支名保持一致的 type + service 前缀。

**示例:**
```
feat(api): add JWT refresh endpoint
fix(matching-engine): prevent double-fill on concurrent orders
docs(web): update onboarding guide
```

### 2.3 PR 描述模板

所有 PR 必须包含以下完整模板(agent 生成草稿时强制填齐):

```markdown
## 功能点
- 简洁列举本次新增/修改的功能(每条一行)

## 影响范围
- services/api
- docs/test-cases/api/auth.md

## 测试用例
- docs/test-cases/api/auth.md#TC-012 (新增)
- docs/test-cases/api/auth.md#TC-008 (修改)
- 无(若本次改动不涉及可测功能)

## Breaking Changes
- 无 / 或说明变更及影响

## 迁移步骤
- 无 / 或说明操作步骤

## Rollback 方案
- 回滚 commit <sha> 即可 / 或说明步骤
```

---

## 3. Agent-First PR 工作流

```
agent 开发功能(同一 session)
  │
  ├─ [改了接口]        → 更新 docs/api/<service>.md
  ├─ [改了 DB 表结构]  → 更新 docs/data-model/<service>.md
  ├─ [改了功能行为]    → 更新 docs/modules/<service>.md
  ├─ [任意功能变更]    → 更新 docs/feature-list.md(追加或更新条目)
  ├─ [有可测功能]      → 更新 docs/test-cases/<service>/
  └─ [任意变更]        → 更新 docs/changelogs/<service>/CHANGELOG.md
        │
        ▼
  生成 PR 草稿(完整模板,影响范围列出所有改过的文档路径)
        │
        ▼
  输出草稿给人审查
        │
   人编辑 / 确认
        │
        ▼
  人执行: gh pr create
```

**所有相关文档必须在同一个 PR 里更新,不允许单独补提。** 判断依据:看改动类型,不是每次全更新。

---

## 4. 测试用例文档 ↔ 自动测试脚本

```
docs/test-cases/<service>/<feature>.md    ← 人/agent 维护,描述测试意图
        │
        │  agent 读取并生成
        ▼
auto-tests/<type>/<service>/<feature>.yaml / .spec.ts   ← 可执行脚本
```

测试用例 MD 格式约定:
```markdown
## TC-012: JWT 刷新 token 过期后自动续期

**前置条件:** 用户已登录,access_token 在 5 分钟内过期  
**操作步骤:**
1. 等待 access_token 过期
2. 发起任意 API 请求

**预期结果:** 自动用 refresh_token 换取新 access_token,请求正常返回  
**类型:** integration  
**优先级:** P1
```

---

## 5. Harness 变更(AI--First-Coding-Loop-CC)

> **状态说明:** 本节记录实际已落地的变更。原设计中的 5.1/5.2/5.3 已以不同形式实现，见下。

### 5.1 CLAUDE.md.template 更新（已完成）

`claude-code/CLAUDE.md.template` 全面重写，适配单仓结构：

- **目录结构**：更新为 mono-repo 布局（apps/web/ + services/ hexagonal + auto-tests/ + docs/ + graphify-out/ + .claude/）
- **Session 开始必读**：新增 `graphify-out/GRAPH_REPORT.md` 优先读取规则
- **编码规范**：新增 Go 后端规范（hexagonal 层规则、slog、ULID、错误处理）+ React 前端规范（TypeScript strict、禁 class component、金额用 string）
- **强制加载表**：新增 13 行 skill 强制加载规则（按情形 → 必读 skill）
- **文档同步义务表**：新增 PR 前必须完成的文档同步要求（改接口 → api.md，改 DB → data-model.md，等）
- **工作约定 Rule 7**：批量推送规则——修完所有评审意见后一次性 commit & push，禁止碎推

原设计的"PR 生成 prompt skill"和"pre-push hook 检查 PR 描述结构"均通过 CLAUDE.md.template 的强制规则实现，不单独做 hook 脚本。

### 5.2 新增 Skills（已完成）

| Skill | 路径 | 覆盖内容 |
|-------|------|---------|
| `go-logging` | `skills/go-logging/SKILL.md` | slog only；context 传播；snake_case 字段；慢路径固定格式；log storm 防护；PII ReplaceAttr 过滤 |
| `go-error-handling` | `skills/go-error-handling/SKILL.md` | 哨兵错误；errors.Is/As；errors.Join；资金错误绝不吞 → protection mode + 告警 |
| `go-observability` | `skills/go-observability/SKILL.md` | OTel span 在 adapters 层；Prometheus 在 middleware 层；label 约定（service/method/status/shard_id） |
| `changelog-output` | `skills/changelog-output/SKILL.md` | Keep-a-changelog 格式；Unreleased 区块；各服务独立文件（docs/changelogs/\<service\>/）；Breaking Changes 必须单独成节 |

原设计的"session 结束前 changelog 检查"由 `changelog-output` skill 的约束替代——开发完成后 agent 必须先读 skill 再写 changelog，PR 前检查义务在 CLAUDE.md.template 文档同步表中强制。

### 5.3 更新 Skills（已完成）

| Skill | 变更内容 |
|-------|---------|
| `financial-numerics` | 新增 Go 部分：Decimal18+Dec 两类型、禁 NewFromFloat（lint 强制）、web3 token.Decimals 从 DB 读；新增 React 前端部分：金额用 string、formatTokenAmount、禁浮点运算 |
| `api-doc-output` | 路径更新：`docs/api/<service>.md`；新增格式模板（金额字段标注为 string）；移除 docs-repo/contracts/ 引用 |
| `data-model-output` | 路径更新：`docs/data-model/<service>.md`；新增 NUMERIC(38,18) 约定，禁 FLOAT；新增迁移说明模板（可回滚性、锁影响评估） |

> **文档落点为项目可自定义项。** 上述 5.2/5.3 中 skill 记录的 `docs/api/<service>.md`、`docs/data-model/<service>.md`、`docs/changelogs/<service>/` 等为**默认（扁平）布局**；skill 本身不写死路径，而**以各项目 `CLAUDE.md`「目录结构」节为准**——例如 ba-trading 按服务分目录 `docs/services/<服务名>/{api.md,数据模型.md,CHANGELOG.md}`（另有各服务的 `<服务名>.md` 详细设计文档）。harness 源 skill（`claude-code/skills/*`）已改为「落点见项目 CLAUDE.md」的通用表述，因此 `tools/update.sh` 覆盖 skill 时不会打回项目自定义的落点。

### 5.4 CI 工作流更新（已完成）

`core/workflows/ci.yml` 变更：

- **路径过滤**：Go 路径 `services/**/*.go` + `services/go.mod`；新增 proto 路径 `services/api/proto/**/*.proto` + `services/buf.yaml`
- **Go 版本**：从 `services/go.mod` 动态读取（`go-version-file: services/go.mod`），不硬编码
- **`working-directory`**：所有 Go/proto job 统一设为 `services`
- **新增 `proto-quality` job**：buf lint + buf generate + 校验生成代码已提交（未提交则 CI 报错）
- **`ci-gate`**：将 `proto-quality` 纳入必须通过的 job 列表

---

## 6. deepdog-BIOS 变更

### 6.1 服务提取与回退路由

在 `handlePullRequestEvent` 完成 PR upsert 后,按三级优先级确定服务名:

```
级别 1: 解析分支名
  feat/api/xxx → service = "api"  ✓ 直接路由

级别 2: 分支名不合规 → 分析变更文件路径(纯路径匹配,非 LLM)
  GitHub API: GET /repos/{owner}/{repo}/pulls/{number}/files
  services/api/handler/auth.go  → api
  services/api/service/token.go → api
  全部命中同一服务 → service = "api" + 打 naming:nonstandard 标签

级别 3: 文件跨多服务 → tag service:multi + 通知 workspace 默认负责人人工处理
  services/api/... + services/matching-engine/...  → 无法自动路由
```

`parseServiceFromBranch` 实现:

```go
// parseServiceFromBranch extracts the service segment from a
// branch name following the <type>/<service>/<desc> convention.
// Returns "" for branches that don't match the pattern.
func parseServiceFromBranch(ref string) string {
    parts := strings.SplitN(ref, "/", 3)
    if len(parts) < 2 {
        return ""
    }
    known := map[string]bool{
        "web": true, "api": true,
        "matching-engine": true, "indexer": true, "sdk": true,
    }
    if known[parts[1]] {
        return parts[1]
    }
    return ""
}
```

### 6.2 任务路由

在 `handlePullRequestEvent` 完成 PR upsert + issue 关联后,按 service 路由:

```
service = parseServiceFromBranch(branch)
if service != "" {
    给关联 issue 打标签 service:<name>
    查 workspace 的 service→project 映射
    按任务类型分发:
      ├─ test-task   → 固定分配给 test agent(workspace 级配置)
      ├─ pr-review   → 分配给 service project 的负责 agent/人
      └─ bug-fix     → 分配给 service project 的负责 agent/人
}
```

### 6.3 Service → Agent 路由

不维护独立路由表。路由配置存在 agent 实体自身上:创建智能体时通过 `负责服务` 多选字段声明该 agent 负责哪些服务(如 `api`、`matching-engine`)。

BIOS 路由逻辑:
```
收到 service = "api" 的 PR 事件
  → 查询 workspace 内 services 包含 "api" 的 agent
  → 按任务类型分发:
      test-task   → 固定分配给 test agent(services 含 "test")
      pr-review   → 分配给对应 service agent
      bug-fix     → 分配给对应 service agent
```

**BIOS 需要的改动:**
- `agents` 表加 `services text[]` 列
- 创建/编辑智能体 UI 加"负责服务"多选字段
- `handlePullRequestEvent` 路由时查 `agents.services @> ARRAY[service]`

**V1 实现范围:** 只写入 `service:api` 标签到关联 issue,agent services 字段 + 自动指派在 V2 实现。V1 人工根据标签筛选指派。

### 6.4 自动化测试 Bug 回写

CI 测试失败时,通过 BIOS API 直接创建 bug 工单:

```
POST /api/issues
{
  "title": "[auto-test] <test name> failed",
  "labels": ["bug", "service:<service>", "auto-test"],
  "body": "<failure details + test file path>",
  "project_id": "<from service routing config>"
}
```

- 请求携带 CI 专用 API token(workspace 级配置)
- service 名从测试文件路径提取:  
  `auto-tests/api/auth.yaml` → `service:api`
- BIOS 根据 service 标签自动指派给 service 负责人(V2 自动,V1 人工)

---

## 7. Graphify 知识图谱集成

### 7.1 安装(自动,作为仓库 setup 的一部分)

`requirements-dev.txt` 或 `Makefile` 的 `setup` target 中包含:

```bash
pip install graphifyy          # 安装 graphify
graphify claude install        # 写入 CLAUDE.md 规则 + PreToolUse hook
graphify hook install          # 安装 post-commit / post-checkout git hook
```

新成员 clone 仓库后执行 `make setup` 即自动完成,无需手动操作。

### 7.2 图谱提交到仓库

`graphify-out/` **不加入 `.gitignore`**,随代码提交:

- `GRAPH_REPORT.md` — 1 页摘要,agent 每 session 读一次,了解 god nodes 和社区结构
- `graph.json` — 完整图谱,agent 按需查询(`/graphify query` / `path`),不整体读
- `cache/` — SHA256 缓存,保证重复运行只处理变更文件

**好处:** 任何 agent clone 仓库后立即有可用图谱,无需首次重建(首次重建需要 LLM token)。

### 7.3 自动更新机制

```
git commit → post-commit hook → graphify --update   (只处理变更文件,走缓存)
git checkout → post-checkout hook → graphify --cluster-only  (重新聚类,不重提取)
```

图谱随每次 commit 自动刷新,无需人工维护。

### 7.4 Agent 使用模式

```
session 开始
  → 读 graphify-out/GRAPH_REPORT.md  (~2-5k tokens,一次)
  → 了解 god nodes、服务社区、意外连接

开发过程中(按需)
  → /graphify query "哪些模块依赖 api/auth.go?"
  → /graphify path <changed_file> <service_boundary>

生成 PR 草稿
  → graphify path 输出 → 填入 PR 模板"影响范围"section
  → 比 agent 自己猜更准确
```

### 7.5 对 docs/ 的影响

graphify 自动生成模块结构信息,因此 `docs/modules/` 中:
- **不需要**手动维护"代码结构是什么"(图谱负责)
- **仍需要**手动维护"为什么这么设计"(战略决策、设计动机)

`docs/modules/<service>.md` 内容精简为:设计动机 + 关键约束 + 演进方向,不再描述代码结构。

---

## 8. 实现优先级

| 阶段 | 内容 | 备注 |
|------|------|------|
| **V1** | 新仓库脚手架 + 目录结构 + Harness PR prompt 更新 + pre-push hook | 立即可用 |
| **V1** | Graphify 自动安装 + git hook + 初始图谱提交 | `make setup` 一键完成 |
| **V1** | BIOS: `parseServiceFromBranch` + service 标签写入 | 小改动 |
| **V1** | CI → BIOS bug 工单 API + CI 脚本 | 需要 CI 配置 |
| **V2** | BIOS: agent `services` 字段 + 自动指派 | 需要 DB migration + UI |
| **V2** | test-cases MD → YAML 脚本自动生成 | 需要 agent skill |

---

## 9. 不在本次范围内

- deepdog-BIOS 和 deepdog-work 代码本身的改动(继续独立维护)
- Automation UI 的事件过滤扩展
- mobile/desktop 客户端
- 多 workspace 的 service 路由隔离(单 workspace 场景优先)
- graphify 的 Neo4j 推送、SVG 导出等高级功能
