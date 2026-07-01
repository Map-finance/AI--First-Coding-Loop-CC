---
name: parallel-orchestrator
description: 主 session 拿到 task-decomposer 的 DAG 后,执行 fan-out → fan-in → 整合的回路。利用 Claude Code 的 Task tool —— 一条消息发 N 个 Task 调用 = 真并行,不需要人工开多窗口、不需要 SDK。
when_to_use: decomposition.json 写好且用户确认后,主 session 走到"我现在该实施了"那一步。
when_NOT_to_use: 单任务(没有并行子任务)—— 直接走 implementer。
---

# Skill: Parallel Orchestrator

> 你(主 session)是指挥官。**不要自己写代码**——你只决定"派谁干、收谁、整合谁"。
> 实施靠 `subtask-implementer` 子 agent,整合靠 `merger` 子 agent,
> 你的责任是**正确地 fan-out / 等待 / fan-in / 决定下一轮**。

---

## 主循环(伪代码,贴近 Claude Code 真实 API)

```python
dag = read_json("state/orchestration/<task-id>/decomposition.json")

for round in dag.rounds:
    round_dir = f"state/orchestration/<task-id>/round-{round.round}/"
    mkdir(round_dir)

    # 1. 派发前为每个 sub-task 写 task.md(架构师任务模板)
    for sub in round.subtasks:
        write(f"{round_dir}/{sub.id}.task.md",
              render_architect_task(sub))   # 走 architect-task-writer skill

    # 2. ★ 关键:一条消息发 N 个 Task 调用 = 真并行
    if round.parallel:
        results = parallel_tasks([
            Task(
                subagent_type="subtask-implementer",
                description=sub.id,
                prompt=load(f"{round_dir}/{sub.id}.task.md"),
                # ↓ Claude Code 自动建 git worktree,sub-agent 在隔离 fs 跑
                isolation="worktree",
            )
            for sub in round.subtasks
        ])
        # ↑ 这个调用 BLOCKING——返回时所有 sub-agent 全跑完
    else:
        # 串行轮:逐个跑
        results = [
            Task(
                subagent_type="subtask-implementer",
                description=sub.id,
                prompt=load(f"{round_dir}/{sub.id}.task.md"),
            )
            for sub in round.subtasks
        ]

    # 3. 写结果到 state(每个 sub 一份 .result.md)
    for sub, res in zip(round.subtasks, results):
        write(f"{round_dir}/{sub.id}.result.md", res)

    # 4. 整合本轮——调 merger sub-agent
    merge_report = Task(
        subagent_type="merger",
        description=f"integrate-round-{round.round}",
        prompt=build_merger_prompt(round_dir, round.subtasks),
    )

    # 5. 决策下一步
    if merge_report.has_conflicts:
        # 不要自动解冲突——把决策权回给用户
        ask_user(merge_report.conflicts)
        # 用户答复后:可能修改 decomposition.json + 跑新一轮
        break
    write(f"{round_dir}/round-report.md", merge_report)

# 6. 全部 round 完成
write(f"state/orchestration/<task-id>/final-state.json", aggregated_state)
```

## Task tool 真正的并行语法(Claude Code 实战)

**正确**(并行):
```
[一条消息里发 N 个 Agent 工具调用]
  Agent(subagent_type="subtask-implementer", description="oauth-google", prompt="...")
  Agent(subagent_type="subtask-implementer", description="oauth-github", prompt="...")
  Agent(subagent_type="subtask-implementer", description="oauth-microsoft", prompt="...")
```
Anthropic 协议保证这三个**真同时跑**,主 session 等它们全返回才继续。

**错误**(串行):
```
[消息 1] Agent(... "oauth-google" ...)
等返回...
[消息 2] Agent(... "oauth-github" ...)
等返回...
[消息 3] Agent(... "oauth-microsoft" ...)
```
这是顺序执行,**没有任何加速**。

---

## sub-task 任务包标准格式(写进 task.md)

```markdown
# Sub-task: <id>

## 上下文
你是 N 个并行子 agent 之一,跑在 git worktree 隔离里。
父任务:<原始需求>
本子任务在 DAG 里的位置:Round <N>,与 <其他 sub-id> 并行。

## 你的 scope(只能动这些)
<sub.scope>

## 严禁触及(其他并行任务在改)
<sub.no_touch 列表>

## 验收
<sub.verifies>
做完跑这条命令,绿了再返回。

## 返回格式(主 session 会机械解析)
返回一段 JSON:
{
  "status": "done" | "blocked" | "failed",
  "changed_files": [...],
  "test_output": "...",
  "blockers": [...],   // 如果是 blocked
  "summary": "一句话:做了什么"
}
```

## merger 的输入格式

```markdown
# Merger 任务

## 上下文
Round <N> 的 <K> 个并行子任务已完成。请整合并报告。

## 子任务产出
<sub-1.result.md 内容>
<sub-2.result.md 内容>
...

## 你的工作
1. cd 到主 worktree(集成位置)
2. 按顺序 git merge 每个 sub 分支
3. 每次 merge 后跑一次完整集成测试
4. 任意 merge 冲突 / 测试 fail → 立即 STOP,报告给主 session,**不要尝试自动解**
5. 全部 OK → 写 round-report.md 汇总,返回 has_conflicts=false

## 严禁
- ❌ 修改任何业务代码(merger 只整合,不写)
- ❌ 跳过测试声称 "应该没问题"
```

---

## fan-out 决策清单(每轮派发前问自己)

- [ ] 每个 sub-task 都有清晰的 scope + no_touch?
- [ ] 每个 sub-task 都有客观的 verifies 命令?
- [ ] 这一轮的并行总数 < 5?(超过 5 个,merger 风险陡增,先拆轮)
- [ ] 用户已确认 decomposition.json?

任一 no → 回到 task-decomposer 再决策,不要硬上 fan-out。

## 反模式(BLOCK 自己)

- ❌ N 个 sub-agent 都没有 isolation: worktree —— 必撞 git 状态
- ❌ 派发后用消息 1/2/3 串行调用 —— 没有任何加速,白白多消耗 token
- ❌ merger 自己"擅长决断"修冲突 —— 子任务作者各有意图,merger 凭直觉解 = bug
- ❌ 同一文件被多个 sub.scope 包含 —— decomposer 应该已 BLOCK 这种,你也再扫一遍

## 反递归保护

- subtask-implementer **不允许**再调用 Task 工具(在它的 TOML 里限制)
- 防止"派发出去的 sub-agent 再 fan-out",形成爆炸式并发
- 真有"子任务还能再分解"的情况,**回主 session 决定**(主 session 加新轮)
