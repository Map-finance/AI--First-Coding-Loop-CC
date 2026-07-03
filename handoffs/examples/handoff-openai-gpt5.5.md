# 接力包:把 harness-v2.1 落地到任意新项目(默认 OpenAI / GPT-5.5)

> **给 Claude Code 的角色定位**:你是 harness 落地 agent。
> 任务是把"AI-First 工程脚手架包(v2.1 模型无关版)"以**安全、可回滚、可自审**的方式合并进**用户指定的任意 GitHub 仓库**。
> 不破坏任何现有代码,**不直接合 main**——开分支 + draft PR,等用户(YY)review 后再合。
>
> **LLM 预设:OpenAI / GPT-5.5**(可随时切换,因为 harness v2.1 已模型无关——只改 GitHub vars/secrets 就行)。

---

## 🛑 检查点 0(开场就要做):问用户三件事

在开始任何 git/clone/写文件操作**之前**,先把这三件事问清楚,缺一不可:

1. **GitHub 仓库 URL**:格式 `https://github.com/<org>/<repo>`
2. **项目代号**(internal name,用于 PR 描述与 CLAUDE.md 描述句)
3. **仓库现状**:
   - (A) 刚建好,基本空(只有 README/LICENSE/.gitignore)
   - (B) 已有代码——主要语言栈是什么?

> ❗ 用户回答之前**不要**继续。这是反"自作主张"的第一道护栏——本接力包是项目无关的,Claude Code 必须从用户处获得项目身份。

---

## 1. 你能拿到什么(物料清单)

- **harness-v2.1 zip 包**:
  路径 `~/Library/Application Support/Claude/local-agent-mode-sessions/.../outputs/creao-ai-first-harness-v2.1.zip`
  - 用 `find ~/Library/'Application Support'/Claude -name 'creao-ai-first-harness-v2.1.zip' 2>/dev/null | head -1` 找
  - 找不到 v2.1 → 用 v2.zip,但告诉用户用的是旧版
  - **不要**自己造一份替代品
- **harness-v2.1 解压目录** `creao-ai-first-harness/`:
  - `CLAUDE.md`(agent 常驻地图,按用户项目实际填)
  - `skills/` 6 个 skill
  - `agents/` 7 个 sub-agent(TOML,**v2.1 起含 `provider` 字段**)
  - `state/` 外置记忆
  - `.github/workflows/` 5 个(ci / deploy / **ai-review** / daily-health / triage)
  - `scripts/` 11 个(含 **`ai_review.py`** 模型无关三趟评审脚本)
  - `flags/feature-flags.ts`
  - `prompts/` 三趟评审提示词
  - `docs/{实施手册.md, Week-0-实施清单.md, v2-升级说明.md, 多模型适配.md}` — **请你也参考 `多模型适配.md`**

---

## 2. LLM 预设清单(本接力包的核心特色)

这次不再用 Anthropic,而是 **OpenAI / GPT-5.5**。

### 2.1 GitHub Repo Secrets/Vars(任务 E 会用 `gh` CLI 批量配)

| 类型 | 键 | 值 | 说明 |
|---|---|---|---|
| Secret | `LLM_API_KEY` | 用户的 OpenAI sk-... | **必填** |
| Var | `LLM_PROVIDER` | `openai` | **必填** |
| Var | `LLM_MODEL` | `gpt-5.5` | 全局默认模型(各 role 未单独覆盖时用这个) |
| Var | `LLM_MODEL_EXPLORER` | `gpt-4o-mini` | 探查档,省钱 |
| Var | `LLM_MODEL_IMPLEMENTER` | `gpt-5.5` | 写代码主力 |
| Var | `LLM_MODEL_VERIFIER_QUALITY` | `gpt-5.5` | 质量评审 |
| Var | `LLM_MODEL_VERIFIER_SECURITY` | `gpt-5.5` | 安全评审(这一档别省) |
| Var | `LLM_MODEL_VERIFIER_DEPENDENCY` | `gpt-4o-mini` | 依赖扫描,廉价模型够 |
| Var | `LLM_MODEL_TRIAGE_SCORER` | `gpt-4o-mini` | triage 大量调用,省钱 |
| Var | `LLM_MODEL_CHECKER` | `gpt-4o-mini` | goal_loop 的 done 判定;**与 implementer 不同即可** |
| Var | `MONTHLY_TOKEN_BUDGET` | `50000000` | 月 token 预算,80% 告警 |

### 2.2 ⚠ GPT-5.5 模型名校验(任务 D 必做)

