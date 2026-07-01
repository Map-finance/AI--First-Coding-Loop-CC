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

---

## 1. 目录结构

```
<repo-root>/
├── apps/
│   └── web/                    # 前端应用
├── services/
│   ├── api/                    # API 网关服务
│   ├── matching-engine/        # 撮合引擎
│   ├── indexer/                # 索引器
│   └── sdk/                    # 共享 SDK(库,非独立部署)
├── docs/
│   ├── changelogs/             # 每个服务独立 changelog
│   │   ├── web/CHANGELOG.md
│   │   ├── api/CHANGELOG.md
│   │   ├── matching-engine/CHANGELOG.md
│   │   ├── indexer/CHANGELOG.md
│   │   └── sdk/CHANGELOG.md
│   ├── specs/                  # 设计文档
│   ├── plans/                  # 实现计划
│   └── test-cases/             # 测试用例 MD(按服务分目录)
│       ├── web/
│       ├── api/
│       ├── matching-engine/
│       ├── indexer/
│       └── sdk/
├── auto-tests/
│   ├── e2e/                    # Playwright 前端 E2E 测试
│   ├── api/                    # 接口集成测试
│   └── load/                   # 压测脚本(k6 等)
└── .claude/                    # harness 安装点
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
  ├─ 更新 docs/test-cases/<service>/    ← 与代码同步,同一 PR
  ├─ 更新 docs/changelogs/<service>/CHANGELOG.md
  └─ 生成 PR 草稿(完整模板填齐)
        │
        ▼
  输出草稿给人审查
        │
   人编辑 / 确认
        │
        ▼
  人执行: gh pr create
```

**测试用例和 changelog 必须在同一个 PR 里更新,不允许单独补提。**

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

新增/更新 PR 生成 skill prompt,要求 agent 在提交 PR 草稿前必须:

1. 确认 `docs/test-cases/<service>/` 已更新
2. 确认 `docs/changelogs/<service>/CHANGELOG.md` 已追加本次变更
3. 填齐 PR 模板所有 section(不允许留空或写"TODO")
4. 在"影响范围"里列出所有修改过的 `services/` 或 `apps/` 子目录

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

### 6.1 服务提取

在 `handlePullRequestEvent` 开头添加服务名提取:

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

### 6.3 Service → Project 映射

每个 workspace 维护一张 `workspace_service_routing` 配置(存入 workspace settings 或独立表):

```
service_name  →  project_id  +  default_assignee_id
api           →  proj-xxx    +  agent-xxx
web           →  proj-yyy    +  agent-yyy
...
```

**V1 实现范围:** 只写入 service 标签(`service:api`)到关联 issue,路由表配置和自动指派在 V2 实现。V1 人工根据标签筛选指派。

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

## 7. 实现优先级

| 阶段 | 内容 | 备注 |
|------|------|------|
| **V1** | 新仓库脚手架 + 目录结构 + Harness PR prompt 更新 + pre-push hook | 立即可用 |
| **V1** | BIOS: `parseServiceFromBranch` + service 标签写入 | 小改动 |
| **V1** | CI → BIOS bug 工单 API + CI 脚本 | 需要 CI 配置 |
| **V2** | BIOS: `workspace_service_routing` 表 + 自动指派 | 需要 DB migration + UI |
| **V2** | test-cases MD → YAML 脚本自动生成 | 需要 agent skill |

---

## 8. 不在本次范围内

- deepdog-BIOS 和 deepdog-work 代码本身的改动(继续独立维护)
- Automation UI 的事件过滤扩展
- mobile/desktop 客户端
- 多 workspace 的 service 路由隔离(单 workspace 场景优先)
