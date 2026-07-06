# Harness 模块化安装(技能包按栈/域 + 分支门禁可配)Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development(推荐)或 superpowers:executing-plans 逐任务实施。步骤用 `- [ ]` 复选框跟踪。

**Goal:** 把 harness 从「整包无差别安装 + 门禁焊死 main」改造为「按技术栈/业务域选装技能包 + 门禁分支安装时可配」,消除语言/业务焊死与 dev 裸奔两个通用性缺陷。

**Architecture:** 三个正交维度组合安装 —— `--profile`(single|monorepo,已有)× `--stacks/--domains`(技能包,新)× `--gate-branches`(门禁分支,新)。技能归类靠 SKILL.md frontmatter 的 `pack:` 标签;install.sh 探测仓库标志物决定默认装哪些包,CLI 参数覆盖;门禁分支靠 install.sh 把 workflow 的 `on:` 段做模板注入。改动落在 harness 源仓(CC + Codex)的 install.sh + skill frontmatter + workflow 模板,消费仓不手改。

**Tech Stack:** Bash(install.sh + 测试)、YAML(GitHub Actions)、Markdown frontmatter(YAML)。两仓并行:AI--First-Coding-Loop-CC(`claude-code/skills`、`.claude`)与 AI--First-Coding-Loop-Codex(`codex/skills`、`.agents`/`.codex`)。

---

## 术语与包分类(单一信源)

一个 skill 属于**恰好一个包**,用 frontmatter 字段 `pack:` 声明。合法值:

| pack 值 | 含义 | 安装条件 |
|---|---|---|
| `universal` | 与栈/域无关,永远装 | 总是 |
| `stack:go` `stack:node` `stack:java` `stack:rust` `stack:python` | 后端语言栈 | `--stacks` 命中 或 探测命中 |
| `frontend:common` | 任意前端通用 | `--stacks frontend` 或探测到任一前端平台 |
| `frontend:web` `frontend:mobile` `frontend:desktop` | 前端具体端 | 对应平台被选中/探测到 |
| `domain:finance` `domain:web3-solidity` | 业务域 | `--domains` 命中 或 探测命中 |

**现有 24 skill 的归类(Phase 1 落地)**:

- `universal`(20):agent-coding-discipline、clean-code、naming-convention、commenting、design-patterns、secure-coding、testing-standards、performance-review、sql-optimization、feature-flag-setup、architect-task-writer、task-decomposer、parallel-orchestrator、pr-investigator、triage-severity-scorer、weekly-comprehension-check、api-endpoint-creator、api-doc-output、data-model-output、changelog-output
- `stack:go`(3):go-logging、go-error-handling、go-observability
- `domain:finance`(1):financial-numerics

**探测标志物(install.sh 默认行为)**:

| 栈/域 | 标志物 |
|---|---|
| go | `go.mod` |
| node(后端) | `package.json` 且依赖含 express/koa/nest/fastify/hapi |
| java | `pom.xml` 或 `build.gradle`(`.kts`) |
| rust | `Cargo.toml` |
| python | `pyproject.toml` 或 `requirements*.txt` |
| frontend:web | `package.json` 依赖含 next/nuxt/react-dom/vue/svelte/@angular/core/vite |
| frontend:mobile | 依赖含 react-native/expo/@ionic 或 存在 `pubspec.yaml`(Flutter) |
| frontend:desktop | 依赖含 electron/@tauri-apps |
| domain:web3-solidity | `foundry.toml` 或 `hardhat.config.*` 或 存在 `*.sol` |
| domain:finance | 不自动探测(业务判断),仅 `--domains finance` 显式启用 |

**门禁分支默认值**:探测该仓真实存在的分支,取 `{默认分支} ∪ ({dev,develop,test,staging} ∩ 实际存在的分支)`;`--gate-branches a,b,c` 覆盖。

---

## 文件结构(创建/修改清单)

**两仓对称改动。下表以 CC 为例,Codex 路径映射:`claude-code/skills`→`codex/skills`,`.claude`→`.agents`/`.codex`,模板 `CLAUDE.*`→`AGENTS.*`。**