OpenAI 模型字符串经常变。在写完配置后,**先用一次 API 调用验证 `gpt-5.5` 当前可用**:
```bash
curl -s https://api.openai.com/v1/models -H "Authorization: Bearer $LLM_API_KEY" \
  | python3 -c "import json,sys; ms=[m['id'] for m in json.load(sys.stdin)['data']]; print('gpt-5.5 available:', 'gpt-5.5' in ms); print('candidates:', [m for m in ms if m.startswith('gpt-5')][:5])"
```
- 输出 `gpt-5.5 available: True` → 直接用,继续
- 输出 `False`,但列出 `gpt-5`、`gpt-5-turbo` 等 → 停下来问用户:用哪个替代?把所有 `gpt-5.5` 替换成新名
- 仍找不到 `gpt-5*` → 回退到 `gpt-4o`(最强稳定版),并在 PR 描述里**明确告诉用户**

---

## 3. 任务流(按顺序,带显式停下来问用户的检查点)

### 任务 A — 弄清新仓库的现状(读 + 不写)

1. `gh auth status` 确认 gh CLI 已登录,没登录 → 提示 `gh auth login`
2. `cd ~/projects`(或用户偏好目录,问清楚);`gh repo clone <用户给的 URL>` 或更新已有 clone
3. 用 **TodoWrite** 登记本次任务的子项,持续 TodoRead 更新
4. 进入仓库目录,只读探查:
   ```bash
   ls -la
   cat README.md 2>/dev/null | head -100
   ls .github 2>/dev/null
   ls .github/workflows 2>/dev/null
   git log --oneline -20
   git branch -a
   # 主要语言/技术栈
   find . -maxdepth 3 \
     \( -name 'package.json' -o -name 'go.mod' -o -name 'requirements*.txt' \
        -o -name 'pyproject.toml' -o -name 'Cargo.toml' -o -name 'pom.xml' \
        -o -name 'CMakeLists.txt' -o -name 'Gemfile' \) 2>/dev/null | head -20
   ```
5. 把"现状速写"用 ≤ 12 行写出来:语言栈、目录骨架、是否有现成 CI、是否有 CLAUDE.md、是否有自己的 docs/。

**🛑 检查点 1 — 停下来给用户看现状速写**,等用户确认或纠正,再往下。

### 任务 B — 决定合并策略(根据现状)

仅根据任务 A 的发现,从三种里挑一种 + 写理由:

- **策略 1:空仓 / 几乎空** → 直接把 `creao-ai-first-harness/` 内容平铺到目标根
- **策略 2:有代码但无 CI/CLAUDE.md** → 主体直接拷,**保留**用户原 README.md,把 v2.1 的合并进现有 docs/
- **策略 3:有现成 CI 或冲突结构** → 在仓里建子目录 `.harness/`(或用户偏好名),先并存再渐进迁移;workflow 文件按需重命名避撞

**🛑 检查点 2 — 给用户看策略 + 理由 + 期望影响**,等用户拍板。

### 任务 C — 在新分支上执行合并

用户确认策略后:
1. `git switch -c chore/bootstrap-harness-v2.1`
2. 解压 zip:`unzip -d /tmp/harness-v2.1 "$(找到的 zip 路径)"`
3. 按策略 `rsync`/`cp` 文件进目标仓库(**不要** `cp -rf` 覆盖现有重要文件)
4. **不要触碰**这些已有文件(若存在),除非用户明确同意:
   - 现有 `README.md`(harness 的内容合并到末尾,或单独 `HARNESS-README.md`)
   - 现有 `.gitignore`(只 append harness 的几行,不替换)
   - 现有 `.github/workflows/*.yml`(改名避撞,如 `ci.yml` → `harness-ci.yml`,告诉用户)
   - 现有 `Makefile`、`Dockerfile`、`docker-compose.*`(同上 + 告知)
5. 把 zip 解压后的 `creao-ai-first-harness/` 一层去掉(直接平铺到目标根),避免多套一层

### 任务 D — 把 harness 项目化(填 placeholder + OpenAI/GPT-5.5 配置)

#### D.1 改 `CLAUDE.md`

替换占位:
- 项目描述句:用用户在检查点 0 给的项目代号 + README 里能挖到的真实定位
- 目录结构地图:按任务 A 看到的真实目录改
- 本地起栈命令:照用户项目实际的 `make dev`/`pnpm dev`/`docker compose up`/`cmake ...` 等改
- 安全禁区、特性开关名:先留通用版本,标 TODO 让用户后续填具体业务术语

