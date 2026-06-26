# AI 评审四趟扩展 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把现有三趟 AI 评审(quality/security/dependency)扩展为四趟,新增聚焦"性能+韧性+可观测性"的 `performance` 趟,并用一份 13 类问题库为四趟划定职责、把团队真实痛点标为 BLOCK 级。

**Architecture:** 在 `ai_review.py` 的 `PROMPTS` / `PASS_ROLE` 两个注册表各加一项(argparse choices 自动跟随);新增 `review-performance.md` prompt 与 `verifier-performance.toml` agent;`ai-review.yml` 增加一个 performance job 并把它纳入 `ai-review-gate` 的 needs;新增 `issue-checklist.md` 作为四趟共享的问题库总览,并据此补强既有三趟 prompt。`install.sh` 靠通配自动分发新 prompt/agent,无需改。

**Tech Stack:** Python 3(ai_review.py + pytest)+ Markdown(prompt)+ TOML(agent)+ GitHub Actions(YAML)

---

## File Structure

新增:
- `core/prompts/review-performance.md` — 第 4 趟 prompt(问题库 2/3/4/5/7 类)
- `core/prompts/issue-checklist.md` — 13 类问题库总览,四趟共享
- `claude-code/agents/verifier-performance.toml` — 第 4 趟 agent
- `core/scripts/test_ai_review_passes.py` — 注册表单元测试

修改:
- `core/scripts/ai_review.py:38-49` — `PROMPTS` 与 `PASS_ROLE` 各加 performance
- `core/scripts/ai_review.py:11-13` — 更新用法注释
- `core/workflows/ai-review.yml` — 加 performance job + gate needs + 标题改 4 passes
- `core/prompts/review-quality.md` / `review-security.md` / `review-dependency.md` — 按问题库补强职责边界

---

## Task 1: 注册 performance 趟到 ai_review.py(TDD)

**Files:**
- Modify: `core/scripts/ai_review.py:38-49`
- Test: `core/scripts/test_ai_review_passes.py`

- [ ] **Step 1: 写失败测试**

```python
# core/scripts/test_ai_review_passes.py
"""验证四趟评审的注册表完整且自洽。"""
import importlib.util
import pathlib
import sys

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE))  # 让 ai_review 能 import _adapters

spec = importlib.util.spec_from_file_location("ai_review", HERE / "ai_review.py")
ai_review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ai_review)


def test_performance_pass_registered():
    assert "performance" in ai_review.PROMPTS
    assert ai_review.PROMPTS["performance"].endswith("review-performance.md")


def test_performance_role_mapping():
    assert ai_review.PASS_ROLE["performance"] == "verifier-performance"


def test_all_passes_have_role():
    # 每个 PROMPTS 趟都必须有对应 role,否则 main() 里 PASS_ROLE[pass_name] 会 KeyError
    assert set(ai_review.PROMPTS) == set(ai_review.PASS_ROLE)
```

- [ ] **Step 2: 运行测试,确认失败**

Run: `cd core/scripts && python3 -m pytest test_ai_review_passes.py -v`
Expected: FAIL — `test_performance_pass_registered` 报 `'performance' not in PROMPTS`

- [ ] **Step 3: 改 PROMPTS 与 PASS_ROLE(ai_review.py 第 38-49 行)**

把第 38-42 行的 `PROMPTS` 改为:

```python
PROMPTS = {
    "quality":     f"{_PROMPTS_DIR}/review-quality.md",
    "security":    f"{_PROMPTS_DIR}/review-security.md",
    "performance": f"{_PROMPTS_DIR}/review-performance.md",
    "dependency":  f"{_PROMPTS_DIR}/review-dependency.md",
}
```

把第 45-49 行的 `PASS_ROLE` 改为:

```python
# 四趟与 sub-agent 的对应关系(影响 LLM_MODEL_<ROLE> 的覆盖键)
PASS_ROLE = {
    "quality":     "verifier-quality",
    "security":    "verifier-security",
    "performance": "verifier-performance",
    "dependency":  "verifier-dependency",
}
```

- [ ] **Step 4: 运行测试,确认通过**

Run: `cd core/scripts && python3 -m pytest test_ai_review_passes.py -v`
Expected: PASS — 3 passed

- [ ] **Step 5: 更新脚本顶部用法注释(ai_review.py 第 11-13 行)**

把第 11-13 行:

```python
  python3 scripts/ai_review.py --pass quality      # 第 1 趟:质量
  python3 scripts/ai_review.py --pass security     # 第 2 趟:安全
  python3 scripts/ai_review.py --pass dependency   # 第 3 趟:依赖
```

