# Mono-Repo Scaffold + Graphify 集成 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 从零搭建新项目单仓骨架,包含标准目录结构、初始文档模板、graphify 知识图谱自动化安装与提交。

**Architecture:** 创建新 git 仓库,按 spec 定义的目录布局初始化所有目录和占位文件,通过 `make setup` 自动安装 graphify 并写入 CLAUDE.md 规则 + git hook,最后把初始知识图谱提交到仓库。

**Tech Stack:** Python 3.10+(graphify)、Make、git hooks、graphifyy PyPI 包

---

## 文件清单

**创建:**
- `Makefile` — setup/check/help targets
- `requirements-dev.txt` — 开发依赖(含 graphifyy)
- `.gitignore` — 标准忽略规则(不含 graphify-out/)
- `CLAUDE.md` — agent 上下文(graphify 读取规则 + 项目约定)
- `apps/web/.gitkeep`
- `services/api/.gitkeep`
- `services/matching-engine/.gitkeep`
- `services/indexer/.gitkeep`
- `services/sdk/.gitkeep`
- `docs/architecture/overview.md` — 架构说明模板
- `docs/architecture/service-map.md` — 服务依赖图模板
- `docs/architecture/tech-stack.md` — 技术选型模板
- `docs/modules/web.md` — 各服务模块设计模板(×5)
- `docs/modules/api.md`
- `docs/modules/matching-engine.md`
- `docs/modules/indexer.md`
- `docs/modules/sdk.md`
- `docs/feature-list.md` — 功能清单模板
- `docs/api/web.md` — 接口文档模板(×3)
- `docs/api/api.md`
- `docs/api/sdk.md`
- `docs/data-model/api.md` — 数据模型模板(×2)
- `docs/data-model/matching-engine.md`
- `docs/changelogs/web/CHANGELOG.md` — changelog 模板(×5)
- `docs/changelogs/api/CHANGELOG.md`
- `docs/changelogs/matching-engine/CHANGELOG.md`
- `docs/changelogs/indexer/CHANGELOG.md`
- `docs/changelogs/sdk/CHANGELOG.md`
- `docs/specs/.gitkeep`
- `docs/plans/.gitkeep`
- `docs/test-cases/web/.gitkeep` — 测试用例目录(×5)
- `docs/test-cases/api/.gitkeep`
- `docs/test-cases/matching-engine/.gitkeep`
- `docs/test-cases/indexer/.gitkeep`
- `docs/test-cases/sdk/.gitkeep`
- `auto-tests/e2e/.gitkeep`
- `auto-tests/api/.gitkeep`
- `auto-tests/load/.gitkeep`
- `.claude/` — harness 安装点(参考 AI--First-Coding-Loop-CC 结构复制)

---

## Task 1: 初始化仓库 + 根配置文件

**Files:**
- Create: `Makefile`
- Create: `requirements-dev.txt`
- Create: `.gitignore`

- [ ] **Step 1: 创建项目目录并初始化 git**

```bash
mkdir <your-project-name> && cd <your-project-name>
git init
git checkout -b main
```

- [ ] **Step 2: 创建 `.gitignore`**

```
# Python
__pycache__/
*.py[cod]
.venv/
*.egg-info/

# OS
.DS_Store
Thumbs.db

# IDE
.idea/
.vscode/
*.swp

# 注意: graphify-out/ 不在此处 — 它提交到仓库
```

- [ ] **Step 3: 创建 `requirements-dev.txt`**

```
graphifyy>=0.8.0
```

- [ ] **Step 4: 创建 `Makefile`**

```makefile
.PHONY: setup check help

help:
	@echo "make setup  — 安装开发依赖 + graphify + git hooks"
	@echo "make check  — 运行所有检查"

setup:
	@echo "==> 安装 Python 开发依赖..."
	pip install -r requirements-dev.txt
	@echo "==> 安装 graphify Claude Code 集成..."
	graphify claude install
	@echo "==> 安装 graphify git hooks..."
	graphify hook install
	@echo "==> setup 完成"

check:
	@echo "==> 检查 graphify 安装..."
	graphify --version
	@echo "==> 检查 git hooks..."
	test -f .git/hooks/post-commit && echo "post-commit hook: OK" || echo "post-commit hook: MISSING"
	test -f .git/hooks/post-checkout && echo "post-checkout hook: OK" || echo "post-checkout hook: MISSING"
```

- [ ] **Step 5: 验证 Makefile 语法**

```bash
make help
```