- 修改:`claude-code/skills/*/SKILL.md`(24 个,加 `pack:` frontmatter)—— Phase 1
- 创建:`claude-code/skills/PACKS.md`(包清单单一信源,人读 + 校验用)—— Phase 1
- 修改:`tools/install.sh`(参数 `--stacks/--domains/--frontend-platforms/--gate-branches/--list-packs` + 探测函数 + skill 筛选 + workflow 分支注入)—— Phase 2、3
- 创建:`tools/detect_stacks.sh`(可被 install.sh source 的探测函数库,单测友好)—— Phase 2
- 创建:`tools/gate_branches.sh`(把 `on:` 段按分支列表重写的函数库)—— Phase 3
- 创建:`tools/install_matrix.test.sh`(装到临时目录、断言选装结果的集成测试)—— Phase 2、3
- 修改:`core/workflows/{ci,ci.single,ai-review}.yml`、`.github/workflows/self-review.yml`、`templates/cc-quota-review/.github/workflows/harness-claude-review.yml`(把 `branches: [main]` 改成占位 `branches: [__GATE_BRANCHES__]`,由 install.sh 注入;源文件里占位默认渲染成 `[main]` 保持独立可用)—— Phase 3
- 创建:`claude-code/skills/<新包>/...`(Phase 4 各技能包)
- 修改:`docs/多模型适配.md` 同级新增 `docs/技能包与门禁配置.md`(使用文档)—— Phase 5
- 修改:`README.md`(安装姿势加 `--stacks/--gate-branches` 说明)—— Phase 5

---

## Phase 1 — 技能包分类打标签(两仓 24 skill)

**目标:** 每个 SKILL.md frontmatter 加 `pack:` 字段;建立 `PACKS.md` 单一信源。纯元数据,不改 skill 正文。

### Task 1.1:建立 PACKS.md 单一信源

**Files:** Create `claude-code/skills/PACKS.md`(Codex:`codex/skills/PACKS.md`)

- [ ] **Step 1:** 写 `PACKS.md`,内容为上文「术语与包分类」表 + 探测标志物表 + 「加新包/新 skill 时必须在此登记」的约定。
- [ ] **Step 2:** Commit `docs(skills): add PACKS.md pack taxonomy single-source`。

### Task 1.2:给 20 个 universal skill 打标签

**Files:** Modify `claude-code/skills/{agent-coding-discipline,clean-code,naming-convention,commenting,design-patterns,secure-coding,testing-standards,performance-review,sql-optimization,feature-flag-setup,architect-task-writer,task-decomposer,parallel-orchestrator,pr-investigator,triage-severity-scorer,weekly-comprehension-check,api-endpoint-creator,api-doc-output,data-model-output,changelog-output}/SKILL.md`

- [ ] **Step 1:** 对每个文件,在 frontmatter 的 `name:` 行后插入一行 `pack: universal`。用脚本(zsh 注意用字面列表,不要 `for x in $VAR`):

```bash
CC=/path/to/AI--First-Coding-Loop-CC/claude-code/skills
for s in agent-coding-discipline clean-code naming-convention commenting design-patterns \
         secure-coding testing-standards performance-review sql-optimization feature-flag-setup \
         architect-task-writer task-decomposer parallel-orchestrator pr-investigator \
         triage-severity-scorer weekly-comprehension-check api-endpoint-creator api-doc-output \
         data-model-output changelog-output; do
  perl -i -pe 's/^(name:.*)$/$1\npack: universal/ if $. <= 5 && !$done{$ARGV}++' "$CC/$s/SKILL.md"
done
```

- [ ] **Step 2:** 校验:`grep -L '^pack:' $CC/{那20个}/SKILL.md` 应为空(全部有 pack 行)。
- [ ] **Step 3:** Commit `feat(skills): tag 20 universal skills with pack frontmatter`。

### Task 1.3:给 stack:go(3)与 domain:finance(1)打标签

**Files:** Modify `claude-code/skills/{go-logging,go-error-handling,go-observability}/SKILL.md`、`claude-code/skills/financial-numerics/SKILL.md`