改为:

```python
  python3 scripts/ai_review.py --pass quality      # 第 1 趟:质量
  python3 scripts/ai_review.py --pass security     # 第 2 趟:安全
  python3 scripts/ai_review.py --pass performance  # 第 3 趟:性能/韧性/可观测
  python3 scripts/ai_review.py --pass dependency   # 第 4 趟:依赖
```

- [ ] **Step 6: Commit**

```bash
git add core/scripts/ai_review.py core/scripts/test_ai_review_passes.py
git commit -m "feat(ai-review): register performance pass + tests"
```

---

## Task 2: 新建 13 类问题库总览 issue-checklist.md

**Files:**
- Create: `core/prompts/issue-checklist.md`

- [ ] **Step 1: 创建文件(完整内容)**

```markdown
# AI 评审问题库(13 类)— 四趟共享

每趟评审聚焦自己负责的类别(见各 review-*.md);本表是总览与分工。
标 ⛔ 的是团队历史真实痛点,出现即 **BLOCK**。

## 趟次分工
- **quality 趟**:第 1、9、10、12 类
- **security 趟**:第 6 类
- **performance 趟**:第 2、3、4、5、7 类
- **dependency 趟**:第 13 类

## 13 类
1. 正确性/逻辑:边界、空值、off-by-one、时区/日期、浮点精度、整数溢出、类型转换
2. 并发/异步:竞态、死锁、共享状态、异步未 await、资源泄漏
3. 数据库/持久层:⛔N+1、⛔缺索引、⛔全表、⛔SELECT *、大/长事务、锁竞争、缺分页、未参数化、迁移不可回滚、数据兼容
4. 外部依赖/韧性:⛔无超时、⛔无重试退避、无熔断降级、⛔无幂等、⛔无限流、级联失败
5. 性能:热路径重复计算、缓存击穿穿透雪崩、大 payload、序列化;前端重渲染/bundle/内存泄漏/长列表
6. 安全:注入、越权(鉴权vs授权)、密钥硬编码、⛔敏感信息进日志、SSRF/CSRF、不安全反序列化、过度权限
7. 错误处理/可观测性:⛔吞异常、错误未分级、⛔缺埋点/监控、缺 trace_id/上下文、⛔日志不结构化、缺健康检查
8. API/契约:破坏性变更、版本兼容、契约不一致、文档未同步、状态码/错误格式、入参校验
9. 代码质量/可维护:命名、注释 why、复杂度、重复、职责单一、抽象层级、过度设计、魔法值、死代码
10. 测试:覆盖率、边界/异常路径、别测实现细节、缺集成/契约测试、可读性
11. 配置/部署/运维:特性开关、环境隔离、回滚、迁移与代码解耦、资源限制与超时
12. 文档:接口/DB/模块说明随代码更新、ADR
13. 依赖管理:必要性、许可证、体积、维护状态、已知漏洞
```

- [ ] **Step 2: 验证**

Run: `grep -c '⛔' core/prompts/issue-checklist.md`
Expected: 数字 ≥ 10

- [ ] **Step 3: Commit**

```bash
git add core/prompts/issue-checklist.md
git commit -m "docs(review): add 13-category issue checklist shared by four passes"
```

---

## Task 3: 新建 review-performance.md prompt

**Files:**
- Create: `core/prompts/review-performance.md`

- [ ] **Step 1: 创建文件(完整内容,自包含 2/3/4/5/7 类)**

```markdown
# 评审 Pass 3 — 性能 / 韧性 / 可观测性

你是这个 monorepo 的高级评审员,负责**性能、韧性、可观测性**这一趟。你可以读取整个
仓库(Read/Grep/Glob)理解上下文。这一趟覆盖团队历史上最常出事的维度,从严。

## 你的任务
只评审本 PR 的 diff,结合全仓上下文。聚焦五类(对应问题库第 2/3/4/5/7 类):

### 韧性(外部依赖)— 以下缺失一律 BLOCK
- 外部调用(HTTP/RPC/DB/缓存)**无显式超时**
- 可重试错误**无重试 + 指数退避**;或对**非幂等写操作做了重试**
- 写操作/回调**无幂等键**
- 对外接口**无限流**
- 依赖失败无熔断/降级,可能级联失败

### 数据库/持久层(详见 sql-optimization skill)— 多为 BLOCK
- N+1、缺索引、全表扫描、SELECT *、缺分页、未参数化、大/长事务

### 性能
- 热路径重复计算/分配;缓存击穿穿透雪崩未防护;大 payload
- 前端:不必要重渲染、bundle 膨胀、内存泄漏、长列表未虚拟化

### 并发/异步
- 竞态、共享状态未保护、异步未 await、连接/文件/句柄未释放

### 可观测性 — 结构化日志与埋点缺失按 BLOCK
- 日志非结构化或缺 service/request_id/level;关键路径吞异常或无监控埋点;错误未分级

## 输出格式
对每个发现:
- **严重度**:`BLOCK` / `WARN` / `NIT`
- **位置**:`文件:行`
- **问题**:一句话
- **建议**:可直接采纳的修法,尽量给代码片段

## 判定规则(决定本 job 红/绿)
- 出现任意 `BLOCK` → 结尾输出 `VERDICT: BLOCK`。
- 否则输出 `VERDICT: PASS`。

## 重要
- 你是**门禁**,不是建议箱。但上面标 BLOCK 的痛点项不要手软。
- 不复述 diff,不泛泛表扬,只产出可执行发现。
```