期望输出:
```
make setup  — 安装开发依赖 + graphify + git hooks
make check  — 运行所有检查
```

- [ ] **Step 6: 提交**

```bash
git add Makefile requirements-dev.txt .gitignore
git commit -m "chore: init repo with build setup and gitignore"
```

---

## Task 2: 创建目录结构

**Files:**
- Create: `apps/web/.gitkeep`
- Create: `services/{api,matching-engine,indexer,sdk}/.gitkeep`
- Create: `auto-tests/{e2e,api,load}/.gitkeep`
- Create: `docs/specs/.gitkeep`, `docs/plans/.gitkeep`
- Create: `docs/test-cases/{web,api,matching-engine,indexer,sdk}/.gitkeep`

- [ ] **Step 1: 创建所有目录和占位文件**

```bash
# 服务目录
mkdir -p apps/web
mkdir -p services/{api,matching-engine,indexer,sdk}
touch apps/web/.gitkeep
touch services/api/.gitkeep services/matching-engine/.gitkeep
touch services/indexer/.gitkeep services/sdk/.gitkeep

# 自动化测试目录
mkdir -p auto-tests/{e2e,api,load}
touch auto-tests/e2e/.gitkeep auto-tests/api/.gitkeep auto-tests/load/.gitkeep

# 文档子目录
mkdir -p docs/{architecture,modules,api,data-model,specs,plans,feature-list}
mkdir -p docs/changelogs/{web,api,matching-engine,indexer,sdk}
mkdir -p docs/test-cases/{web,api,matching-engine,indexer,sdk}
touch docs/specs/.gitkeep docs/plans/.gitkeep
touch docs/test-cases/{web,api,matching-engine,indexer,sdk}/.gitkeep
```

- [ ] **Step 2: 验证结构**

```bash
find . -not -path './.git/*' -type d | sort
```

期望输出包含:
```
./apps/web
./auto-tests/api
./auto-tests/e2e
./auto-tests/load
./docs/api
./docs/architecture
./docs/changelogs/api
./docs/changelogs/indexer
./docs/changelogs/matching-engine
./docs/changelogs/sdk
./docs/changelogs/web
./docs/data-model
./docs/modules
./docs/plans
./docs/specs
./docs/test-cases/api
./docs/test-cases/indexer
./docs/test-cases/matching-engine
./docs/test-cases/sdk
./docs/test-cases/web
./services/api
./services/indexer
./services/matching-engine
./services/sdk
```

- [ ] **Step 3: 提交**

```bash
git add .
git commit -m "chore: scaffold mono-repo directory structure"
```

---

## Task 3: 创建文档模板

**Files:**
- Create: `docs/architecture/overview.md`
- Create: `docs/architecture/service-map.md`
- Create: `docs/architecture/tech-stack.md`
- Create: `docs/modules/{web,api,matching-engine,indexer,sdk}.md`
- Create: `docs/feature-list.md`
- Create: `docs/api/{web,api,sdk}.md`
- Create: `docs/data-model/{api,matching-engine}.md`
- Create: `docs/changelogs/*/CHANGELOG.md`

- [ ] **Step 1: 创建架构文档模板**

`docs/architecture/overview.md`:
```markdown
# 系统架构概览

## 服务职责

| 服务 | 职责 | 技术栈 |
|------|------|--------|
| apps/web | 前端应用 | — |
| services/api | API 网关 | — |
| services/matching-engine | 撮合引擎 | — |
| services/indexer | 索引器 | — |
| services/sdk | 共享 SDK | — |

## 系统架构图

<!-- 在此插入架构图 -->

## 关键设计决策

<!-- 记录重要的架构决策及其理由 -->
```

`docs/architecture/service-map.md`:
```markdown
# 服务依赖关系

## 服务间通信

<!-- 描述各服务之间的调用关系、消息队列、共享数据等 -->

## 外部依赖

<!-- 第三方服务、数据库、消息队列等 -->
```

`docs/architecture/tech-stack.md`:
```markdown
# 技术选型

| 层次 | 技术 | 选型理由 |
|------|------|----------|
| — | — | — |
```

- [ ] **Step 2: 创建模块设计模板(每个服务一份)**

以 `docs/modules/api.md` 为例(其他服务同结构):
```markdown
# API 服务 — 模块设计

> 此文档记录"为什么这么设计",代码结构由 graphify-out/GRAPH_REPORT.md 自动生成。

## 设计动机

<!-- 为什么要有这个服务?解决什么问题? -->

## 关键约束

<!-- 性能要求、安全边界、兼容性限制等 -->

## 演进方向

<!-- 未来计划的重大变更或扩展 -->
```

