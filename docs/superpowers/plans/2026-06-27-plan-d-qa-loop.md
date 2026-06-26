# 测试闭环 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在合并到 main 后自动生成 `qa-task` 测试任务、由 QA 按模板提交测试报告、再由测试 agent 审核报告并 PASS 关单 / BLOCK 打回，落地 spec 第 6 节流程后半段的测试闭环。

**Architecture:** 复用 AIFCL 既有的 `_adapters.py`（`ModelAdapter` 读 diff / 调模型，`TrackerAdapter` 建单关单）与 `state/*.jsonl` append-only 记账模式。新增两个 Python 脚本（`gen_test_tasks.py` 生成测试任务、`qa_review.py` 审核报告），仿 `ai_review.py` 的 PASS/BLOCK verdict 与 `triage_engine.py`/`verify_triage.py` 的建单/复检逻辑。一个 `qa-handoff.yml` workflow 把两者分别挂在 push-to-main 与 issue_comment 两个触发点上。所有新文件靠 `install.sh` 现有通配规则自动分发，**无需改 install.sh**。

**Tech Stack:** Python 3 + _adapters.py(ModelAdapter/TrackerAdapter) + GitHub Actions + gh CLI

---

## File Structure

新增文件（install.sh 已有通配规则覆盖 `core/scripts/*`、`core/prompts/*.md`、`core/workflows/*.yml`、`claude-code/agents/*.toml`；`templates/` 随仓 clone 即得，无需 install.sh 改动）：

| 文件 | 职责 |
|---|---|
| `core/scripts/gen_test_tasks.py` | 合并到 main 后触发：读本次合并 diff → `ModelAdapter` 生成「测试用例+测试流程+验收标准」→ 用 GitHub Issues（`gh` CLI，仿 ai_review.py 的 gh 用法）在**本代码仓**建 `qa-task` 类型 issue，正文内嵌测试报告模板段。建单后 append `state/qa-history.jsonl`（action=created）。仿 triage_engine 建单 + gen_release_notes 读 diff。 |
| `core/scripts/qa_review.py` | QA 在 `qa-task` issue 下评论提交测试报告后触发：读评论正文 → `ModelAdapter` 核对（是否覆盖全部验收点？是否附证据？）→ 输出 `VERDICT: PASS`/`VERDICT: BLOCK`（仿 ai_review）。PASS → 关单 + append `state/qa-history.jsonl`(action=passed)；BLOCK → 在 issue 留言打回（仿 verify_triage 复检/回测）+ append(action=blocked)。 |
| `core/prompts/gen-test-tasks.md` | 生成测试任务的 prompt（喂给 ModelAdapter）。 |
| `core/prompts/review-qa-report.md` | 审核测试报告的 prompt（喂给 ModelAdapter，要求末尾给 VERDICT）。 |
| `claude-code/agents/qa-generator.toml` | qa-generator 角色 agent 定义，绑定 gen-test-tasks.md。 |
| `claude-code/agents/qa-reviewer.toml` | qa-reviewer 角色 agent 定义，绑定 review-qa-report.md。 |
| `core/workflows/qa-handoff.yml` | push/merge 到 main → gen_test_tasks；issue_comment（issue 带 qa-task 标签）→ qa_review。 |
| `templates/team-ops/issue-templates/qa-report.yml` | 测试报告结构化模板（GitHub Issue Form 形态，QA 据此填）。 |
| `core/scripts/test_gen_test_tasks.py` | gen_test_tasks 的 pytest（TDD）。 |
| `core/scripts/test_qa_review.py` | qa_review 的 pytest（TDD）。 |

> `state/qa-history.jsonl` 为运行时产物，由脚本首次运行时自动创建（沿用 `_adapters._state_dir()` 的 `state/` 解析），无需在仓库预置空文件。

---

### Task 1: `gen_test_tasks.py` —— 读合并 diff 生成 qa-task issue（TDD）

**Files:**
- `core/scripts/gen_test_tasks.py`（新建）
- `core/scripts/test_gen_test_tasks.py`（新建）

被测函数全部为纯函数 / 可注入：`collect_merge_diff`、`build_qa_task_body`、`append_qa_history`、`make_qa_title`。`append_qa_history` 自包含写在本脚本内（仿 `_adapters.append_triage_history`，不改 _adapters.py），落 `state/qa-history.jsonl`。

- [ ] 写失败测试 `core/scripts/test_gen_test_tasks.py`，完整内容：