- [ ] **Step 1:** go 三件套插入 `pack: stack:go`;financial-numerics 插入 `pack: domain:finance`。
- [ ] **Step 2:** 校验全 24 skill 都有唯一 `pack:` 行:`grep -c '^pack:' $CC/*/SKILL.md` 每个为 1。
- [ ] **Step 3:** Commit `feat(skills): tag go stack + finance domain packs`。

### Task 1.4:Codex 仓同步 Task 1.1–1.3

- [ ] **Step 1:** 在 `codex/skills/` 重复 1.1–1.3(路径映射)。
- [ ] **Step 2:** 校验两仓 `pack:` 标签一致:对每个同名 skill diff frontmatter 的 pack 行。
- [ ] **Step 3:** Commit(Codex 仓)。

---

## Phase 2 — install.sh 按包选装 + 探测

**目标:** `--stacks/--domains/--frontend-platforms/--list-packs` + 自动探测 + universal 永远装。默认行为(无参数)= 探测。

### Task 2.1:探测函数库 detect_stacks.sh(TDD)

**Files:** Create `tools/detect_stacks.sh`;Test `tools/install_matrix.test.sh`

- [ ] **Step 1(写失败测试):** 在 `install_matrix.test.sh` 写:造临时目录放 `go.mod` → `detect_stacks <dir>` 输出应含 `stack:go`;放含 `"react-dom"` 的 package.json → 含 `frontend:web`;放 `Cargo.toml` → `stack:rust`;放 `foundry.toml` → `domain:web3-solidity`。

```bash
test_detect() {
  d=$(mktemp -d); echo 'module x' > "$d/go.mod"
  out=$(detect_stacks "$d")
  case "$out" in *stack:go*) echo PASS ;; *) echo "FAIL: $out"; exit 1 ;; esac
}
```

- [ ] **Step 2(跑,看失败):** `bash tools/install_matrix.test.sh` → FAIL(detect_stacks 未定义)。
- [ ] **Step 3(最小实现):** 写 `detect_stacks()`,按上文标志物表输出以空格分隔的 pack 前缀集合(`stack:go`、`frontend:web`、`domain:web3-solidity`…)。package.json 依赖判断用 `grep -E`(不引 jq,保持零依赖)。
- [ ] **Step 4(跑,看通过):** `bash tools/install_matrix.test.sh` → PASS。
- [ ] **Step 5:** Commit `feat(tools): add detect_stacks.sh with tests`。

### Task 2.2:install.sh 参数解析 + skill 按 pack 筛选

**Files:** Modify `tools/install.sh`(参数区 line 28–46;skill 拷贝段 line 159–170)

- [ ] **Step 1:** 参数区加 `STACKS=""`、`DOMAINS=""`、`FE_PLATFORMS=""`、`LIST_PACKS=0`,case 加 `--stacks) STACKS="$2"; shift`、`--domains`、`--frontend-platforms`、`--list-packs`。source `detect_stacks.sh`。
- [ ] **Step 2:** 计算生效包集合 `SELECTED`:
  - 若 `--stacks`/`--domains` 任一非空 → 用显式值;否则 `SELECTED=$(detect_stacks "$TARGET")`。
  - `--stacks frontend` 展开为 `frontend:common` + (`--frontend-platforms` 指定的 `frontend:<p>`,默认取探测到的前端平台)。
  - 永远并入 `universal`。
- [ ] **Step 3:** 改 skill 拷贝循环:读每个源 skill 的 `pack:` 值,`case` 判断是否 ∈ `SELECTED`,否则跳过并 `skip "跳过 <name>(pack=<pack> 未选中)"`。
- [ ] **Step 4:** `--list-packs`:打印每个源 skill 的 name+pack,`exit 0`(不安装)。
- [ ] **Step 5:** 更新 `--help`(sed 行范围)与顶部用法注释,列出新参数。
- [ ] **Step 6:** `bash -n tools/install.sh` 语法通过。
- [ ] **Step 7:** Commit `feat(install): select skills by pack via --stacks/--domains + autodetect`。

### Task 2.3:install 矩阵集成测试

**Files:** Modify `tools/install_matrix.test.sh`

