# core/ — 项目无关 + 模型无关的核心

> 这里的一切**不依赖任何特定项目结构**、**不依赖任何特定 LLM 厂商**。
> 拷到任何 GitHub 仓库都能跑(可能要按你的语言改 ci.yml 里的 paths-filter)。

## 内容

| 子目录 | 用途 | 拷到目标仓的位置 |
|---|---|---|
| `scripts/` | 12 个 Python/Bash 自愈环 + 评审 + loop 脚本 | `scripts/` |
| `workflows/` | 5 个 GitHub Actions YAML | `.github/workflows/` |
| `prompts/` | 4 份评审 + 任务 prompt | `prompts/` |
| `flags/` | 特性开关封装 | `flags/` |
| `state/` | agent 外置记忆的目录约定 | `state/` |

## 关键脚本一句话

- `_adapters.py`:**模型适配器** — 切厂商只改 2 个 env。所有 LLM 调用单点经过这里
- `ai_review.py`:**模型无关的三趟 PR 评审**(替代 anthropics/claude-code-action)
- `triage_engine.py`:错误聚类 → 九维打分 → 去重 → 自动建工单
- `verify_triage.py`:部署后复检,已解决的工单自动关
- `health_report.py`:每日健康摘要(含 token 报告 + 周一 comprehension 报告)
- `goal_loop.py`:**maker/checker 分工的回路** — 跑到验证条件成立才停
- `spawn_agent_worktree.sh`:并行 agent 任务的 fs/docker 隔离
- `token_report.py`:Token 花费聚合 + 月预算外推 + 80% 告警
- `comprehension_metrics.py`:**反认知投降三指标**(coverage / pr-read-rate / modification-rate)
- `check_env_parity.py`:env 模板 key 集合一致性
- `gen_release_notes.py`:AI 生成发布说明

## 切 LLM 厂商

设两个 env(本地或 GitHub Repo Vars/Secrets):

```bash
LLM_PROVIDER=deepseek      # 或 openai / anthropic / qwen / kimi / glm / ...
LLM_API_KEY=sk-...
```

详见 `../docs/多模型适配.md`。

## 本地 5 项 sanity(无需任何 API key)

```bash
python3 scripts/check_env_parity.py /dev/null /dev/null    # 编程友好示例
OBSERVABILITY_BACKEND=mock TRACKER=github-dryrun python3 scripts/triage_engine.py
python3 scripts/ai_review.py --pass quality --mock
python3 scripts/token_report.py --days 1 || echo "(空也 OK)"
python3 scripts/comprehension_metrics.py --mock
```


## v2.3 可选门禁

额外 3 个 workflow(不在默认 ci-gate / ai-review-gate 里,按需 opt-in):

- `workflows/perf-gate.yml` + `scripts/perf_check.py` + `scripts/perf-scenarios/` — k6 p95 vs baseline
- `workflows/image-scan.yml` — Trivy fs + image 双扫
- `workflows/secret-scan.yml` — gitleaks PR diff + 周一全仓深扫

详细启用步骤见 [`../docs/optional-gates.md`](../docs/optional-gates.md)。