```python
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import gen_test_tasks as g


def test_make_qa_title_truncates_and_tags():
    title = g.make_qa_title("abc1234", "feat: 新增支付回调幂等校验，避免重复入账问题非常长" * 5)
    assert title.startswith("[qa] ")
    assert "[merge:abc1234]" in title
    assert len(title) <= 120


def test_build_qa_task_body_has_all_sections():
    body = g.build_qa_task_body(
        merge_sha="abc1234",
        generated="## 测试用例\n- TC1: 正常入账\n## 验收标准\n- 幂等",
    )
    # AI 生成段落原样嵌入
    assert "TC1: 正常入账" in body
    # 必带可去重的 merge 标记（仿 triage 的 [fp:..]）
    assert "[merge:abc1234]" in body
    # 必带 QA 报告模板段，提示 QA 在评论里贴报告
    assert "测试报告（QA 填写）" in body
    assert "QA-REPORT" in body


def test_append_qa_history_writes_jsonl(tmp_path, monkeypatch):
    monkeypatch.setattr(g, "STATE", tmp_path)
    g.append_qa_history(merge_sha="abc1234", action="created",
                        issue="42", extra={"repo": "org/svc"})
    line = (tmp_path / "qa-history.jsonl").read_text(encoding="utf-8").strip()
    rec = json.loads(line)
    assert rec["merge_sha"] == "abc1234"
    assert rec["action"] == "created"
    assert rec["issue"] == "42"
    assert rec["repo"] == "org/svc"
    assert "ts" in rec


def test_collect_merge_diff_uses_git(monkeypatch):
    calls = []

    def fake_sh(*args, **kw):
        calls.append(args)
        return "diff --git a/x b/x\n+changed\n"

    monkeypatch.setattr(g, "sh", fake_sh)
    diff = g.collect_merge_diff("abc1234")
    assert "changed" in diff
    # 取 merge commit 自身的改动（first-parent）
    assert any("abc1234" in " ".join(a) for a in calls)


def test_collect_merge_diff_truncates_when_huge(monkeypatch):
    monkeypatch.setattr(g, "sh", lambda *a, **k: "x" * 500000)
    monkeypatch.setenv("QA_GEN_MAX_DIFF_CHARS", "1000")
    diff = g.collect_merge_diff("abc1234")
    assert len(diff) < 2000
    assert "截断" in diff


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
```

- [ ] 跑验证失败：`cd core/scripts && python3 -m pytest test_gen_test_tasks.py -q`
      预期：`ModuleNotFoundError: No module named 'gen_test_tasks'`（脚本还没建）。

- [ ] 写最小实现 `core/scripts/gen_test_tasks.py`，完整内容：

