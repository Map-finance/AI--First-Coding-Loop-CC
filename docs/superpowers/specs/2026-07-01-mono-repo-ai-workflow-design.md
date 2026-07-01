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
│   └── web/                        # 前端应用
├── services/
│   ├── api/                        # API 网关服务
│   ├── matching-engine/            # 撮合引擎
│   ├── indexer/                    # 索引器
│   └── sdk/                        # 共享 SDK(库,非独立部署)
├── docs/
│   ├── architecture/               # 整体架构(全局,不分服务)
│   │   ├── overview.md             # 系统架构图 + 各服务职责说明
│   │   ├── service-map.md          # 服务间依赖与通信关系
│   │   └── tech-stack.md           # 技术选型及理由
│   ├── modules/                    # 各模块功能设计(每服务一份)
│   │   ├── web.md
│   │   ├── api.md
│   │   ├── matching-engine.md
│   │   ├── indexer.md
│   │   └── sdk.md
│   ├── feature-list.md             # 功能清单(全局,记录已上线/开发中/规划功能)
│   ├── api/                        # HTTP/RPC 接口文档(每服务一份)
│   │   ├── web.md
│   │   ├── api.md
│   │   └── sdk.md
│   ├── data-model/                 # 数据库表结构 + 字段说明(每服务一份)
│   │   ├── api.md
│   │   └── matching-engine.md
│   ├── changelogs/                 # 每个服务独立 changelog
│   │   ├── web/CHANGELOG.md
│   │   ├── api/CHANGELOG.md
│   │   ├── matching-engine/CHANGELOG.md
│   │   ├── indexer/CHANGELOG.md
│   │   └── sdk/CHANGELOG.md
│   ├── specs/                      # 设计决策文档(高层,跨服务)
│   ├── plans/                      # 实现计划
│   └── test-cases/                 # 测试用例 MD(按服务分目录)
│       ├── web/
│       ├── api/
│       ├── matching-engine/
│       ├── indexer/
│       └── sdk/
├── auto-tests/
│   ├── e2e/                        # Playwright 前端 E2E 测试
│   ├── api/                        # 接口集成测试
│   └── load/                       # 压测脚本(k6 等)
├── graphify-out/                   # 知识图谱(提交到仓库,随代码更新)
│   ├── GRAPH_REPORT.md             # 1页摘要:god nodes + 社区结构(agent 每 session 读一次)
│   ├── graph.json                  # 完整图谱(agent 按需查询,不整体读)
│   └── cache/                      # SHA256 缓存(只重处理变更文件)
└── .claude/                        # harness 安装点
```

**合法服务名**(`<service>` 字段的合法值):
`web` | `api` | `matching-engine` | `indexer` | `sdk`

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

### 5.1 PR 生成 Prompt

新增/更新 PR 生成 skill prompt,要求 agent 在提交 PR 草稿前必须完成以下文档同步:

| 改动类型 | 必须同步更新的文档 | 对应 harness skill |
|----------|-------------------|-------------------|
| 新增/修改 HTTP/RPC 接口 | `docs/api/<service>.md` | `api-doc-output` |
| 新增/修改 DB 表/字段/索引 | `docs/data-model/<service>.md` | `data-model-output` |
| 新增/修改功能模块行为 | `docs/modules/<service>.md` | — |
| 任意功能变更 | `docs/feature-list.md`(追加或更新条目) | — |
| 任意变更 | `docs/changelogs/<service>/CHANGELOG.md` | — |
| 可测功能变更 | `docs/test-cases/<service>/` | — |

全部文档更新后方可生成 PR 草稿。PR 模板的"影响范围"需列出所有修改过的文档路径。

### 5.2 Pre-Push Git Hook

`.claude/hooks/pre-push`:

检查 PR 描述(从 `git log` 最新 commit message 或 PR body 草稿文件读取)是否包含:
- `## 功能点`
- `## 影响范围`
- `## 测试用例`
- `## Breaking Changes`
- `## 迁移步骤`
- `## Rollback 方案`

任一缺失则阻断 push,输出错误提示。这是兜底检查;主要约束在 prompt 层。

### 5.3 Changelog 约束

agent session 结束前检查:每个在"影响范围"里列出的服务,其 `docs/changelogs/<service>/CHANGELOG.md` 的最后修改时间是否晚于 session 开始时间。未更新则提示 agent 补充。

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