- [ ] **Step 2: 验证**

Run: `grep -c 'VERDICT: BLOCK' core/prompts/review-performance.md`
Expected: 1

- [ ] **Step 3: Commit**

```bash
git add core/prompts/review-performance.md
git commit -m "feat(review): add performance pass prompt"
```

---

## Task 4: 新建 verifier-performance.toml agent

**Files:**
- Create: `claude-code/agents/verifier-performance.toml`

- [ ] **Step 1: 创建文件(完整内容,仿 verifier-quality.toml)**

```toml
name = "verifier-performance"
description = "PR 评审第 3 趟:性能、韧性(超时/重试/熔断/幂等/限流)、可观测性(结构化日志/埋点)。团队真实痛点从严,只对真正影响稳定性/性能的问题给 BLOCK。"
# 推荐档:Anthropic Sonnet / OpenAI gpt-4o / DeepSeek deepseek-chat / Qwen qwen-plus
provider = "anthropic"
model = "claude-sonnet-4-6"
reasoning = "medium"
tools = ["Read", "Grep", "Glob"]
prompt_file = "prompts/review-performance.md"

[budget]
max_input_tokens = 40000
max_output_tokens = 4000
```

- [ ] **Step 2: 验证 TOML 合法**

Run: `python3 -c "import tomllib; tomllib.load(open('claude-code/agents/verifier-performance.toml','rb')); print('ok')"`
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add claude-code/agents/verifier-performance.toml
git commit -m "feat(agents): add verifier-performance agent"
```

---

## Task 5: ai-review.yml 增加 performance job 并纳入 gate

**Files:**
- Modify: `core/workflows/ai-review.yml`(标题第 14 行、新增 job、gate needs 第 84 行)

- [ ] **Step 1: 改标题(第 14 行)**

把 `name: AI Review (3 passes, multi-provider)` 改为 `name: AI Review (4 passes, multi-provider)`

- [ ] **Step 2: 在 `dependency` job 之后、`ai-review-gate` job 之前插入 performance job**

在第 81 行(dependency job 的 run 行)之后、第 83 行(`ai-review-gate:`)之前插入:

```yaml
  performance:
    if: github.event.pull_request.draft == false
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }
      - uses: actions/setup-python@v5
        with: { python-version: '3.12', cache: 'pip' }
      - run: pip install -r scripts/requirements.txt
      - name: Pass 3 — Performance / Resilience / Observability
        env:
          LLM_MODEL_VERIFIER_PERFORMANCE: ${{ vars.LLM_MODEL_VERIFIER_PERFORMANCE }}
        run: python3 scripts/ai_review.py --pass performance

```

- [ ] **Step 3: 把 performance 纳入 gate 的 needs(原第 84 行)**

把 `    needs: [quality, security, dependency]` 改为:

```yaml
    needs: [quality, security, performance, dependency]
```

- [ ] **Step 4: 验证 YAML 合法且四趟齐全**

Run: `python3 -c "import yaml; d=yaml.safe_load(open('core/workflows/ai-review.yml')); j=d['jobs']; assert 'performance' in j; assert set(j['ai-review-gate']['needs'])=={'quality','security','performance','dependency'}; print('ok')"`
Expected: `ok`

(若环境无 yaml:`pip install pyyaml` 后重试。)

- [ ] **Step 5: Commit**

```bash
git add core/workflows/ai-review.yml
git commit -m "feat(ci): add performance job to AI review gate (4 passes)"
```

---

## Task 6: 补强既有三趟 prompt 的职责边界

**Files:**
- Modify: `core/prompts/review-quality.md`
- Modify: `core/prompts/review-security.md`
- Modify: `core/prompts/review-dependency.md`

- [ ] **Step 1: review-quality.md 收窄职责(避免与 performance 趟重叠)**

把 review-quality.md 第 11-14 行的"性能"小节(`2. **性能**:N+1 查询...复杂度。`)替换为:

```markdown
2. **性能与韧性**:本趟**不**深查(交给 performance 趟)。仅当看到明显逻辑性的性能错误
   (如死循环、明显的算法复杂度爆炸)才提 WARN。