```python
#!/usr/bin/env python3
"""gen_test_tasks — 合并到 main 后，读本次合并 diff 生成测试任务并建 qa-task issue。

落地 spec 第 6 节：合并 → qa-generator 读本次 diff → 生成「测试用例 + 测试流程 +
验收标准」→ 在对应代码仓建 qa-task issue 进测试看板。

设计原则（仿 triage_engine）：只负责"读 diff → 生成 → 建单"，不执行测试、不关单。
建单走 gh CLI（与 ai_review.py 发 PR 评论同源；qa-task issue 落在触发本次合并的
**当前代码仓**，便于 PR/issue 同仓自动关单），生成走 _adapters.ModelAdapter。

本地零凭证试跑（不真正建 issue）：
    python3 scripts/gen_test_tasks.py --merge-sha HEAD --mock
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path

from _adapters import ModelAdapter, STATE

# reusable workflow 场景下 prompts/ 可能不在 cwd（同 ai_review.py 约定）
_PROMPTS_DIR = os.getenv("AIFCL_PROMPTS_DIR", "prompts")
PROMPT_PATH = Path(f"{_PROMPTS_DIR}/gen-test-tasks.md")

# QA 在 issue 评论里贴报告时用此哨兵开头，qa_review.py 据此识别"这是测试报告"
REPORT_SENTINEL = "QA-REPORT"


def sh(*args: str, **kw) -> str:
    return subprocess.run(args, capture_output=True, text=True, **kw).stdout


def collect_merge_diff(merge_sha: str) -> str:
    """取本次合并 commit 自身引入的改动（first-parent diff）。"""
    sh("git", "fetch", "--quiet", "--depth", "2", "origin", merge_sha, check=False)
    diff = sh("git", "diff", f"{merge_sha}^1", merge_sha)
    if not diff.strip():
        # 容错：浅克隆下拿不到父提交时退回 show
        diff = sh("git", "show", "--first-parent", merge_sha)
    cap = int(os.getenv("QA_GEN_MAX_DIFF_CHARS", "240000"))
    if len(diff) > cap:
        diff = diff[:cap] + f"\n\n[…diff 超长，截断到 {cap} 字符；测试任务应据此拆分…]"
    return diff


def make_qa_title(merge_sha: str, subject: str) -> str:
    short = merge_sha[:7]
    base = f"[qa] {subject.strip().splitlines()[0] if subject.strip() else '本次合并'}"
    tag = f" [merge:{short}]"
    room = 120 - len(tag)
    if len(base) > room:
        base = base[: room - 1] + "…"
    return base + tag


def build_qa_task_body(merge_sha: str, generated: str) -> str:
    short = merge_sha[:7]
    return f"""**自动生成的测试任务**（合并标记 `[merge:{short}]`）

> 由 gen_test_tasks（qa-generator）基于本次合并 diff 生成。请勿删除标题里的
> `[merge:..]` 标记（用于去重与回测追溯）。

## 测试用例 / 测试流程 / 验收标准
{generated}

---

## 测试报告（QA 填写）

测试完成后，**在本 issue 下新增一条评论**，按下面结构粘贴报告（首行必须是
`{REPORT_SENTINEL}`，qa-reviewer 据此识别并审核）：

```
{REPORT_SENTINEL}
### 覆盖的验收点
- [ ] <逐条对应上面「验收标准」，勾选并说明结果>
### 测试环境
- <dev/staging、版本、数据准备>
### 证据
- <截图链接 / 日志片段 / 接口响应 / 用例执行记录>
### 结论
- <通过 / 不通过 + 原因>
```

审核结果：qa-reviewer 会回帖 `VERDICT: PASS`（关单）或 `VERDICT: BLOCK`（打回重测）。
"""


def append_qa_history(*, merge_sha: str, action: str,
                      issue: str = "", extra: dict | None = None) -> None:
    """action ∈ {created, passed, blocked}。append-only，仿 _adapters.append_triage_history。"""
    rec = {
        "ts": dt.datetime.now(dt.timezone.utc).isoformat(),
        "merge_sha": merge_sha,
        "action": action,
        "issue": issue,
    }
    if extra:
        rec.update(extra)
    with (STATE / "qa-history.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def create_qa_issue(repo: str, token: str, title: str, body: str) -> str:
    """用 gh CLI 在当前代码仓建 qa-task issue，返回 issue 号（失败返回 ""）。"""
    env = os.environ.copy()
    env["GH_TOKEN"] = token
    out = subprocess.run(
        ["gh", "issue", "create", "--repo", repo,
         "--title", title, "--body", body, "--label", "qa-task"],
        env=env, capture_output=True, text=True, check=False,
    ).stdout.strip()
    # gh 输出 issue URL，取末段号
    return out.rsplit("/", 1)[-1] if out else ""


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--merge-sha", default=os.getenv("MERGE_SHA", "HEAD"))
    p.add_argument("--mock", action="store_true",
                   help="不调真实 LLM、不建 issue，只验证骨架")
    args = p.parse_args(argv[1:])

    merge_sha = args.merge_sha
    repo = os.getenv("GITHUB_REPOSITORY", "")
    token = os.getenv("GITHUB_TOKEN", "")

    if not PROMPT_PATH.exists():
        print(f"::error::找不到 prompt 文件 {PROMPT_PATH}", file=sys.stderr)
        return 2

    base_prompt = PROMPT_PATH.read_text(encoding="utf-8")
    diff = collect_merge_diff(merge_sha)
    if not diff.strip():
        print("本次合并无代码改动，跳过生成测试任务。")
        return 0

    subject = sh("git", "log", "-1", "--pretty=format:%s", merge_sha).strip()
    full_prompt = (
        base_prompt
        + f"\n\n---\n\nMERGE DIFF（commit {merge_sha[:7]}）\n```diff\n{diff}\n```\n"
        + "\n请据此输出该 PR 的「测试用例 + 测试流程 + 验收标准」。"
    )

    if args.mock:
        print(f"=== MOCK gen_test_tasks merge={merge_sha[:7]} prompt_chars={len(full_prompt)} ===")
        generated = "## 测试用例\n- TC1: 占位\n## 验收标准\n- 占位"
    else:
        generated = ModelAdapter.summarize(
            full_prompt, loop="qa-handoff", role="qa-generator",
        )

    title = make_qa_title(merge_sha, subject)
    body = build_qa_task_body(merge_sha, generated)

    if args.mock or not (repo and token):
        print(f"[DRY-RUN] CREATE qa-task issue  {title}")
        print(body[:1200])
        return 0

    issue = create_qa_issue(repo, token, title, body)
    if not issue:
        print("::error::gh issue create 未返回 issue 号", file=sys.stderr)
        return 1
    append_qa_history(merge_sha=merge_sha, action="created",
                      issue=issue, extra={"repo": repo})
    print(f"已建 qa-task issue #{issue}（{title}）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
```

- [ ] 跑验证通过：`cd core/scripts && python3 -m pytest test_gen_test_tasks.py -q`
      预期：`5 passed`。

- [ ] 烟测 mock 路径：`cd core/scripts && python3 gen_test_tasks.py --merge-sha HEAD --mock`
      预期：打印 `=== MOCK gen_test_tasks ...` 与 `[DRY-RUN] CREATE qa-task issue ...`，退出码 0（mock 不依赖 git 历史，diff 为空时打印「无代码改动」也算通过）。

- [ ] commit：

```bash
git add core/scripts/gen_test_tasks.py core/scripts/test_gen_test_tasks.py
git commit -m "feat(qa): gen_test_tasks 读合并 diff 生成 qa-task issue

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: `qa_review.py` —— 审核测试报告 PASS/BLOCK + 关单/打回（TDD）

**Files:**
- `core/scripts/qa_review.py`（新建）
- `core/scripts/test_qa_review.py`（新建）

复用 `gen_test_tasks.append_qa_history` 与常量 `REPORT_SENTINEL`（import 自 Task 1 已建的模块）。仿 `ai_review.parse_verdict` 解析 VERDICT；仿 `verify_triage` 的"复检后关单"。关单 / 打回留言走 gh CLI。

- [ ] 写失败测试 `core/scripts/test_qa_review.py`，完整内容：

```python
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import qa_review as q