- [ ] **Step 1(写测试):** 造 3 个临时「目标仓」:①只有 go.mod ②package.json(react-dom)③go.mod+package.json(express)。分别 `bash install.sh <t> --no-... ` 后断言 `.claude/skills/` 里:① 有 go-logging、无 financial-numerics、无前端包;② 有 frontend:* 包、无 go-*;③ 同时有 go-* 与 node 后端包。universal 三种都在。
- [ ] **Step 2(跑):** 期望 PASS。
- [ ] **Step 3:** Commit `test(install): pack selection matrix`。

### Task 2.4:Codex 仓同步 2.1–2.3(路径映射 `.agents/skills`)

- [ ] Steps:重复,commit。

---

## Phase 3 — 门禁分支安装时可配

**目标:** install.sh `--gate-branches`,把 gating workflow 的 `on:` 注入 push+pull_request 分支列表;默认探测存在的环境分支。**只改门禁类**(ci、ci.single、ai-review、self-review/self-test、harness-claude-review 模板);secret-scan/image-scan/perf-gate 保持各自 main 专属逻辑。

### Task 3.1:workflow 源文件占位化

**Files:** Modify `core/workflows/ci.yml`(line 17)、`core/workflows/ci.single.yml`(line 15)、`core/workflows/ai-review.yml`(line 19)、`.github/workflows/self-review.yml`、`.github/workflows/self-test.yml`、`templates/cc-quota-review/.github/workflows/harness-claude-review.yml`

- [ ] **Step 1:** 把这些文件里 `pull_request:` 下的 `branches: [main]` 改为 `branches: [main]  # gate-branches`(保留 main 独立可跑);并在 `on:` 下补 `push:\n    branches: [main]  # gate-branches`(ci/ai-review 原本无 push 触发,补上以拦直推)。注意 ci.yml 保留 `merge_group:`。
- [ ] **Step 2:** `python3 -c "import yaml,glob; [yaml.safe_load(open(f)) for f in [...]]"` 校验 YAML 合法。
- [ ] **Step 3:** Commit `refactor(ci): mark gate-branch triggers for install-time templating`。

### Task 3.2:gate_branches.sh 重写函数(TDD)

**Files:** Create `tools/gate_branches.sh`;Test `tools/install_matrix.test.sh`

- [ ] **Step 1(写失败测试):** 造一个含 `# gate-branches` 标记的临时 yml,`apply_gate_branches <file> "main dev test"` 后,断言该文件 push 与 pull_request 的 branches 均为 `[main, dev, test]`。
- [ ] **Step 2(跑,失败)。**
- [ ] **Step 3(实现):** `apply_gate_branches()` 用 awk/perl 把带 `# gate-branches` 标记行的 `branches: [...]` 替换为给定列表。`default_gate_branches <repo>`:`git -C <repo> branch --format='%(refname:short)'` ∩ `{dev,develop,test,staging}` ∪ 默认分支。
- [ ] **Step 4(跑,通过)。**
- [ ] **Step 5:** Commit `feat(tools): add gate_branches.sh with tests`。

### Task 3.3:install.sh 接入 --gate-branches

**Files:** Modify `tools/install.sh`

- [ ] **Step 1:** 参数加 `GATE_BRANCHES=""`,case `--gate-branches)`。source `gate_branches.sh`。
- [ ] **Step 2:** 落 workflow 后:`branches=${GATE_BRANCHES:-$(default_gate_branches "$TARGET")}`;对已铺到目标仓的门禁 workflow 逐个 `apply_gate_branches`。
- [ ] **Step 3:** `--help` + 用法注释更新;安装结尾提示打印生效的门禁分支。
- [ ] **Step 4:** `bash -n` 通过。
- [ ] **Step 5:** Commit `feat(install): configurable CI/AI-review gate branches`。

### Task 3.4:门禁分支矩阵测试 + Codex 同步

- [ ] **Step 1(测试):** 装到造了 `dev`、`test` 分支的临时仓,断言 ci.yml/ai-review.yml 的 branches 含 dev、test;`--gate-branches main` 覆盖后只含 main。
- [ ] **Step 2:** Codex 仓同步 3.1–3.3(`AGENTS`/`self-review` 对应文件)。
- [ ] **Step 3:** Commit 两仓。

---

## Phase 4 — 新技能包内容(按包独立可执行)

