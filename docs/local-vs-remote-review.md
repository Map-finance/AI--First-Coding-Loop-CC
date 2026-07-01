# Local vs Remote 评审:不付双倍钱的架构指南(v2.5)

> 一个常被忽略的问题:**reusable workflow 在 GitHub Actions 里跑,需要它自己的 LLM API key——这不是和我已有的 Claude Code 订阅重复了吗?**
>
> 答:在某些场景下**确实重复,完全不必配远端 key**。这份文档把何时该配远端、何时纯本地讲清楚。

---

## 架构事实(为什么远端"看起来"要 key)

```
你 Mac 上的 Claude Code              GitHub Actions Runner
─────────────────────             ─────────────────────────
认证:  你的订阅 OAuth              认证:  *它自己的* API key
                                       (它认不出你 Mac 的 OAuth session)
触发:  你手动 prompt               触发:  *任何人* 开 PR / push
位置:  你的本地 fs                 位置:  Microsoft 云
```

**核心约束**:GitHub Actions 跑在远端 runner 上,**不认识你 Mac 上的 Claude Code session**。所以它要做评审,必须有自己能用的认证。

---

## 三条路线 + 决策表(选哪条)

| 路线 | 远端 API key | 自动化程度 | 月费(参考) | 适合 |
|---|---|---|---|---|
| **A. Local-only** | ❌ 不要 | 手动 / 半自动 | **$0**(吃订阅) | 单人开发、纯测试期、不要 required check |
| **B. Remote API key**(reusable workflow 默认) | ✅ 独立 key | 全自动 | $18~$80 | 多人协作、要 required check、要审计、跨设备 |
| **C. Claude Code OAuth Action** | ❌ 用订阅 token | 全自动 | 吃订阅额度 | 只用 Claude、放弃多厂商灵活性、有 Claude Code 团队席位 |

**决策树**:

```
有别人(同事/外包/agent)会提 PR 吗?─── 是 ──► 远端,用 B 或 C
                                          │
                                          否
                                          ▼
要不要让 main 分支强制门禁(required check)?─── 是 ──► 远端,用 B 或 C
                                          │
                                          否
                                          ▼
                                       用 A:Local-only,完全不付远端钱
```

---

## A. Local-only(推荐起步)

**怎么做**:

```bash
# 你刚 commit 了一些代码,push 前想评审一下
cd <your-project>
git fetch origin main
bash <(curl -sSL https://raw.githubusercontent.com/WILLcis/AI--First-Coding-Loop-CC/v2.5/scripts/local_review.sh)
# 它会打印三段 prompt(quality/security/dependency),
# 把每段贴进 Claude Code 一个会话,人工 review 完再 push
```

或者更紧凑的 one-shot 三趟:

```bash
bash <(curl -sSL https://raw.githubusercontent.com/WILLcis/AI--First-Coding-Loop-CC/v2.5/scripts/local_review.sh) --combined
# 输出一段总 prompt,让 Claude Code 一次跑完三趟并给 VERDICT
```

**好处**:
- ✅ 零账单——完全吃你 Claude Code 订阅的额度
- ✅ 零远端配置(无需 secret/var、无需 workflow permissions = write)
- ✅ 即改即看——push 前就能拦,不用等 GitHub Actions

**代价**:
- ❌ 你不在线时其他人提 PR 不会被评审
- ❌ 不能做 required check(GitHub 看不到本地 review 结果)
- ❌ 跨设备同事看不到一致策略

## B. Remote API key(reusable workflow 默认)

**怎么做**:见 [`reusable-workflows.md`](reusable-workflows.md) — 4 行 `uses:` + 配 GitHub Secret/Var。

**好处**:全自动、required check 成立、跨设备一致、有审计 log。
**代价**:**每月需要付 LLM API 账单**(独立于 Claude Code 订阅)。

## C. Claude Code OAuth Action(进阶)

Anthropic 官方的 [`anthropics/claude-code-action`](https://github.com/anthropics/claude-code-action) 支持用 **`CLAUDE_CODE_OAUTH_TOKEN`** 代替 `ANTHROPIC_API_KEY`,让 GitHub Actions 走你 Claude Code 订阅的 OAuth token,不付额外 API 费用。

**好处**:无双倍账单、全自动。
**代价**:
- 锁回 Anthropic(失去 v2.1 的"多厂商无关")
- OAuth token 有过期/轮换问题,运维稍复杂
- 需要在 Claude Code 里跑 `claude setup-token` 拿 token,放进 Secret

如果你**只用 Claude、不要多厂商灵活性**,这是最优解。需要的话我们可以加一个 `claude-code-oauth-review.yml` 作为 ai-review-reusable.yml 的 Anthropic 版替代。

---

## 我现在该选哪个?(贴墙上)

| 你的处境 | 选 |
|---|---|
| 我刚开始,自己测试 harness 是否能用 | **A**(完全不配远端,用 `scripts/local_review.sh`) |
| 我一个人,但有 5 个分项目要管 | **A** + 写个脚本自动 review 各项目 |
| 我开始有同事提 PR / 想 required check | **B**(配独立 Anthropic API key) |
| 我已经付 Claude Code Team / 用得很重 | **C**(OAuth,不重复付钱) |
| 我要切 DeepSeek / Qwen 省钱 | **B**(C 不支持非 Anthropic 厂商) |

---

## 反模式

- ❌ 没多人协作 / 没 required check 需求,却配了远端 API key —— 白付钱
- ❌ 配了远端,但本地也手动跑一遍 —— 双倍消耗 token
- ❌ 把 Claude Code 订阅 token 当 API key 用 —— 协议不一样,会失败
- ❌ 觉得"local 不够正式" —— **正式与否取决于谁/什么时候用,不取决于跑在哪台机器**

---

## 升级路径(L → R)

从 Local-only 升到 Remote API key 不是回头路——是**渐进的**:

```
Day 0   纯本地评审,免费验证 harness 价值
Day N   团队增加到 2 人 / 你开始上 CI required check
       ↓
       开 PR 配 GitHub Secret/Var:LLM_API_KEY + LLM_PROVIDER + LLM_MODEL
       开 PR 加 .github/workflows/pr-review.yml
       合并后远端开始 take over,你不用再手动跑 local_review
```

A → B 的迁移只是**加 secret + 加 1 个 workflow 文件**,本地脚本可以继续保留作"push 前快速自检"用。