对 `web`、`matching-engine`、`indexer`、`sdk` 创建相同结构的文件,将标题中的服务名替换。

- [ ] **Step 3: 创建功能清单**

`docs/feature-list.md`:
```markdown
# 功能清单

| 功能 | 服务 | 状态 | 上线日期 | 备注 |
|------|------|------|----------|------|
| — | — | 规划中/开发中/已上线 | — | — |
```

- [ ] **Step 4: 创建接口文档模板**

`docs/api/api.md`(其他服务同结构):
```markdown
# API 服务 — 接口文档

> 由 harness api-doc-output skill 约束同步更新。改接口必须同步更新此文件。

## 接口列表

### GET /example

**鉴权:** 需要登录  
**入参:**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|

**出参:**
```json
{}
```

**错误码:**

| 状态码 | 含义 |
|--------|------|
```

- [ ] **Step 5: 创建数据模型模板**

`docs/data-model/api.md`(matching-engine 同结构):
```markdown
# API 服务 — 数据模型

> 由 harness data-model-output skill 约束同步更新。改 DB 表结构必须同步更新此文件。

## 表: example_table

**用途:** —

| 字段 | 类型 | 可空 | 默认 | 说明 |
|------|------|------|------|------|

**索引:**
- `idx_example` ON (column) — 用途

**约束:** —

**迁移说明:** —
```

- [ ] **Step 6: 创建 changelog 模板(每个服务)**

`docs/changelogs/api/CHANGELOG.md`(其他服务同结构):
```markdown
# API 服务 Changelog

## [Unreleased]

<!-- 当前开发中的变更 -->

---

格式: `## [版本号] - YYYY-MM-DD`
```

对 `web`、`matching-engine`、`indexer`、`sdk` 创建相同结构。

- [ ] **Step 7: 验证所有文档文件存在**

```bash
find docs -name "*.md" | sort
```

期望输出包含所有 `.md` 文件(architecture ×3, modules ×5, api ×3, data-model ×2, changelogs ×5, feature-list)。

- [ ] **Step 8: 提交**

```bash
git add docs/
git commit -m "docs: add initial document templates for all services"
```

---

## Task 4: 创建 CLAUDE.md

**Files:**
- Create: `CLAUDE.md`

- [ ] **Step 1: 创建 `CLAUDE.md`**

```markdown
# CLAUDE.md

## 知识图谱(必读)

每次 session 开始时,先读 `graphify-out/GRAPH_REPORT.md` 了解代码库的 god nodes 和服务社区结构。

在使用 Grep/Glob 搜索文件之前,先通过知识图谱导航:
- 宏观结构 → 读 `graphify-out/GRAPH_REPORT.md`
- 具体路径查询 → `/graphify path <source> <target>`
- 影响范围分析 → `/graphify query "哪些模块依赖 <file>?"`

## 项目结构

```
apps/web/               — 前端应用
services/api/           — API 网关
services/matching-engine/ — 撮合引擎
services/indexer/       — 索引器
services/sdk/           — 共享 SDK
docs/                   — 共享文档库
auto-tests/             — 自动化测试
```

## 分支命名规范

```
<type>/<service>/<short-desc>

feat/api/add-jwt-refresh
fix/matching-engine/order-fill-race
```

type: feat | fix | refactor | docs | chore | test
service: web | api | matching-engine | indexer | sdk

## Commit 格式

```
<type>(<service>): <短描述>
feat(api): add JWT refresh endpoint
```

## PR 工作流

开发完成后,在生成 PR 草稿前必须同步以下文档(按改动类型):
- 改了接口 → `docs/api/<service>.md`
- 改了 DB 表 → `docs/data-model/<service>.md`
- 改了功能行为 → `docs/modules/<service>.md`
- 任意功能变更 → `docs/feature-list.md`、`docs/changelogs/<service>/CHANGELOG.md`
- 有可测功能 → `docs/test-cases/<service>/`

PR 描述必须包含以下 sections:
`## 功能点` / `## 影响范围` / `## 测试用例` / `## Breaking Changes` / `## 迁移步骤` / `## Rollback 方案`

## 文档职责分工