**说明:** 本阶段是**内容创作**,不是机械代码。每个新 skill 遵循现有 SKILL.md 模板(frontmatter:`name`/`pack`/`description`/`when_to_use`/`when_NOT_to_use` + 正文:强制规则 + 反模式 + 判定标准),风格对齐 go-logging/secure-coding。每个包一个独立子任务,可分派并行 agent 各写一包。**每 skill 必须带正确 `pack:` 标签并登记进 PACKS.md 与 skills/README.md。** 两仓对称落地。

### Task 4.1:frontend:common(任意前端通用)

**Files:** Create `claude-code/skills/{fe-component-structure,fe-state-management,fe-accessibility,fe-i18n,fe-form-validation,fe-perf-budget,fe-error-boundary}/SKILL.md`(`pack: frontend:common`)

- [ ] 每个 skill 覆盖:组件职责单一/受控与非受控边界;状态分层(本地/全局/服务端缓存)禁滥用全局;a11y(语义标签/键盘/aria/对比度);i18n(禁硬编码文案/复数/RTL);表单校验(客户端≠信任、与后端规则同源);性能预算(bundle 体积/懒加载/图片);错误边界与降级 UI。
- [ ] 登记 + commit `feat(skills): frontend:common pack`。

### Task 4.2:frontend:web

**Files:** Create `claude-code/skills/{web-rendering-strategy,web-seo,web-core-vitals,web-hydration}/SKILL.md`(`pack: frontend:web`)

- [ ] 覆盖:SSR/SSG/CSR 选型与数据获取边界;SEO(元数据/结构化数据/canonical);Core Web Vitals(LCP/CLS/INP 预算与常见回归);hydration 不匹配与流式渲染陷阱。

### Task 4.3:frontend:mobile(多端之一)

**Files:** Create `claude-code/skills/{mobile-navigation,mobile-offline-state,mobile-list-perf,mobile-native-permissions,mobile-platform-parity}/SKILL.md`(`pack: frontend:mobile`)

- [ ] 覆盖:导航栈与深链;离线优先/同步冲突;长列表虚拟化与掉帧;原生权限申请时机与降级;iOS/Android 平台差异一致性。RN 与 Flutter 各给要点。

### Task 4.4:frontend:desktop(多端之一)

**Files:** Create `claude-code/skills/{desktop-ipc-security,desktop-auto-update,desktop-packaging,desktop-native-integration}/SKILL.md`(`pack: frontend:desktop`)

- [ ] 覆盖:Electron/Tauri 主进程↔渲染进程 IPC 最小权限与禁 nodeIntegration 滥用;签名与自动更新通道;打包体积/多平台产物;托盘/菜单/文件关联等原生集成。

### Task 4.5:stack:node(后端)

**Files:** Create `claude-code/skills/{node-logging,node-error-handling,node-async-discipline,node-middleware,node-observability}/SKILL.md`(`pack: stack:node`)

- [ ] 覆盖:结构化日志(pino,禁 console.log,含 request-id);错误处理(区分可运营/编程错、禁吞 promise rejection、集中错误中间件);async 纪律(禁未 await、并发用 Promise.all 有界、AbortController 超时);中间件顺序与鉴权前置;OTel/prom-client 埋点在中间件层。

### Task 4.6:stack:rust

**Files:** Create `claude-code/skills/{rust-error-handling,rust-ownership-discipline,rust-concurrency,rust-logging}/SKILL.md`(`pack: stack:rust`)

- [ ] 覆盖:`Result`/`?`/`thiserror`(库)vs `anyhow`(应用)、禁 `unwrap`/`expect` 于可恢复路径;所有权/借用/生命周期常见误用与 clone 滥用判定;并发(`Send`/`Sync`、tokio 任务、避免持锁 await);`tracing` 结构化日志与 span。

### Task 4.7:domain:web3-solidity

**Files:** Create `claude-code/skills/{sol-security,sol-gas-optimization,sol-arithmetic-safety,sol-upgradeability,sol-testing}/SKILL.md`(`pack: domain:web3-solidity`)

