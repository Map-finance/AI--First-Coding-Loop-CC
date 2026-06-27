# 组织级 GitHub Projects —— 跨多仓统一看板

## 为什么用组织级 Projects
issue 分散在多个代码仓（svc-order/web-order…），需要一个跨仓视图看全局进度。
组织级（Org-level）Projects v2 可聚合多仓 issue 到同一看板，全团队一个入口。

## 一次性配置
1. 在组织级新建 Project（v2），命名如 `Team Delivery Board`。
2. 字段建议：`Status`（Todo/In Progress/In Review/QA/Done）、`Type`（daily-task/feature/bug/qa-task/review）、`Service`（子服务）、`Assignee`、`Estimate`。
3. 在 Project 的 Workflows 里开启：
   - "Item added to project → Status = Todo"
   - "Item closed → Status = Done"
   - "Pull request merged → Status = Done"（覆盖关联了该 PR 的 issue）

## 自动入板（让各代码仓新建的 issue 自动进本看板）
两种方式择一：
- **内置 Auto-add workflow**（推荐）：在 Project Settings → Workflows → "Auto-add to project"
  里按仓/按 label 过滤，把目标代码仓新建的 issue 自动纳入。
- **Actions 方式**：在各代码仓加 `actions/add-to-project` 步骤，用 org-level PAT/App token
  把新 issue 加到本 Project（适合需要细粒度过滤时）。

## 跨仓自动关单（Closes #N 的约束与对策）
- **约束**：GitHub `Closes #N` / `Fixes #N` 只能自动关闭**同仓** issue。
- **对策**：daily-task/feature/bug/qa/review issue 都建在**对应代码仓**（见 ownership.md 的 repo 列），
  因此实现 PR 在同仓用 `Closes #N` 即可自动关单，看板 Status 经 workflow 同步为 Done。
- **跨仓引用**（仅展示关系，不自动关闭）：可用全限定 `Closes org/other-repo#N` 做关联引用，
  但**不会**自动关闭——需手动或经 Actions 调 API 关闭。故不依赖跨仓自动关单。
- **管理仓 team-ops 不放可关单 issue**：本仓只放计划文档与配置，避免"`Closes` 关不掉"的陷阱。
