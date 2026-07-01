# Sub-Agents(v2.1 — 模型无关)

> 把"评审者"扩展为完整角色分工:explorer / implementer / 三类 verifier / triage-scorer / checker。
> 关键原则:**写代码的 agent 不能是判断 done 的 agent**(Addy:maker/checker split)。
> **v2.1 升级**:每个 sub-agent 有 `provider` 字段,可以是 anthropic / openai / deepseek / qwen / kimi / glm 等,
> **切厂商只改两个 env**:`LLM_PROVIDER` + `LLM_API_KEY`(详见 `docs/多模型适配.md`)。

## 在你的项目里怎么放

- **Claude Code**:整体移到 `.claude/agents/`
- **Codex CLI**:整体移到 `.codex/agents/`
- **自建编排**:直接用本目录的 TOML,自己的执行器读 `model` / `reasoning` / `tools` 这三个字段即可

## 模型分层原则(省钱 + 提质两条都顾)

| 角色 | 默认模型 | 推理深度 | 为什么 |
|---|---|---|---|
| `explorer` | Haiku | low | 只读探查,快且便宜,不需要深思考 |
| `implementer` | Sonnet | medium | 写码主力,性价比最高 |
| `verifier-quality` | Sonnet | medium | 关心逻辑/性能/可维护性 |
| `verifier-security` | **Opus** | **high** | 安全错一次代价最大,这里值得花钱 |
| `verifier-dependency` | Haiku | low | 形态简单(版本/许可证),靠规则 + 轻量 LLM 已足够 |
| `triage-scorer` | Sonnet | medium | 大量调用,Sonnet 性价比好 |
| `checker` | Sonnet | medium | goal_loop 的 done 判定,需要稳但不必最贵 |

**单 PR 预估**:从全 Opus 改为分层后,Anthropic API 月费下降 **40~60%**,且 security 趟反而升级到 high reasoning。

## 当前 agents

| name | 主要工具 | 模型 / 推理 | 典型触发 |
|---|---|---|---|
| explorer | Read/Grep/Glob | haiku / low | architect-task-writer 调用前先探查;pr-investigator 第 1 拍 |
| implementer | Read/Write/Edit/Bash | sonnet / medium | 写实现代码 + 自带测试(单任务) |
| **subtask-implementer** ★v2.6 | Read/Write/Edit/Bash | sonnet / medium | **并行多子任务之一**,worktree 隔离,禁 spawn 其他 agent |
| **merger** ★v2.6 | Read/Bash(无 Write) | sonnet / medium | **整合 N 个 sub-agent 产出**,只 git merge + 跑测试,**不写业务代码** |
| verifier-quality | Read/Grep | sonnet / medium | claude-review.yml 第 1 趟 |
| verifier-security | Read/Grep | opus / high | claude-review.yml 第 2 趟 |
| verifier-dependency | Read | haiku / low | claude-review.yml 第 3 趟 |
| triage-scorer | Read | sonnet / medium | triage_engine.py 内部调用 |
| checker | Read/Bash | sonnet / medium | goal_loop.py 的 done 判定 |

## 加一个新 agent

1. 写 TOML 文件:`agents/<name>.toml`
2. 在本 README 表格里加一行
3. 如果新 agent 替换了已有调用点,改 workflow / 脚本里的引用
4. 跑 `python3 scripts/verify_agents.py`(检查 TOML 合法 + 模型名在白名单)