def test_parse_verdict_block():
    assert q.parse_verdict("一些发现\nVERDICT: BLOCK\n") == "BLOCK"


def test_parse_verdict_pass():
    assert q.parse_verdict("看起来覆盖完整\nVERDICT: PASS") == "PASS"


def test_parse_verdict_defaults_block_when_missing():
    # 报告审核场景下，模型没明确判定时保守视为 BLOCK（与 ai_review 的保守 PASS 相反，
    # 因为这里"放过未审核的报告"风险更高）
    assert q.parse_verdict("没有给出判定") == "BLOCK"


def test_is_qa_report_detects_sentinel():
    assert q.is_qa_report("QA-REPORT\n### 覆盖的验收点\n- [x] ok") is True
    assert q.is_qa_report("普通讨论评论，不是报告") is False


def test_extract_merge_sha_from_title():
    assert q.extract_merge_sha("[qa] feat: x [merge:abc1234]") == "abc1234"
    assert q.extract_merge_sha("没有标记的标题") == ""


def test_build_block_comment_mentions_reason():
    body = q.build_block_comment("缺少 TC3 的证据，验收点 2 未覆盖")
    assert "BLOCK" in body
    assert "TC3" in body
    assert "重测" in body


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
```

- [ ] 跑验证失败：`cd core/scripts && python3 -m pytest test_qa_review.py -q`
      预期：`ModuleNotFoundError: No module named 'qa_review'`。

- [ ] 写最小实现 `core/scripts/qa_review.py`，完整内容：

```python
#!/usr/bin/env python3
"""qa_review — QA 提交测试报告后，由 qa-reviewer 审核报告并 PASS 关单 / BLOCK 打回。

落地 spec 第 6 节闭环后半段：QA 在 qa-task issue 下评论提交测试报告 →
本脚本读报告 → ModelAdapter 核对（是否覆盖全部验收点？是否附证据？）→
输出 VERDICT（仿 ai_review）→ PASS 关单 + 记账；BLOCK 留言打回（仿 verify_triage 复检）。

由 qa-handoff.yml 的 issue_comment 触发（仅当 issue 带 qa-task 标签且评论是报告时）。

退出码：0 = PASS，1 = BLOCK，2 = 配置错误 / 非报告评论（跳过）。

读取的 env（workflow 里设）：
  GITHUB_TOKEN, GITHUB_REPOSITORY, ISSUE_NUMBER, ISSUE_TITLE,
  ISSUE_BODY（含验收标准）, COMMENT_BODY（QA 报告）

本地零凭证试跑：
  ISSUE_TITLE='[qa] x [merge:abc1234]' \
  COMMENT_BODY='QA-REPORT\n### 结论\n- 通过' \
  ISSUE_BODY='## 验收标准\n- 幂等' \
  python3 scripts/qa_review.py --mock
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

from _adapters import ModelAdapter
from gen_test_tasks import REPORT_SENTINEL, append_qa_history

_PROMPTS_DIR = os.getenv("AIFCL_PROMPTS_DIR", "prompts")
PROMPT_PATH = Path(f"{_PROMPTS_DIR}/review-qa-report.md")


def is_qa_report(comment_body: str) -> bool:
    """评论首个非空行是哨兵 → 视为测试报告。"""
    for line in comment_body.splitlines():
        s = line.strip()
        if s:
            return s.upper().startswith(REPORT_SENTINEL)
    return False


def extract_merge_sha(issue_title: str) -> str:
    m = re.search(r"\[merge:([0-9a-fA-F]+)\]", issue_title)
    return m.group(1) if m else ""


def parse_verdict(text: str) -> str:
    """仿 ai_review.parse_verdict，但缺判定时保守视为 BLOCK（避免放过未审核报告）。"""
    for line in reversed(text.splitlines()):
        s = line.strip().upper()
        if s.startswith("VERDICT:"):
            if "PASS" in s:
                return "PASS"
            if "BLOCK" in s:
                return "BLOCK"
    return "BLOCK"


def build_block_comment(review_body: str) -> str:
    return (
        "🛑 **QA Review · BLOCK**\n\n"
        "测试报告未通过审核，打回重测（验收点未全覆盖 / 缺证据）。请补充后再次"
        "在本 issue 评论提交报告：\n\n" + review_body
    )


def build_pass_comment(review_body: str) -> str:
    return (
        "✅ **QA Review · PASS**\n\n"
        "测试报告覆盖全部验收点且附证据，自动关闭本 qa-task。\n\n" + review_body
    )


def gh_issue_comment(repo: str, issue: str, token: str, body: str) -> None:
    env = os.environ.copy()
    env["GH_TOKEN"] = token
    subprocess.run(
        ["gh", "issue", "comment", issue, "--repo", repo, "--body", body],
        env=env, check=False,
    )


def gh_issue_close(repo: str, issue: str, token: str, comment: str) -> None:
    env = os.environ.copy()
    env["GH_TOKEN"] = token
    subprocess.run(
        ["gh", "issue", "close", issue, "--repo", repo,
         "--reason", "completed", "--comment", comment],
        env=env, check=False,
    )


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--mock", action="store_true")
    args = p.parse_args(argv[1:])

    repo = os.getenv("GITHUB_REPOSITORY", "")
    issue = os.getenv("ISSUE_NUMBER", "")
    title = os.getenv("ISSUE_TITLE", "")
    issue_body = os.getenv("ISSUE_BODY", "")
    comment = os.getenv("COMMENT_BODY", "")
    token = os.getenv("GITHUB_TOKEN", "")

    if not is_qa_report(comment):
        print(f"评论非测试报告（首行不是 {REPORT_SENTINEL}），跳过。")
        return 2

    if not PROMPT_PATH.exists():
        print(f"::error::找不到 prompt 文件 {PROMPT_PATH}", file=sys.stderr)
        return 2

    base_prompt = PROMPT_PATH.read_text(encoding="utf-8")
    merge_sha = extract_merge_sha(title)
    full_prompt = (
        base_prompt
        + "\n\n---\n\n## qa-task issue 正文（含验收标准）\n" + issue_body
        + "\n\n---\n\n## QA 提交的测试报告\n" + comment
        + "\n\n请核对：是否逐条覆盖验收点？是否附了可信证据？"
          "末尾给出 `VERDICT: PASS`（全覆盖+有证据）或 `VERDICT: BLOCK`。"
    )

    if args.mock:
        print(f"=== MOCK qa_review issue={issue} merge={merge_sha} prompt_chars={len(full_prompt)} ===")
        review_body = "[MOCK] 假装审核通过。"
        verdict = "PASS"
    else:
        review_body = ModelAdapter.summarize(
            full_prompt, loop="qa-handoff", role="qa-reviewer",
        )
        verdict = parse_verdict(review_body)

    print(f"--- qa-review verdict: {verdict} ---")
    print(review_body[:2000])

    if not args.mock and repo and issue and token:
        if verdict == "PASS":
            gh_issue_close(repo, issue, token, build_pass_comment(review_body))
            append_qa_history(merge_sha=merge_sha, action="passed",
                              issue=issue, extra={"repo": repo})
        else:
            gh_issue_comment(repo, issue, token, build_block_comment(review_body))
            append_qa_history(merge_sha=merge_sha, action="blocked",
                              issue=issue, extra={"repo": repo})

    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
```

- [ ] 跑验证通过：`cd core/scripts && python3 -m pytest test_qa_review.py -q`
      预期：`6 passed`。

- [ ] 烟测 mock：`cd core/scripts && COMMENT_BODY=$'QA-REPORT\n### 结论\n- 通过' ISSUE_TITLE='[qa] x [merge:abc1234]' ISSUE_BODY='## 验收标准\n- 幂等' python3 qa_review.py --mock`
      预期：打印 `=== MOCK qa_review ...` 与 `--- qa-review verdict: PASS ---`，退出码 0。

- [ ] 回归：`cd core/scripts && python3 -m pytest -q`（确认两脚本测试同时全绿）
      预期：`11 passed`。

- [ ] commit：

```bash
git add core/scripts/qa_review.py core/scripts/test_qa_review.py
git commit -m "feat(qa): qa_review 审核测试报告 PASS 关单 / BLOCK 打回

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: 两个 prompt 文件（内容即产物）

**Files:**
- `core/prompts/gen-test-tasks.md`（新建）
- `core/prompts/review-qa-report.md`（新建）

- [ ] 创建 `core/prompts/gen-test-tasks.md`，完整内容：

```markdown
# 测试任务生成 — qa-generator

你是 QA 测试设计师。下面给你一次「已合并到 main 的 PR」的 **MERGE DIFF**。
你要为它产出一份可被测试同事直接执行的测试任务，输出**中文 Markdown**。

## 你的任务
只针对本次 diff 改动的行为面设计测试（不要为未改动的旧功能编用例）。结合
改动的接口/数据/边界，覆盖正常路径、边界、异常与回归风险。

## 输出结构（严格按以下三段，用二级标题）
### 测试用例
逐条编号 `TC1/TC2/...`，每条含：前置条件、输入、操作步骤、**预期结果**。
覆盖：正常路径、边界值、错误输入/异常分支、并发或幂等（若 diff 涉及）、
对既有调用方的兼容性（若改了契约/接口）。

### 测试流程
QA 实际执行的顺序与环境要求（dev/staging、数据准备、依赖服务、回滚注意）。

### 验收标准
逐条可勾选 `- [ ]`，每条是一个**客观可判定**的通过条件（不是"看起来正常"，
而是"接口返回 200 且 X 字段等于 Y""重复提交两次只入账一次"这种可验证陈述）。
qa-reviewer 后续会逐条核对 QA 报告是否覆盖这些验收点，请让它们清晰、原子、可证。

## 重要
- 不要复述 diff，不要泛泛而谈；只产出能直接执行的用例与可判定的验收标准。
- 涉及金额/价格/交易时，验收标准要显式覆盖精度与舍入（呼应 financial-numerics）。
- 若 diff 改了数据库/迁移，加入数据兼容与回滚验证用例。
```

- [ ] 创建 `core/prompts/review-qa-report.md`，完整内容：

```markdown
# 测试报告审核 — qa-reviewer

你是 QA 审核员（maker/checker 分离中的 checker）。下面给你一个 qa-task issue
的正文（含**验收标准**）和 QA 提交的**测试报告**。你判断这份报告是否达标。

## 审核维度
1. **覆盖完整性**：报告是否逐条对应 issue 里「验收标准」的每一个 `- [ ]`？
   有没有遗漏的验收点？被勾选的点是否真的给了结果说明？
2. **证据充分性**：每个声称通过的点是否附了可信证据（截图链接 / 日志片段 /
   接口响应 / 用例执行记录）？只有"已测试通过"而无证据的，视为未覆盖。
3. **结论一致性**：报告结论与逐点结果是否自洽？有不通过项却给"通过"结论 → BLOCK。

## 输出格式
- 先按上面三维列出发现，指明**缺哪条验收点 / 缺哪条证据**（精确到 TC 编号或验收点）。
- 然后末尾**单独一行**给出判定：`VERDICT: PASS` 或 `VERDICT: BLOCK`。

## 判定规则
- 全部验收点都被覆盖且每条有证据、结论自洽 → `VERDICT: PASS`。
- 任一验收点未覆盖 / 缺证据 / 结论矛盾 → `VERDICT: BLOCK`，并说清要补什么。
- **没把握时保守判 BLOCK**（放过未审核的报告比多打回一次代价更高）。

## 重要
你是闭环门禁，不是建议箱。PASS 会直接关单，BLOCK 会打回重测，所以判定必须有依据。
```

- [ ] grep 验证两文件结构：
      `grep -l "qa-generator" core/prompts/gen-test-tasks.md && grep -c "VERDICT:" core/prompts/review-qa-report.md`
      预期：第一段打印路径；`grep -c` 输出 `>= 2`（PASS/BLOCK 两处）。

- [ ] commit：

```bash
git add core/prompts/gen-test-tasks.md core/prompts/review-qa-report.md
git commit -m "feat(qa): 新增 gen-test-tasks 与 review-qa-report 两个 prompt

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: 两个 agent toml（内容即产物）

**Files:**
- `claude-code/agents/qa-generator.toml`（新建）
- `claude-code/agents/qa-reviewer.toml`（新建）

仿 `verifier-quality.toml`（绑 prompt_file + budget）与 `implementer.toml`（tools 列表）。

- [ ] 创建 `claude-code/agents/qa-generator.toml`，完整内容：

```toml
name = "qa-generator"
description = "合并到 main 后读本次合并 diff，生成「测试用例 + 测试流程 + 验收标准」，建 qa-task issue 进测试看板。只设计测试、不执行、不评审报告。"
# 推荐档:Anthropic Sonnet / OpenAI gpt-4o / DeepSeek deepseek-chat / Qwen qwen-plus
provider = "anthropic"
model = "claude-sonnet-4-6"
reasoning = "medium"
tools = ["Read", "Grep", "Glob"]
prompt_file = "prompts/gen-test-tasks.md"

[budget]
max_input_tokens = 60000
max_output_tokens = 6000
```

- [ ] 创建 `claude-code/agents/qa-reviewer.toml`，完整内容：

```toml
name = "qa-reviewer"
description = "测试闭环的 checker:审核 QA 提交的测试报告是否覆盖全部验收点、是否附证据。只给 PASS(关单)或 BLOCK(打回重测),不替 QA 补测。"
# 推荐档:Anthropic Sonnet / OpenAI gpt-4o / DeepSeek deepseek-chat / Qwen qwen-plus
provider = "anthropic"
model = "claude-sonnet-4-6"
reasoning = "medium"
tools = ["Read", "Grep", "Glob"]
prompt_file = "prompts/review-qa-report.md"

[budget]
max_input_tokens = 40000
max_output_tokens = 4000
```

- [ ] grep 验证：
      `grep "prompt_file" claude-code/agents/qa-generator.toml claude-code/agents/qa-reviewer.toml`
      预期：两行分别指向 `prompts/gen-test-tasks.md` 与 `prompts/review-qa-report.md`。

- [ ] commit：

```bash
git add claude-code/agents/qa-generator.toml claude-code/agents/qa-reviewer.toml
git commit -m "feat(qa): 新增 qa-generator / qa-reviewer 两个 agent 定义

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: `qa-handoff.yml` workflow（内容即产物）

**Files:**
- `core/workflows/qa-handoff.yml`（新建）

仿 `triage.yml`（setup-python + pip install requirements + env 注入 + run 脚本）。两个 job：
`gen-test-tasks` 由 push-to-main 触发；`qa-review` 由 issue_comment（issue 含 qa-task 标签）触发。

- [ ] 创建 `core/workflows/qa-handoff.yml`，完整内容：

```yaml
# =============================================================================
# 测试交接 — 测试闭环 workflow（spec 第 6 节后半段）
# -----------------------------------------------------------------------------
# 1) push/merge 到 main → gen_test_tasks：读本次合并 diff 生成 qa-task issue。
# 2) issue_comment（issue 带 qa-task 标签）→ qa_review：审核 QA 报告，
#    PASS 关单、BLOCK 打回重测。
#
# 与 triage.yml 同源：setup-python + pip install scripts/requirements.txt +
# 由 env 注入凭证 + run 脚本。建单 / 关单 / 留言走 gh CLI（GITHUB_TOKEN 自带）。
# =============================================================================
name: QA Handoff

on:
  push:
    branches: [main]
  issue_comment:
    types: [created]

permissions:
  contents: read
  issues: write          # 建 qa-task / 关单 / 打回留言

jobs:
  # 合并后生成测试任务 -------------------------------------------------------
  gen-test-tasks:
    if: github.event_name == 'push'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 2          # 取 merge commit 的父提交以算 first-parent diff
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'pip'
      - run: pip install -r scripts/requirements.txt
      - name: Generate qa-task issue from merge diff
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          GITHUB_REPOSITORY: ${{ github.repository }}
          MERGE_SHA: ${{ github.sha }}
          LLM_PROVIDER: ${{ vars.LLM_PROVIDER }}
          LLM_API_KEY: ${{ secrets.LLM_API_KEY }}
          LLM_BASE_URL: ${{ vars.LLM_BASE_URL }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: python3 scripts/gen_test_tasks.py --merge-sha "$MERGE_SHA"

  # QA 提交报告后审核 --------------------------------------------------------
  qa-review:
    # 仅当评论发生在 issue（非 PR）且该 issue 带 qa-task 标签时
    if: >
      github.event_name == 'issue_comment' &&
      !github.event.issue.pull_request &&
      contains(toJSON(github.event.issue.labels.*.name), 'qa-task')
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'pip'
      - run: pip install -r scripts/requirements.txt
      - name: Review QA report
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          GITHUB_REPOSITORY: ${{ github.repository }}
          ISSUE_NUMBER: ${{ github.event.issue.number }}
          ISSUE_TITLE: ${{ github.event.issue.title }}
          ISSUE_BODY: ${{ github.event.issue.body }}
          COMMENT_BODY: ${{ github.event.comment.body }}
          LLM_PROVIDER: ${{ vars.LLM_PROVIDER }}
          LLM_API_KEY: ${{ secrets.LLM_API_KEY }}
          LLM_BASE_URL: ${{ vars.LLM_BASE_URL }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        # 退出码 2 = 非报告评论（跳过），不应让 job 红，故吞掉 2
        run: |
          set +e
          python3 scripts/qa_review.py
          code=$?
          if [ "$code" = "2" ]; then echo "非测试报告评论，跳过。"; exit 0; fi
          exit $code
```

- [ ] grep 验证触发点与脚本调用：
      `grep -E "issue_comment|gen_test_tasks.py|qa_review.py|qa-task" core/workflows/qa-handoff.yml`
      预期：能看到 `issue_comment`、两条脚本 run、`qa-task` 标签过滤。

- [ ] （可选）若装了 actionlint：`actionlint core/workflows/qa-handoff.yml` 预期无错误。

- [ ] commit：

```bash
git add core/workflows/qa-handoff.yml
git commit -m "feat(qa): qa-handoff workflow 串起生成测试任务与报告审核

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: 测试报告结构化模板（内容即产物）

**Files:**
- `templates/team-ops/issue-templates/qa-report.yml`（新建）

GitHub Issue Form（YAML）形态，放在 spec 第 4.3 的 `team-ops/issue-templates/`（这里随 AIFCL 仓 `templates/` 下发，团队装进 team-ops 仓的 `.github/ISSUE_TEMPLATE/`）。字段结构与 `gen_test_tasks.build_qa_task_body` 内嵌的报告段一致，保证 qa-reviewer 能稳定核对。

- [ ] 创建 `templates/team-ops/issue-templates/qa-report.yml`，完整内容：

```yaml
# 测试报告 Issue Form —— QA 据此结构化提交测试结果。
# 部署位置：team-ops 仓的 .github/ISSUE_TEMPLATE/qa-report.yml
# 说明：日常 QA 报告优先直接在对应代码仓的 qa-task issue 下"评论"提交
#       （首行 QA-REPORT，与 gen_test_tasks 内嵌模板一致，触发 qa_review 自动审核）；
#       本 Issue Form 用于需要独立留痕 / 跨仓汇总时新开报告 issue。
name: QA 测试报告
description: 提交一个 qa-task 的测试执行结果，供 qa-reviewer 审核
title: "QA-REPORT: <对应 qa-task 标题>"
labels: ["qa-report"]
body:
  - type: input
    id: qa_task_ref
    attributes:
      label: 关联 qa-task
      description: 对应的 qa-task issue 编号或链接（含其标题里的 [merge:..] 标记）
      placeholder: "#123 / org/svc#123"
    validations:
      required: true
  - type: textarea
    id: coverage
    attributes:
      label: 覆盖的验收点
      description: 逐条对应 qa-task「验收标准」里的每个勾选项，写明结果
      placeholder: |
        - [x] 验收点1：重复提交两次只入账一次 —— 实测两次返回同一交易号
        - [x] 验收点2：金额精度按最小单位 —— 实测无浮点误差
    validations:
      required: true
  - type: input
    id: environment
    attributes:
      label: 测试环境
      description: dev/staging、版本/镜像 tag、数据准备情况
      placeholder: "staging, image rel-2026.06.27-abc1234"
    validations:
      required: true
  - type: textarea
    id: evidence
    attributes:
      label: 证据
      description: 截图链接 / 日志片段 / 接口响应 / 用例执行记录（每个通过点都要有）
    validations:
      required: true
  - type: dropdown
    id: conclusion
    attributes:
      label: 结论
      options:
        - 通过
        - 不通过
    validations:
      required: true
  - type: textarea
    id: notes
    attributes:
      label: 备注 / 不通过原因
      description: 若不通过，说明缺陷与复现步骤
    validations:
      required: false
```

- [ ] grep 验证关键字段齐全：
      `grep -E "qa_task_ref|coverage|evidence|conclusion" templates/team-ops/issue-templates/qa-report.yml`
      预期：四个字段 id 全部命中。

- [ ] commit：

```bash
git add templates/team-ops/issue-templates/qa-report.yml
git commit -m "feat(qa): 新增 QA 测试报告结构化 Issue Form 模板

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Self-Review

对照 spec 第 6 节流程后半段（测试闭环）逐条确认：

- [ ] **"qa-generator：读本次 diff → 生成测试用例 + 测试流程 + 验收标准"** → Task 1 `gen_test_tasks.collect_merge_diff` 读 first-parent 合并 diff，`gen-test-tasks.md`（Task 3）强制输出三段结构。
- [ ] **"→ 自动建 qa-task issue 进测试看板"** → Task 1 `create_qa_issue` 用 `gh issue create --label qa-task` 在当前代码仓建单（PR/issue 同仓可自动关单，呼应 spec 3.2）。
- [ ] **"测试同事领取 → 按规范执行 → 按 Issue 模板提交测试报告"** → Task 6 `qa-report.yml` Issue Form + Task 1 issue 正文内嵌的 `QA-REPORT` 评论模板段（两条路径字段一致）。
- [ ] **"qa-reviewer 审核报告（覆盖全部验收点？有证据？）"** → Task 2 `qa_review.py` + `review-qa-report.md`（Task 3）三维审核（覆盖/证据/一致性）。
- [ ] **"PASS → 关单 + 记账"** → Task 2 `gh_issue_close` + `append_qa_history(action="passed")`。
- [ ] **"BLOCK → 打回 / 重开 dev 任务（回测）"** → Task 2 `build_block_comment` 留言打回 + `append_qa_history(action="blocked")`（仿 verify_triage 复检/回测语义）。
- [ ] **PASS/BLOCK verdict 仿 ai_review** → Task 2 `parse_verdict`（缺判定保守 BLOCK），prompt 末尾要求 `VERDICT:` 行。
- [ ] **建单/关单/复检仿 triage_engine + verify_triage** → Task 1 建单含 `[merge:..]` 去重标记（仿 `[fp:..]`）；Task 2 关单/留言闭环。
- [ ] **append-only 记账（仿 triage-history.jsonl）** → `state/qa-history.jsonl`，`append_qa_history` 复用 `_adapters.STATE` 路径，action ∈ {created, passed, blocked}。
- [ ] **install.sh 靠通配自动分发** → 新文件落在 `core/scripts/*`（含 test_*.py）、`core/prompts/*.md`、`core/workflows/*.yml`、`claude-code/agents/*.toml`；`templates/` 随仓 clone。**无需改 install.sh**（已核对 install.sh 第 79-112 行通配规则）。
- [ ] **角色映射 qa-generator / qa-reviewer**（spec 第 5 节）→ Task 4 两个 agent toml，且脚本 `ModelAdapter.summarize(..., role="qa-generator"/"qa-reviewer")` 与之对齐（驱动 `LLM_MODEL_QA_GENERATOR` 等覆盖键 + token 记账的 role 维度）。

**文件清单（8 新增 + 2 测试 = 10 个文件，6 个 commit）：**
1. `core/scripts/gen_test_tasks.py` + `core/scripts/test_gen_test_tasks.py`
2. `core/scripts/qa_review.py` + `core/scripts/test_qa_review.py`
3. `core/prompts/gen-test-tasks.md`、`core/prompts/review-qa-report.md`
4. `claude-code/agents/qa-generator.toml`、`claude-code/agents/qa-reviewer.toml`
5. `core/workflows/qa-handoff.yml`
6. `templates/team-ops/issue-templates/qa-report.yml`

运行时产物：`state/qa-history.jsonl`（脚本自动创建，无需预置）。