- `docs/architecture/` — 手写,记录战略决策(不描述代码结构)
- `docs/modules/<service>.md` — 手写,只写"为什么",代码结构由图谱负责
- `graphify-out/GRAPH_REPORT.md` — 自动生成,描述代码实际结构
```

- [ ] **Step 2: 验证 CLAUDE.md 可读**

```bash
wc -l CLAUDE.md
```

期望:行数 > 40。

- [ ] **Step 3: 提交**

```bash
git add CLAUDE.md
git commit -m "docs: add CLAUDE.md with project conventions and graphify rules"
```

---

## Task 5: 安装 graphify 并提交初始图谱

**Files:**
- Create: `graphify-out/GRAPH_REPORT.md` (由 graphify 生成)
- Create: `graphify-out/graph.json` (由 graphify 生成)
- Create: `graphify-out/cache/` (由 graphify 生成)

- [ ] **Step 1: 运行 make setup**

```bash
make setup
```

期望输出:
```
==> 安装 Python 开发依赖...
Successfully installed graphifyy-...
==> 安装 graphify Claude Code 集成...
==> 安装 graphify git hooks...
==> setup 完成
```

- [ ] **Step 2: 验证 graphify 安装**

```bash
graphify --version
```

期望:打印版本号,无报错。

- [ ] **Step 3: 验证 git hooks 安装**

```bash
make check
```

期望:
```
post-commit hook: OK
post-checkout hook: OK
```

- [ ] **Step 4: 构建初始知识图谱**

```bash
graphify .
```

期望:命令执行完成,在 `graphify-out/` 下生成以下文件:
```
graphify-out/GRAPH_REPORT.md
graphify-out/graph.json
graphify-out/cache/
```

- [ ] **Step 5: 验证图谱文件存在且非空**

```bash
ls -lh graphify-out/
wc -l graphify-out/GRAPH_REPORT.md
```

期望:`GRAPH_REPORT.md` 行数 > 10,`graph.json` 文件大小 > 0。

- [ ] **Step 6: 验证 CLAUDE.md 已被 graphify claude install 更新**

```bash
grep -i "graphify" CLAUDE.md | head -5
```

期望:至少有 1 行包含 graphify 相关规则(graphify claude install 会追加内容)。

如果 CLAUDE.md 被 graphify 覆写导致自定义内容丢失,手动合并两份内容。

- [ ] **Step 7: 提交图谱**

```bash
git add graphify-out/ CLAUDE.md
git commit -m "chore: add initial graphify knowledge graph"
```

- [ ] **Step 8: 验证 git hook 触发**

```bash
# 做一个小改动触发 post-commit hook
echo "# test" >> docs/architecture/overview.md
git add docs/architecture/overview.md
git commit -m "test: verify graphify post-commit hook"
```

期望:commit 完成后,graphify 自动运行更新(终端输出 graphify 日志)。

```bash
# 还原测试改动
git revert HEAD --no-edit
```

---

## Task 6: 验证完整交付物

- [ ] **Step 1: 验证目录结构完整**

```bash
find . -not -path './.git/*' -not -path './graphify-out/cache/*' | sort | head -80
```

确认包含所有预期目录和文件。

- [ ] **Step 2: 验证 make setup 在全新环境可重复执行**

```bash
# 模拟新成员流程
pip uninstall graphifyy -y
make setup
graphify --version
```

期望:setup 成功完成,graphify 可用。

- [ ] **Step 3: 验证 GRAPH_REPORT.md 对 agent 可读**

```bash
cat graphify-out/GRAPH_REPORT.md
```

期望:输出包含 god nodes、社区结构、意外连接等章节。

- [ ] **Step 4: 最终状态检查**

```bash
git log --oneline
```

期望:至少 5 条 commit:
```
chore: add initial graphify knowledge graph
docs: add CLAUDE.md with project conventions and graphify rules
docs: add initial document templates for all services
chore: scaffold mono-repo directory structure
chore: init repo with build setup and gitignore
```

- [ ] **Step 5: 推送到远程**

```bash
git remote add origin <remote-url>
git push -u origin main
```

---

## 交付验收标准

- [ ] `make setup` 在全新克隆环境执行成功
- [ ] `make check` 验证 graphify 和 git hook 正常
- [ ] 所有服务目录存在(`apps/web/`、`services/{api,matching-engine,indexer,sdk}/`)
- [ ] 所有文档模板已创建(architecture ×3, modules ×5, api ×3, data-model ×2, changelogs ×5)
- [ ] `graphify-out/` 已提交且包含 `GRAPH_REPORT.md` 和 `graph.json`
- [ ] `CLAUDE.md` 包含分支规范、commit 格式、PR 工作流、图谱读取规则
- [ ] git commit 触发 graphify 自动更新
