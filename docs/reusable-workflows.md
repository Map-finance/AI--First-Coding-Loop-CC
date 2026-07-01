# Reusable Workflow:在别人的仓库里"一行调用"AI 评审

> **先看一眼**:你是不是真的需要远端跑?如果只是**单人测试 / 不要 required check**,
> 用 [`local_review.sh`](../core/scripts/local_review.sh) 在本地跑、吃 Claude Code 订阅,
> 完全不付远端 API 钱。详见 [`local-vs-remote-review.md`](local-vs-remote-review.md)。
> 下面这套是给"有多人协作 / 要 required check / 要审计 log"场景。

> AI--First-Coding-Loop-CC 暴露了一个**GitHub Actions 可复用工作流**(`workflow_call`):
> 任何 repo 在自己的 `.github/workflows/` 里写 4 行 `uses:` 就能拿到全套三趟 AI 评审,
> **不需要拷贝任何文件、不需要 install.sh、未来升级只需改 ref**。

---

## 1. 调用方写法(最简版)

在你的目标仓 `<your-repo>/.github/workflows/pr-review.yml`:

```yaml
name: PR Review
on:
  pull_request:
    branches: [main]
    types: [opened, synchronize, reopened, ready_for_review]

jobs:
  review:
    uses: WILLcis/AI--First-Coding-Loop-CC/.github/workflows/ai-review-reusable.yml@main
    secrets:
      LLM_API_KEY: ${{ secrets.LLM_API_KEY }}
    with:
      provider: openai
      model_default: gpt-5.5
```

**就这些**。下一个 PR 自动跑三趟评审。

---

## 2. 完整参数(全部可选,除了 LLM_API_KEY)

```yaml
jobs:
  review:
    uses: WILLcis/AI--First-Coding-Loop-CC/.github/workflows/ai-review-reusable.yml@v2.2
    secrets:
      LLM_API_KEY: ${{ secrets.LLM_API_KEY }}
    with:
      provider: deepseek                  # 默认 anthropic
      base_url: ''                        # custom provider 才需要
      model_default: deepseek-chat        # 全局默认
      model_quality: deepseek-chat
      model_security: deepseek-reasoner   # 旗舰档
      model_dependency: deepseek-chat
      ref: v2.2                           # 钉版本(强烈推荐,不要用 main)
      python_version: '3.12'
      max_diff_chars: '320000'            # 超大 PR 截断
```

---

## 3. 给不同厂商的"4 行最小调用"模板

### OpenAI / GPT-5.5
```yaml
uses: WILLcis/AI--First-Coding-Loop-CC/.github/workflows/ai-review-reusable.yml@main
secrets: { LLM_API_KEY: ${{ secrets.LLM_API_KEY }} }
with: { provider: openai, model_default: gpt-5.5 }
```

### DeepSeek
```yaml
uses: WILLcis/AI--First-Coding-Loop-CC/.github/workflows/ai-review-reusable.yml@main
secrets: { LLM_API_KEY: ${{ secrets.LLM_API_KEY }} }
with: { provider: deepseek, model_default: deepseek-chat, model_security: deepseek-reasoner }
```

### Anthropic Claude
```yaml
uses: WILLcis/AI--First-Coding-Loop-CC/.github/workflows/ai-review-reusable.yml@main
secrets: { LLM_API_KEY: ${{ secrets.LLM_API_KEY }} }
with: { provider: anthropic, model_default: claude-sonnet-4-6, model_security: claude-opus-4-6 }
```

### Qwen / 阿里通义
```yaml
uses: WILLcis/AI--First-Coding-Loop-CC/.github/workflows/ai-review-reusable.yml@main
secrets: { LLM_API_KEY: ${{ secrets.LLM_API_KEY }} }
with: { provider: qwen, model_default: qwen-plus, model_security: qwen-max }
```

---

## 4. 分支保护:把 reusable workflow 设为 required check

合并到 main 必须过 AI 评审:

1. 你 repo Settings → Branches → Branch protection rule for `main`
2. ✅ Require status checks → 加 **`review / ai-review-gate`**(注意是 `<job-name> / ai-review-gate`)
3. ✅ Do not allow bypassing the above settings

这样故意改坏的 PR 永远合不进 main。

---

## 5. reusable vs 拷贝版 选哪个

| 维度 | reusable(本文) | 拷贝版(`tools/install.sh`) |
|---|---|---|
| 上手速度 | 极快(4 行) | 中(拷一堆文件) |
| 升级方式 | 改 `ref: vX.Y` | 重新 install + diff merge |
| 离线/私有 GitHub Enterprise | 不行(需访问 WILLcis 仓) | 行 |
| 自定义 prompts/scripts | 不行(共享版) | 行 |
| state/ 持久化(triage 历史等) | 不能(只跑评审) | 行(全套自愈环) |
| 适合 | **只想要 AI 评审** | 想完整 harness(自愈环、特性开关、reports) |

**最佳实践**:大部分仓用 reusable workflow 跑 AI 评审就够;少数核心仓用 install.sh 装全套自愈环。

---

## 6. 升级建议:**永远钉 ref 到 tag**,不要 `@main`

```yaml
# ❌ 危险:本仓更新可能在你的下一个 PR 突然改变评审行为
uses: WILLcis/AI--First-Coding-Loop-CC/.github/workflows/ai-review-reusable.yml@main

# ✅ 推荐:钉到具体 tag,主动控制升级时机
uses: WILLcis/AI--First-Coding-Loop-CC/.github/workflows/ai-review-reusable.yml@v2.2
```

每次本仓发新版后,你在目标仓发一个 PR 把 `ref:` 改成新 tag,review 看影响后再合。
这就是 harness 自己的"灰度发布"。

---

## 7. 故障排查

### "Resource not accessible by integration"
调用方仓的 `GITHUB_TOKEN` 权限不够。本 reusable workflow 已声明 `permissions: pull-requests: write`,
但调用方仓 Settings → Actions → General → Workflow permissions 必须设为 "Read and write"(默认是只读)。

### "Unable to checkout WILLcis/AI--First-Coding-Loop-CC"
本仓是私有的话,调用方 GITHUB_TOKEN 没权访问。两个解法:
- (推荐)把本仓设为 public
- 在调用方仓配一个 PAT 通过 secret 传给 `actions/checkout` 的 `token` 输入(需要把 reusable workflow 改造接 secret)

### `gpt-5.5` 模型不存在
ai_review.py 会 fail-safe 返回 stub 文本 + 把错误记进 token-usage,**workflow 不会因模型不存在而崩**。
但你会在 PR 评论里看到 `[模型调用失败 ...]`。这时去 vars 改成有效模型名(如 `gpt-4o`)。