```

并在文件末尾(第 30 行后)追加一行:

```markdown

> 本趟负责问题库第 1、9、10、12 类(见 `prompts/issue-checklist.md`)。性能/韧性归 performance 趟,安全归 security 趟。
```

- [ ] **Step 2: review-security.md 末尾追加职责声明**

在 review-security.md 文件末尾追加:

```markdown

> 本趟负责问题库第 6 类(注入、越权、密钥、PII 进日志、SSRF/CSRF、不安全反序列化、过度权限)。详见 `prompts/issue-checklist.md`。
```

- [ ] **Step 3: review-dependency.md 末尾追加职责声明**

在 review-dependency.md 文件末尾追加:

```markdown

> 本趟负责问题库第 13 类(依赖必要性、许可证、体积、维护状态、已知漏洞)。详见 `prompts/issue-checklist.md`。
```

- [ ] **Step 4: 验证三处职责声明都已写入**

Run: `grep -l 'issue-checklist.md' core/prompts/review-quality.md core/prompts/review-security.md core/prompts/review-dependency.md | wc -l`
Expected: `3`

- [ ] **Step 5: Commit**

```bash
git add core/prompts/review-quality.md core/prompts/review-security.md core/prompts/review-dependency.md
git commit -m "docs(review): scope three passes against shared issue checklist"
```

---

## Task 7: 端到端冒烟(mock 跑四趟)

**Files:**(无改动,仅验证)

- [ ] **Step 1: mock 跑新 performance 趟**

Run: `cd core/scripts && AIFCL_PROMPTS_DIR=../prompts python3 ai_review.py --pass performance --mock`
Expected: 打印 `=== MOCK pass=performance role=verifier-performance ...`,退出码 0

- [ ] **Step 2: 确认四趟都能 mock 跑通**

Run: `cd core/scripts && for p in quality security performance dependency; do AIFCL_PROMPTS_DIR=../prompts python3 ai_review.py --pass "$p" --mock >/dev/null 2>&1 && echo "$p ok" || echo "$p FAIL"; done`
Expected: 四行 `... ok`(dependency 无依赖变更时也会因 collect_dep_diff 走 mock 分支前的 0 退出,属正常)

- [ ] **Step 2 注**:若 dependency 趟因本仓无依赖 diff 而提前 `return 0` 打印"未改依赖",也算 ok。

- [ ] **Step 3: 运行单元测试确认仍绿**

Run: `cd core/scripts && python3 -m pytest test_ai_review_passes.py -v`
Expected: 3 passed

---

## Self-Review

对照 spec 覆盖检查:

- **spec §10 评审四趟**:quality/security/performance/dependency 全部就位(Task 1 注册 + Task 3 prompt + Task 4 agent + Task 5 workflow)。✅
- **spec §10 团队痛点标 BLOCK 级**:review-performance.md(Task 3)把无超时/无重试/无幂等/无限流/日志不结构化/缺埋点列为 BLOCK;issue-checklist.md(Task 2)用 ⛔ 标注。✅
- **spec 附录 A 13 类问题库**:issue-checklist.md(Task 2)完整 13 类 + 趟次分工;三趟 prompt 补强引用(Task 6)。✅
- **spec §9.3 双相**:performance 趟职责与 Plan A 的 performance-review skill 内容一致(超时/重试/熔断/幂等/限流/日志/埋点),开发期 skill + 评审期 prompt 同源。✅

类型/命名一致性:`performance` 这一 pass 名在 PROMPTS、PASS_ROLE、prompt 文件名(review-performance.md)、agent 文件名(verifier-performance.toml)、workflow job 名与 needs、env 键(LLM_MODEL_VERIFIER_PERFORMANCE)中全部一致。

无占位符:prompt、toml、workflow 片段、测试均给出完整内容。

依赖关系:本 plan 独立,不依赖 Plan A/C/D 即可执行(performance-review skill 是开发期增强,缺它评审仍能跑)。