- [ ] 覆盖:安全(重入/checks-effects-interactions/访问控制/tx.origin/低级 call 检查返回);gas(storage 布局/短路/批量);算术(0.8 溢出检查与 unchecked 边界、定点小数);可升级(proxy 存储冲突/initializer);测试(foundry/hardhat、fuzz、价格预言机操纵与闪电贷场景)。**与 universal 的 secure-coding 交叉引用,不重复通用条目。**

### Task 4.8:stack:java + stack:python(补齐后端矩阵)

**Files:** Create `claude-code/skills/{java-logging,java-error-handling,java-spring-patterns,java-observability}/SKILL.md`(`pack: stack:java`);`{python-logging,python-typing,python-error-handling,python-observability}/SKILL.md`(`pack: stack:python`)

- [ ] Java:slf4j 结构化日志、受检/非受检异常边界、Spring 依赖注入与事务边界、Micrometer 埋点。
- [ ] Python:structlog/logging、类型标注 + mypy 严格、异常链与自定义异常、OTel。

### Task 4.9:探测与 PACKS.md 补全

- [ ] **Step 1:** 确认 `detect_stacks.sh` 覆盖所有新包标志物(Phase 2 已写,补 mobile 的 `pubspec.yaml`、desktop 的 tauri)。
- [ ] **Step 2:** PACKS.md、skills/README.md、AGENTS/CLAUDE 模板的「强制加载表」按需补入新包(仅在对应栈项目里生效,用「适用范围」列标注)。
- [ ] **Step 3:** 两仓 commit。

---

## Phase 5 — 文档 + 收口

### Task 5.1:使用文档

**Files:** Create `docs/技能包与门禁配置.md`;Modify `README.md`

- [ ] 写:三维安装矩阵(profile × stacks/domains × gate-branches)、探测规则表、`--stacks/--domains/--frontend-platforms/--gate-branches/--list-packs` 用法与示例(纯前端 web、Go 后端、node+java 全栈、web3);README「怎么用」补 `--stacks`/`--gate-branches` 姿势。
- [ ] Commit。

### Task 5.2:全量 verify + 两仓一致性

- [ ] **Step 1:** 跑 `tools/install_matrix.test.sh`(两仓)全绿;`tools/verify.sh` 通过。
- [ ] **Step 2:** 抽验:纯前端仓不落 go-*/financial;Go 仓不落前端包;universal 恒在;门禁分支按 `--gate-branches`/探测生效。
- [ ] **Step 3:** Commit `docs+test: modular install matrix green`。

---

## Self-Review(计划自检)

- **Spec 覆盖:** ①技能包按栈(Phase 1/2/4)②单仓多仓(复用既有 `--profile`,Phase 无需新增,文档 5.1 说明正交)③前端多端/单端(Phase 4.1–4.4 + `--frontend-platforms` 探测,Phase 2.2 Step 2)④rust/web3(4.6/4.7)⑤分支安装时可配 + 默认环境分支 + CLI 覆盖(Phase 3)——全覆盖。
- **无占位:** Phase 1–3、5 为机械/脚本任务,给了命令与断言;Phase 4 明确标注为内容创作,给了每包的 skill 文件名与主题清单(非「TODO」,是可执行的作者任务)。
- **命名一致:** `pack:` 字段、`detect_stacks`/`apply_gate_branches`/`default_gate_branches` 函数名在 Phase 2/3 定义并在测试中引用一致;包值 `stack:*`/`frontend:*`/`domain:*` 全程一致。
- **风险:** package.json 探测前端 vs node 后端可能重叠(全栈仓两者都装,是期望行为);`# gate-branches` 标记注入需保证源文件默认渲染仍是合法的 `[main]`(Task 3.1 保证独立可跑)。

---

## 执行说明

- **两仓对称**:每个 Phase 在 CC 落地后,同 Phase 的 Codex 子任务紧随(路径映射固定)。
- **Phase 4 可并行**:8 个包彼此独立,适合每包一个 subagent 并行创作(见 superpowers:subagent-driven-development / dispatching-parallel-agents)。
- **顺序**:Phase 1 → 2 → 3 为基础设施(必须先做,互有依赖);Phase 4 依赖 Phase 1 的 `pack:` 约定但各包间独立;Phase 5 收口。
