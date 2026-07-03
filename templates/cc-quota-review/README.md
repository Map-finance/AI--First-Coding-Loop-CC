# CC 额度三趟 AI 评审模板(claude-code-action)

用 **Claude Code 会员订阅额度**给任意项目的 PR 做 CI 代码评审 —— 不付云厂商 API
token。基于官方 [`anthropics/claude-code-action`](https://github.com/anthropics/claude-code-action),
经多仓生产实测可用。

> 这是 harness 里**最稳的 CI 评审接法**:订阅 OAuth token 由官方 action 正确处理
> (含 Claude Code 身份),比自定义 `ai_review.py` 直连 Messages API 更可靠。

## 装什么

把本目录**整体镜像**到目标项目根(目录结构保持不变):

```
.github/workflows/harness-claude-review.yml   ← 三趟评审 workflow
.harness/prompts/review-quality.md            ← 质量趟提示词
.harness/prompts/review-security.md           ← 安全趟提示词
.harness/prompts/review-dependency.md         ← 依赖趟提示词
```

一行拉取(目标项目根目录执行,同机需有 gh 访问本公开仓的权限):

```bash
mkdir -p .github/workflows .harness/prompts
base=https://raw.githubusercontent.com/WILLcis/AI--First-Coding-Loop-CC/main/templates/cc-quota-review
curl -fsSL "$base/.github/workflows/harness-claude-review.yml" -o .github/workflows/harness-claude-review.yml
for p in review-quality review-security review-dependency; do
  curl -fsSL "$base/.harness/prompts/$p.md" -o ".harness/prompts/$p.md"
done
```

## 三趟分层(改 `claude_args: --model` 即可调档)

| 趟 | 模型 | 说明 |
|---|---|---|
| 质量 | `claude-sonnet-4-6` | 可读性/正确性/复杂度 |
| 安全 | `claude-opus-4-8` | 最贵的档给最该深查的安全趟 |
| 依赖 | `claude-haiku-4-5-20251001` | 形态简单,便宜模型够用 |

`ai-review-gate` 汇总三趟结果。

## 生效前提:设一个 secret

仓库 **Settings → Secrets and variables → Actions** 新建:

- **Name**: `CLAUDE_CODE_OAUTH_TOKEN`
- **Value**: `claude setup-token` 生成的 `sk-ant-oat01-…`(绑 CC 账号,同一串可复用到多仓)

> 用**网页**设;部分环境下 `gh secret set` 因 token 权限报 403 写不了。
> 没配 secret 前评审 check 会红,配好重跑即绿。

## 关键设计点(别删)

- `claude_code_oauth_token: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}` —— 走 CC 额度。
- `github_token: ${{ secrets.GITHUB_TOKEN }}` —— **绕开"必须安装 Claude Code GitHub
  App"**:不传它时 action 走 OIDC 换 app-token,会报 "Claude Code is not installed"。
- `permissions: pull-requests: write` —— 让 action 能贴评审评论。

## 纯文档 PR 自动跳过(省 CI)

workflow 第一个 `changes` job(几秒)判断本 PR 有没有**非文档**改动:

- **纯文档 PR**(只改 `*.md/*.mdx/*.txt/*.rst`、`docs/`、`.harness/prompts/`、`LICENSE`、`CHANGELOG`)
  → 三趟评审(每趟 2–3 分钟)**全部跳过**,不浪费 CI 和模型额度。
- **含代码改动** → 照常跑三趟。

`ai-review-gate` 始终会跑并变绿,所以即便把它设成 required check,纯文档 PR 也**不会被卡住**。
要增删"算文档"的路径,改 `changes` job 里那条 `grep -vE` 的正则。

## 微调

- `dependency` 趟里 `git diff ... -- '**/package.json' 'go.mod' ...` 的依赖文件 glob,
  按项目语言增删。
- 提示词在 `.harness/prompts/*.md`,版本化、可按项目迭代。