#### D.2 改 `ci.yml`(按用户实际语言栈裁剪)

`.github/workflows/ci.yml` 已为多语言预留 paths-filter。把用户**实际不存在的语言** job 注释掉:
- 没有 Node → 注释 `node-quality` job
- 没有 Go → 注释 `go-quality` job(已注释,无需动)
- 没有 Python → 注释 `python-quality` job(已注释,无需动)

如果用户项目语言不在 TS/Node/Go/Python 里(比如 C++、Rust、Java、Ruby),**新增一个 job**:
```yaml
cpp:    # 示例
  needs: changes
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - run: cmake -B build && cmake --build build && ctest --test-dir build
```
然后把这个 job 名加入 `ci-gate` 的 `needs` 列表。

#### D.3 ⚠ 验证 GPT-5.5 可用(按第 2.2 节)

跑那条 `curl` 命令验证 `gpt-5.5` 当前真的能调。结果是 `True` 就继续;否则按第 2.2 节回退方案处理。

#### D.4 改 `agents/*.toml` 的 `provider` 字段(可选)

v2.1 的 TOML provider 字段是 fallback——**env 优先**。所以理论上你不必改 TOML,只要在任务 E 设好 GitHub vars 就行。

但为了**让仓库 git 历史里也明确写着"这个项目用 OpenAI"**,把 7 个 TOML 的 `provider = "anthropic"` 改成 `provider = "openai"`,把 `model` 改成下面对应的 OpenAI 模型:

| 文件 | provider | model |
|---|---|---|
| `agents/explorer.toml` | `openai` | `gpt-4o-mini` |
| `agents/implementer.toml` | `openai` | `gpt-5.5` |
| `agents/verifier-quality.toml` | `openai` | `gpt-5.5` |
| `agents/verifier-security.toml` | `openai` | `gpt-5.5` |
| `agents/verifier-dependency.toml` | `openai` | `gpt-4o-mini` |
| `agents/triage-scorer.toml` | `openai` | `gpt-4o-mini` |
| `agents/checker.toml` | `openai` | `gpt-4o-mini` |

#### D.5 (可选)更新 `scripts/token_report.py` 的价表

`scripts/token_report.py` 里 `PRICING_PER_M` 只内置了 Claude 三档。在文件顶部 dict 里 **append** 这两行(用户后续根据 OpenAI 实际定价调整):
```python
PRICING_PER_M["gpt-5.5"]      = (10.0, 30.0)   # 占位估值;OpenAI 公布后改这一行
PRICING_PER_M["gpt-4o"]       = (2.5,  10.0)
PRICING_PER_M["gpt-4o-mini"]  = (0.15, 0.60)
```

#### D.6 跑 5 项本地 sanity 校验

```bash
# 1) env parity
python3 scripts/check_env_parity.py config/.env.dev.example config/.env.prod.example 2>&1 | tail -3

# 2) triage 引擎 mock
OBSERVABILITY_BACKEND=mock TRACKER=github-dryrun python3 scripts/triage_engine.py 2>&1 | tail -4

# 3) ai_review.py 三趟 mock
for p in quality security dependency; do
  python3 scripts/ai_review.py --pass $p --mock 2>&1 | head -2
done

# 4) ModelAdapter 走 openai provider(无 key 时走 stub,验证 token-usage 字段 provider=openai)
LLM_PROVIDER=openai LLM_MODEL=gpt-5.5 OBSERVABILITY_BACKEND=mock python3 scripts/health_report.py >/dev/null 2>&1
python3 -c "
import json
last = open('state/token-usage.jsonl').readlines()[-1]
r = json.loads(last)
assert r['provider']=='openai' and r['model']=='gpt-5.5', f'unexpected: {r}'
print('✓ token-usage records provider=openai model=gpt-5.5')
"

# 5) YAML / TOML 健全性
python3 -c "import yaml,glob; [print('OK',f) for f in sorted(glob.glob('.github/workflows/*.yml')) if yaml.safe_load(open(f))]"
python3 -c "
try: import tomllib as t
except: import tomli as t
import glob
for f in sorted(glob.glob('agents/*.toml')):
    d=t.loads(open(f,'rb').read().decode())
    assert 'provider' in d and 'model' in d, f
    print('OK',f,'provider=',d['provider'],'model=',d['model'])
"
```

**🛑 检查点 3 — 给用户看 5 项 sanity 的结尾输出**。全绿才往下;红 → 停下报错。

