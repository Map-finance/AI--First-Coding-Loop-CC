---
name: task-splitter
description: 把架构师写好的当日任务源拆成"每日任务"粒度，产出当日任务计划文档与待建 issue 清单草稿(JSON)。运行 task_splitter.py，绝不直接建 issue；建 issue 由人确认草稿后运行 create_issues_from_draft.py 完成。
when_to_use: 每天开工时由 CTO/PM(人)触发，对当日任务源做第 ③ 层(每日)拆解；或里程碑刷新后需要重新分配当日任务时。
when_NOT_to_use: 项目级/子服务级责任归属(第 ①②层)——那用 CODEOWNERS + ownership.md 固化，相对静态，不走每日拆解；也不要用本 skill 直接建 issue(那是人确认后的另一步)。
---

# Skill: Task Splitter（每日任务拆解 + 人工确认门）

三层任务模型第 ③ 层（每日）的执行手册。**核心纪律:产草稿，人确认，才建单。**

## 前置
- 任务源已就绪：架构师用 `architect-task-writer` 写好的当日结构化任务(markdown)。
- `team-ops/ownership.md` 反映最新责任人归属。

## 步骤（原子动作）

### 1. 跑拆解，产出"计划文档 + 待建 issue 草稿"
```bash
python scripts/task_splitter.py \
  --source <任务源.md> \
  --date $(date +%F) \
  --plan-out team-ops/daily/$(date +%F).md \
  --draft-out state/tasks/draft-$(date +%F).json
```
脚本只写两个文件，**不碰 Tracker**。终端会打印"人工确认门"提醒。

### 2. 人 review 草稿（人工确认门，不可跳过）
打开 `state/tasks/draft-<date>.json` 与 `team-ops/daily/<date>.md`，逐条核对：
- 每条 `repo` 是否指向正确的**代码仓**(不是管理仓)？
- `assignee` 是否符合 ownership.md？拿不准的应留空而非瞎派。
- `daily-task` 强制字段(责任人/所属子服务/验收标准/关联文档/预计工时/依赖项)是否齐全？
- 验收标准是否可测？依赖顺序是否合理？
不满意就**手改草稿 JSON**，再继续。

### 3. 确认后建单（先 dry-run 再真建）
```bash
# 先 dry-run 预览将建什么(默认 TRACKER=github-dryrun)
python scripts/create_issues_from_draft.py --draft state/tasks/draft-$(date +%F).json --confirm
# 确认预览无误后,真正建到各代码仓(需本机 gh auth login)
TRACKER=github-cli python scripts/create_issues_from_draft.py \
  --draft state/tasks/draft-$(date +%F).json --confirm
```

### 4. 归档
`team-ops/daily/<date>.md` 提交进管理仓；建好的 issue 自动进组织级 Projects 看板(见 `team-ops/projects/README.md`)。

## 反模式
- ❌ 让 task_splitter 直接建 issue——它的职责就是只产草稿。
- ❌ 不 review 草稿就 `--confirm`——人工确认门形同虚设。
- ❌ 把 daily-task issue 建到管理仓 team-ops——`Closes #N` 关不掉，PR 合并不会自动关单。
- ❌ 拿不准责任人就硬指派——留空交人定。