### 任务 E — 用 gh CLI 一键配 GitHub vars/secrets

```bash
# 把仓库设为当前 context(避免 --repo 参数)
gh repo set-default <用户给的 URL>

# 必填
read -sp "OpenAI sk-...: " KEY; echo
gh secret set LLM_API_KEY -b"$KEY"

gh variable set LLM_PROVIDER -b"openai"
gh variable set LLM_MODEL    -b"gpt-5.5"

# per-role 模型分层(省钱 + 提质)
gh variable set LLM_MODEL_EXPLORER             -b"gpt-4o-mini"
gh variable set LLM_MODEL_IMPLEMENTER          -b"gpt-5.5"
gh variable set LLM_MODEL_VERIFIER_QUALITY     -b"gpt-5.5"
gh variable set LLM_MODEL_VERIFIER_SECURITY    -b"gpt-5.5"
gh variable set LLM_MODEL_VERIFIER_DEPENDENCY  -b"gpt-4o-mini"
gh variable set LLM_MODEL_TRIAGE_SCORER        -b"gpt-4o-mini"
gh variable set LLM_MODEL_CHECKER              -b"gpt-4o-mini"
gh variable set MONTHLY_TOKEN_BUDGET           -b"50000000"

# 验证
gh secret list
gh variable list
```

**🛑 检查点 4 — 把 secret/variable list 输出给用户看**,确认无误才合并 PR。

### 任务 F — Commit + Push + 开 draft PR(不要合)

```bash
git add -A
git status                                # 给用户看一眼
git commit -m "chore: bootstrap harness v2.1 — OpenAI/GPT-5.5 edition

引入 Addy Osmani《Loop Engineering》5 块积木 + 反认知投降护栏:
- skills/      6 个 skill,按域可发现可调用
- agents/      7 个 sub-agent,模型分层(GPT-5.5 主力 + gpt-4o-mini 探查档)
- state/       外置记忆(triage-history/token-usage/comprehension-log)
- scripts/     +goal_loop.py / spawn_agent_worktree.sh / token_report.py
              +ai_review.py(模型无关三趟评审)
              +comprehension_metrics.py(反认知投降护栏)
- workflows:   ai-review.yml 用任意 LLM;daily-health 含 token+comprehension 周报
- LLM:         OpenAI GPT-5.5(切厂商只改 GitHub vars/secrets)
- docs/        实施手册 + Week-0 清单 + v2 升级说明 + 多模型适配

未启用:deploy.yml 中 AWS 路径(用户尚未开户 AWS,下一阶段处理)。
"
git push -u origin chore/bootstrap-harness-v2.1
gh pr create --draft \
  --title "[harness] bootstrap v2.1 — OpenAI/GPT-5.5 edition" \
  --body "$(cat <<'EOF'
## 这个 PR 在做什么
把 harness v2.1(模型无关版,LLM 默认 OpenAI GPT-5.5)落地到本仓库,作为后续所有功能开发的脚手架。
**这是 draft PR——给用户(YY)自审,通过后再 ready_for_review → merge。**

## 含的东西
- (Claude Code 把任务 D 里改过的关键点列 6~10 条)

## LLM 配置
- Provider: OpenAI
- Default model: gpt-5.5
- Per-role 分层见 agents/*.toml 与 GitHub Variables
- 切换厂商只需改 GitHub vars `LLM_PROVIDER` + secret `LLM_API_KEY`,**无需改代码**
- 详见 `docs/多模型适配.md`

## 不含 / 待办
- AWS 部署链路(`ops/*.sh`、`deploy.yml` 的 AWS 路径)未联调 — 等用户开 AWS 后单独 PR
- `CLAUDE.md` 里仍有 TODO,等用户补具体业务术语
- `token_report.py` 的 gpt-5.5 价格是占位估值,等 OpenAI 公布后调整

## 自审清单
- [ ] CLAUDE.md 描述符合本项目真实情况
- [ ] ci.yml 没注释错语言
- [ ] gpt-5.5 模型确认在 OpenAI 当前可用列表中(任务 D.3 验证过)
- [ ] GitHub Secrets/Vars 已用 `gh secret list` / `gh variable list` 确认
- [ ] 本地 5 项 sanity 命令全绿

## 怎么继续
1. Review 此 PR
2. 确认无误 → Convert to ready for review → 合到 main
3. Week-0 Day 1:分支保护强制化(把 ci-gate / ai-review-gate 设为 required check)
4. Week-0 Day 2:接入 Statsig / Linear / Sentry / Teams 四个服务
5. Week-1 Day 3:接 AWS 部署链路
EOF
)"
```

**🛑 检查点 5 — 给用户:**
- PR URL
- 改了哪些文件、加了哪些文件、**没**碰哪些文件
- 5 项 sanity 命令的 tail 5 行
- GitHub Secrets/Vars 配置确认列表
- 建议用户哪些地方亲自看一眼(战略风险点)

### 任务 G — 报告回来

**不要继续做 Day 1/Day 2 的事**——等用户在 PR 上 review 后单独说"继续"。
报告格式:**先用一句话定性**(成功/部分成功/卡住),再列细节,严格 200 字内。

---

## 4. 检查点总表

| # | 时机 | 给用户看 | 等用户 |
|---|---|---|---|
| **0** | **开场,第一件事** | "我需要这三件事才能开始:仓库 URL / 项目代号 / 是否空仓" | **必答** |
| 1 | 任务 A 完 | 现状速写(≤12 行) | 确认 / 纠正 |
| 2 | 任务 B 完 | 合并策略 + 理由 + 期望影响 | 拍板用哪个策略 |
| 3 | 任务 D.6 完 | 5 项 sanity 的尾部输出 | 全绿继续,有红 → 停 |
| 4 | 任务 E 完 | `gh secret list` + `gh variable list` 输出 | 确认配置完整 |
| 5 | 任务 F 完 | draft PR URL + 改动总结 + 风险点 | 用户自己 review |

## 5. 完成的判据(self-check before reporting)

- [ ] 目标仓库有了一个 draft PR `chore/bootstrap-harness-v2.1`
- [ ] 该 PR 不改动任何已有源码文件(只加新文件 + 改 CLAUDE.md / .gitignore 等 meta)
- [ ] 5 项 sanity 命令在本地全绿
- [ ] GitHub Secrets/Vars 已配齐(至少 1 secret + 10 vars)
- [ ] `gpt-5.5` 模型已验证可用(或已记录回退方案)
- [ ] main 分支毫发无损,可随时不合此 PR

## 6. 反模式(绝对不做)

- ❌ 跳过检查点 0,自己猜项目名 / 仓库
- ❌ 直接 push 到 main
- ❌ 覆盖用户已有的 README.md / Dockerfile / Makefile / 现有 CI
- ❌ 自作主张创建 AWS 资源、合并 PR、改用户 GitHub repo 的分支保护规则
- ❌ 用 `git push --force` 任何分支
- ❌ 让 `CLAUDE.md` 一直留着 `[占位]`
- ❌ `gpt-5.5` 不可用时**默默回退**到其他模型——必须显式告诉用户
- ❌ 把 `LLM_API_KEY` 写进代码、commit 进仓库、或贴在 PR 描述里

## 7. OpenAI / GPT-5.5 专属注意事项

1. **模型字符串可能漂移**:`gpt-5.5` 若 OpenAI 改名(如 `gpt-5.5-turbo`、`gpt-5.5-2026-xx-xx`),只需改一个 GitHub Variable `LLM_MODEL`,代码不动
2. **rate limit 节奏与 Anthropic 不同**:OpenAI tier 限速更宽,但 PR 量大时仍建议三趟评审错峰跑(`concurrency` 已经做了)
3. **token 计费方式**:OpenAI usage 字段是 `prompt_tokens` / `completion_tokens`,v2.1 的 `_adapters.py` 的 OpenAI 兼容路径已正确读取这两个字段
4. **没有 Anthropic 的 prompt caching**:同一 PR 多趟评审会重复计费 system+diff——是 OpenAI 的成本结构差别,无解,但单 PR 月费仍可控

## 8. 你随时可以参考的文档

- `docs/多模型适配.md`(**必读**——8 厂商预设、5 种推荐分层组合、调用解析顺序)
- `docs/v2-升级说明.md`(理解 v2 7 项升级)
- `docs/实施手册.md`(背后的方法论)
- `docs/Week-0-实施清单.md`(参考,但**这次不严格按 Day 划分**,用户已表态)

---

## 给用户(YY)的提示

把这份文件**整体**贴进 Claude Code 的第一个消息,或者:
```
请读 ~/path/to/handoff-new-project-bootstrap-openai.md 并按它的指令从检查点 0 开始,
严格遵守所有 🛑 检查点。
```

Claude Code 会从第一件事——问你"哪个仓库 + 项目代号 + 是否空仓"——开始,你回答后它继续。
全程 5 个检查点,每个你拍板它再往下。
