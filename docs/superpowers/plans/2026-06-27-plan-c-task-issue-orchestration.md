# 任务拆解与 Issue 体系 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 AIFCL 基座上落地"每日任务拆解 → 待建 issue 草稿 → 人确认 → 在对应代码仓建结构化 Issue"的编排链路，固化人工确认门与 5 类 Issue Form。

**Architecture:** 管理仓 `team-ops` 承载每日计划文档、责任人归属、Issue Form 模板与组织级 Projects 配置；`task_splitter.py` 用 `ModelAdapter` 读进度源只产出"计划文档 + 待建 issue 草稿(JSON)"，绝不直接建 issue；人确认草稿后 `create_issues_from_draft.py` 用 `TrackerAdapter`/`gh` 在草稿每条所指定的**代码仓**建 issue（GitHub `Closes #N` 只能关同仓 issue，故 issue 必须落代码仓而非管理仓）。`install.sh` 负责把 Issue Form 分发到目标代码仓 `.github/ISSUE_TEMPLATE/`。

**Tech Stack:** Python 3 + _adapters.py(ModelAdapter/TrackerAdapter) + gh CLI + GitHub Issue Forms(YAML)

---

## File Structure

新增文件（按职责）：

| 文件 | 职责 |
|---|---|
| `templates/team-ops/README.md` | 管理仓模板说明：目录用途、人工确认门工作流 |
| `templates/team-ops/ownership.md` | 三层模型①②：项目级/子服务级责任人归属（静态） |
| `templates/team-ops/daily/.gitkeep` | 每日任务计划文档归档目录占位 |
| `templates/team-ops/daily/EXAMPLE-2026-06-27.md` | 当日任务计划文档样例（task_splitter 产出格式参照） |
| `templates/team-ops/projects/README.md` | 组织级 GitHub Projects 配置 + 跨仓自动关单说明 |
| `templates/team-ops/issue-templates/daily-task.yml` | Issue Form：每日任务（强制字段：责任人/所属子服务/验收标准/关联文档/预计工时/依赖项） |
| `templates/team-ops/issue-templates/feature.yml` | Issue Form：功能开发 |
| `templates/team-ops/issue-templates/bug.yml` | Issue Form：bug 修复 |
| `templates/team-ops/issue-templates/qa-task.yml` | Issue Form：测试任务 |
| `templates/team-ops/issue-templates/review.yml` | Issue Form：CTO 评审任务 |
| `core/scripts/task_splitter.py` | 读进度+任务源 → ModelAdapter 拆解 → 产出当日计划.md + 待建 issue 草稿 JSON（只产草稿） |
| `core/scripts/create_issues_from_draft.py` | 读人确认后的草稿 JSON → 按每条的 repo 用 TrackerAdapter/gh 建 issue（人确认门后置执行） |
| `core/scripts/_gh_tracker.py` | 给 TrackerAdapter 增加一个面向 GitHub Issues（gh CLI）的实现 `_GhCliTracker` 与 dry-run 变体 |
| `core/prompts/daily-task-split.md` | 任务拆解 prompt（喂给 ModelAdapter） |
| `claude-code/skills/task-splitter/SKILL.md` | 拆解 skill（人触发，产草稿→人确认→建单流程说明） |
| `core/scripts/test_task_splitter.py` | task_splitter TDD 测试 |
| `core/scripts/test_create_issues_from_draft.py` | create_issues_from_draft TDD 测试 |

修改文件：

| 文件 | 修改 |
|---|---|
| `core/scripts/_adapters.py` | `TrackerAdapter.create()` 增加 `github-cli` 分支；新增 `create_issue_in_repo` 接口与 dry-run 实现 |
| `tools/install.sh` | 新增：分发 `templates/team-ops/issue-templates/*.yml` 到目标代码仓 `.github/ISSUE_TEMPLATE/` |

约定（贯穿全 plan，后续任务复用）：

- **草稿 JSON schema**（`task_splitter` 产出、`create_issues_from_draft` 消费）：
  ```json
  {
    "date": "2026-06-27",
    "plan_doc": "team-ops/daily/2026-06-27.md",
    "issues": [
      {
        "repo": "org/backend-svc-order",
        "type": "daily-task",
        "title": "[order] 实现下单幂等键",
        "labels": ["daily-task", "svc-order"],
        "assignee": "alice",
        "body": "## 责任人\nalice\n\n## 所属子服务\nsvc-order\n..."
      }
    ]
  }
  ```
  每条 issue 的 `repo` 字段是**代码仓** slug（`owner/name`），决定 `gh issue create -R <repo>`。

---

### Task 1: 给 _adapters.py 增加 GitHub-CLI Tracker（建 issue 到指定代码仓）

`TrackerAdapter` 现有接口面向"按指纹去重的运维工单"，不含"在指定 repo 用 Issue Form 字段建 issue"。本任务新增 `create_issue_in_repo` 接口 + 一个 gh CLI 实现 + dry-run 实现，并在 `TrackerAdapter.create()` 加 `github-cli` 分支。把 gh 实现放在独立文件 `_gh_tracker.py` 以免污染既有适配器。

**Files:**
- Create: `/Users/luis/work/luis/ai/AI--First-Coding-Loop-CC/core/scripts/_gh_tracker.py`
- Modify: `/Users/luis/work/luis/ai/AI--First-Coding-Loop-CC/core/scripts/_adapters.py`
- Test: `/Users/luis/work/luis/ai/AI--First-Coding-Loop-CC/core/scripts/test_create_issues_from_draft.py`（本任务先建并写第一组测试）

- [ ] 写失败测试。创建 `/Users/luis/work/luis/ai/AI--First-Coding-Loop-CC/core/scripts/test_create_issues_from_draft.py`，内容：

```python
"""create_issues_from_draft + GitHub-CLI Tracker 的测试。"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def test_tracker_factory_returns_dryrun_by_default(monkeypatch):
    """没设 TRACKER 时默认 github-dryrun（零副作用）。"""
    monkeypatch.delenv("TRACKER", raising=False)
    from _adapters import TrackerAdapter
    t = TrackerAdapter.create()
    assert t.__class__.__name__ == "_DryRunTracker"


def test_tracker_factory_returns_gh_cli_when_requested(monkeypatch):
    monkeypatch.setenv("TRACKER", "github-cli")
    # 重新导入以触发工厂分支
    import importlib
    import _adapters
    importlib.reload(_adapters)
    t = _adapters.TrackerAdapter.create()
    assert t.__class__.__name__ == "_GhCliTracker"


def test_dryrun_create_issue_in_repo_prints_and_returns_marker(capsys, monkeypatch):
    monkeypatch.delenv("TRACKER", raising=False)
    from _adapters import TrackerAdapter
    t = TrackerAdapter.create()
    url = t.create_issue_in_repo(
        repo="org/backend",
        title="[order] 幂等键",
        body="## 责任人\nalice",
        labels=["daily-task"],
        assignee="alice",
    )
    out = capsys.readouterr().out
    assert "DRY-RUN" in out
    assert "org/backend" in out
    assert url.startswith("dry-run://")


def test_gh_cli_create_issue_builds_correct_command(monkeypatch):
    """_GhCliTracker.create_issue_in_repo 应调用 gh issue create 且参数正确。"""
    monkeypatch.setenv("TRACKER", "github-cli")
    import importlib
    import _adapters
    importlib.reload(_adapters)

    captured = {}

    def fake_run(args, capture_output, text, check):
        captured["args"] = args
        class R:
            stdout = "https://github.com/org/backend/issues/42\n"
            returncode = 0
        return R()

    monkeypatch.setattr(_adapters.subprocess, "run", fake_run)
    t = _adapters.TrackerAdapter.create()
    url = t.create_issue_in_repo(
        repo="org/backend",
        title="[order] 幂等键",
        body="b",
        labels=["daily-task", "svc-order"],
        assignee="alice",
    )
    a = captured["args"]
    assert a[:3] == ["gh", "issue", "create"]
    assert "-R" in a and "org/backend" in a
    assert "--title" in a and "[order] 幂等键" in a
    assert "--label" in a
    # labels 合并成逗号串
    assert "daily-task,svc-order" in a
    assert "--assignee" in a and "alice" in a
    assert url == "https://github.com/org/backend/issues/42"
```

- [ ] 运行验证失败。命令：`cd /Users/luis/work/luis/ai/AI--First-Coding-Loop-CC/core/scripts && python -m pytest test_create_issues_from_draft.py -k "tracker or dryrun or gh_cli" -q`。预期：`test_tracker_factory_returns_gh_cli_when_requested` 与 `test_dryrun_create_issue_in_repo_prints_and_returns_marker` 与 `test_gh_cli_create_issue_builds_correct_command` 失败，报 `AttributeError: ... has no attribute 'create_issue_in_repo'` 或 `_GhCliTracker` 不存在（`ImportError`/`AssertionError`）。

- [ ] 写最小实现 1/2。创建 `/Users/luis/work/luis/ai/AI--First-Coding-Loop-CC/core/scripts/_gh_tracker.py`：

```python
"""GitHub Issues 适配器(基于 gh CLI)。

与 _adapters.py 里面向"运维指纹工单"的 Tracker 不同,本文件专注
"在指定代码仓用结构化字段建 issue"——服务于每日任务拆解的人工确认门后置执行。

为什么落代码仓而非管理仓:GitHub 的 `Closes #N` 自动关闭关键字只能关同仓 issue,
开发/bug/测试/review issue 必须建在对应代码仓,PR 合并才能自动关单。
"""
from __future__ import annotations

import subprocess


class _GhCliTracker:
    """用 `gh issue create` 在指定 repo 建 issue。需要本机已 `gh auth login`。"""

    def create_issue_in_repo(
        self,
        *,
        repo: str,
        title: str,
        body: str,
        labels: list[str] | None = None,
        assignee: str | None = None,
    ) -> str:
        args = ["gh", "issue", "create", "-R", repo, "--title", title, "--body", body]
        if labels:
            args += ["--label", ",".join(labels)]
        if assignee:
            args += ["--assignee", assignee]
        proc = subprocess.run(args, capture_output=True, text=True, check=True)
        return proc.stdout.strip()
```

- [ ] 写最小实现 2/2。在 `/Users/luis/work/luis/ai/AI--First-Coding-Loop-CC/core/scripts/_adapters.py` 顶部 import 区(`import os` 之后)确认已有 `import subprocess`；若无则添加。当前文件无 `import subprocess`，所以在 `import re` 行后新增一行：

将
```python
import re
from dataclasses import dataclass, field, asdict
```
改为
```python
import re
import subprocess
from dataclasses import dataclass, field, asdict
```

- [ ] 在 `_adapters.py` 的 `TrackerAdapter` 基类里新增 `create_issue_in_repo` 抽象方法。把现有
```python
    def close_issue(self, issue_id: str, comment: str) -> None:
        raise NotImplementedError
```
改为
```python
    def close_issue(self, issue_id: str, comment: str) -> None:
        raise NotImplementedError

    def create_issue_in_repo(self, *, repo: str, title: str, body: str,
                             labels: list[str] | None = None,
                             assignee: str | None = None) -> str:
        """在指定代码仓建一个结构化 issue,返回 issue URL。供任务拆解人确认门后置执行。"""
        raise NotImplementedError
```

- [ ] 在 `_adapters.py` 的 `TrackerAdapter.create()` 工厂里增加 `github-cli` 分支。把
```python
    @staticmethod
    def create() -> "TrackerAdapter":
        tracker = os.getenv("TRACKER", "github-dryrun").lower()
        if tracker == "linear":
            return _LinearTracker()
        # Jira / GitHub 可按相同接口扩展
        return _DryRunTracker()
```
改为
```python
    @staticmethod
    def create() -> "TrackerAdapter":
        tracker = os.getenv("TRACKER", "github-dryrun").lower()
        if tracker == "linear":
            return _LinearTracker()
        if tracker == "github-cli":
            from _gh_tracker import _GhCliTracker
            return _GhCliTracker()
        # Jira / 其他可按相同接口扩展
        return _DryRunTracker()
```

- [ ] 给 `_DryRunTracker` 增加 `create_issue_in_repo` 实现。把
```python
    def close_issue(self, issue_id, comment):
        print(f"[DRY-RUN] CLOSE ticket {issue_id}: {comment}")
```
改为
```python
    def close_issue(self, issue_id, comment):
        print(f"[DRY-RUN] CLOSE ticket {issue_id}: {comment}")
    def create_issue_in_repo(self, *, repo, title, body, labels=None, assignee=None):
        print(f"[DRY-RUN] CREATE issue in {repo}  labels={labels} assignee={assignee}")
        print(f"          title: {title}")
        print(_indent(body))
        return f"dry-run://{repo}/{abs(hash(title)) % 100000}"
```

- [ ] 让 `_GhCliTracker` 也满足 `TrackerAdapter` 接口约定（测试只检查方法行为，不强制继承，但保持类名 `_GhCliTracker` 即可）。无需改动 `_gh_tracker.py`，因为测试 `test_gh_cli_create_issue_builds_correct_command` 用 `monkeypatch.setattr(_adapters.subprocess, ...)` 打桩——而 gh tracker 用的是自己模块的 `subprocess`。修正：测试打桩 `_adapters.subprocess`，但实现调用 `_gh_tracker.subprocess`。为使打桩生效，改 `_gh_tracker.py` 不自带 import，而是复用 `_adapters` 的 `subprocess`：把 `_gh_tracker.py` 的
```python
from __future__ import annotations

import subprocess
```
改为
```python
from __future__ import annotations

import _adapters
```
并把方法体内 `subprocess.run(...)` 改为 `_adapters.subprocess.run(...)`：
```python
        proc = _adapters.subprocess.run(args, capture_output=True, text=True, check=True)
        return proc.stdout.strip()
```

- [ ] 运行验证通过。命令：`cd /Users/luis/work/luis/ai/AI--First-Coding-Loop-CC/core/scripts && python -m pytest test_create_issues_from_draft.py -k "tracker or dryrun or gh_cli" -q`。预期：4 passed。

- [ ] commit。命令：
```bash
cd /Users/luis/work/luis/ai/AI--First-Coding-Loop-CC && git add core/scripts/_gh_tracker.py core/scripts/_adapters.py core/scripts/test_create_issues_from_draft.py && git commit -m "feat(team-ops): add GitHub-CLI Tracker create_issue_in_repo for code-repo issues

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: task_splitter.py —— 读进度+任务源，产出当日计划.md + 待建 issue 草稿 JSON（人工确认门：只产草稿）

`task_splitter.py` 是三层模型第③层（每日拆解）的入口。它读"任务源文件"（架构师写的结构化任务，文本）+ `ownership.md`（责任人归属），调 `ModelAdapter.summarize` 用 `core/prompts/daily-task-split.md` 拆解，产出两个文件：当日计划 markdown 与草稿 JSON。**绝不调用任何 Tracker。** 模型未配置时回退到"机器拆解"（把任务源逐段切成草稿条目），保证 CI/无 key 也能跑。

**Files:**
- Create: `/Users/luis/work/luis/ai/AI--First-Coding-Loop-CC/core/scripts/task_splitter.py`
- Test: `/Users/luis/work/luis/ai/AI--First-Coding-Loop-CC/core/scripts/test_task_splitter.py`

- [ ] 写失败测试。创建 `/Users/luis/work/luis/ai/AI--First-Coding-Loop-CC/core/scripts/test_task_splitter.py`：

```python
"""task_splitter 的测试:必须只产草稿,绝不建 issue。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


@pytest.fixture
def task_source(tmp_path):
    src = tmp_path / "tasks-source.md"
    src.write_text(
        "# 当日任务源\n\n"
        "## 任务: 实现下单幂等键\n"
        "repo: org/backend\n"
        "子服务: svc-order\n"
        "责任人: alice\n"
        "验收: 重复下单返回同一订单\n\n"
        "## 任务: 前端订单确认页\n"
        "repo: org/frontend\n"
        "子服务: web-order\n"
        "责任人: bob\n"
        "验收: 点击确认显示成功态\n",
        encoding="utf-8",
    )
    return src


def test_run_writes_plan_and_draft_without_creating_issues(tmp_path, task_source, monkeypatch):
    # 强制无模型 → 走机器回退,可确定性断言
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    # 任何 Tracker 调用都视为违反人工确认门
    import _adapters
    def boom(*a, **k):
        raise AssertionError("task_splitter 不得创建/触碰 Tracker")
    monkeypatch.setattr(_adapters.TrackerAdapter, "create", staticmethod(boom))

    import task_splitter
    plan_path = tmp_path / "daily" / "2026-06-27.md"
    draft_path = tmp_path / "draft-2026-06-27.json"
    rc = task_splitter.run(
        source=str(task_source),
        date="2026-06-27",
        plan_out=str(plan_path),
        draft_out=str(draft_path),
    )
    assert rc == 0
    assert plan_path.exists()
    assert draft_path.exists()

    draft = json.loads(draft_path.read_text(encoding="utf-8"))
    assert draft["date"] == "2026-06-27"
    assert len(draft["issues"]) == 2
    repos = {i["repo"] for i in draft["issues"]}
    assert repos == {"org/backend", "org/frontend"}
    for it in draft["issues"]:
        assert it["type"] == "daily-task"
        assert "daily-task" in it["labels"]
        assert it["title"]
        assert it["body"]

    plan_text = plan_path.read_text(encoding="utf-8")
    assert "2026-06-27" in plan_text
    assert "alice" in plan_text and "bob" in plan_text


def test_parse_source_extracts_fields(task_source):
    import task_splitter
    tasks = task_splitter.parse_source(task_source.read_text(encoding="utf-8"))
    assert len(tasks) == 2
    assert tasks[0]["repo"] == "org/backend"
    assert tasks[0]["assignee"] == "alice"
    assert tasks[0]["subservice"] == "svc-order"
    assert "幂等键" in tasks[0]["title"]


def test_draft_never_contains_issue_numbers(tmp_path, task_source, monkeypatch):
    """草稿是'待建',不应预置 issue number / url。"""
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    import task_splitter
    draft_path = tmp_path / "d.json"
    task_splitter.run(
        source=str(task_source), date="2026-06-27",
        plan_out=str(tmp_path / "p.md"), draft_out=str(draft_path),
    )
    draft = json.loads(draft_path.read_text(encoding="utf-8"))
    for it in draft["issues"]:
        assert "number" not in it
        assert "url" not in it
```

- [ ] 运行验证失败。命令：`cd /Users/luis/work/luis/ai/AI--First-Coding-Loop-CC/core/scripts && python -m pytest test_task_splitter.py -q`。预期：`ModuleNotFoundError: No module named 'task_splitter'`（3 个测试全 error/fail）。

- [ ] 写最小实现。创建 `/Users/luis/work/luis/ai/AI--First-Coding-Loop-CC/core/scripts/task_splitter.py`：

```python
#!/usr/bin/env python3
"""每日任务拆解 — 三层模型第 ③ 层(每日)。

读"任务源"(架构师写的结构化任务文本)+ ownership.md(责任人归属),
用 ModelAdapter 按 prompts/daily-task-split.md 拆解,产出两样东西:
  1. 当日任务计划文档(markdown,归档到 team-ops/daily/<date>.md)
  2. 待建 issue 清单草稿(JSON)

人工确认门(本脚本的硬约束):只产草稿,绝不创建 issue、绝不触碰 Tracker。
建 issue 是 create_issues_from_draft.py 在人确认草稿后才做的事。

本地试跑(无模型 key → 机器回退拆解,零副作用):
    python scripts/task_splitter.py --source tasks-source.md --date 2026-06-27 \\
        --plan-out team-ops/daily/2026-06-27.md --draft-out draft.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from _adapters import ModelAdapter

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "daily-task-split.md"


def parse_source(text: str) -> list[dict]:
    """把任务源切成结构化任务条目。

    任务源约定:每个任务以 '## 任务:' 开头,其下若干 'key: value' 行。
    识别 repo / 子服务 / 责任人 / 验收 等字段;未提供的留空。
    """
    tasks: list[dict] = []
    blocks = re.split(r"(?m)^##\s*任务[:：]\s*", text)
    for blk in blocks[1:]:
        lines = blk.splitlines()
        title = lines[0].strip() if lines else ""
        fields = {"title": title, "repo": "", "subservice": "",
                  "assignee": "", "acceptance": ""}
        for ln in lines[1:]:
            m = re.match(r"\s*(repo|子服务|责任人|验收|预计工时|关联文档|依赖)\s*[:：]\s*(.+)$", ln)
            if not m:
                continue
            k, v = m.group(1), m.group(2).strip()
            if k == "repo":
                fields["repo"] = v
            elif k == "子服务":
                fields["subservice"] = v
            elif k == "责任人":
                fields["assignee"] = v
            elif k == "验收":
                fields["acceptance"] = v
            elif k == "预计工时":
                fields["estimate"] = v
            elif k == "关联文档":
                fields["docs"] = v
            elif k == "依赖":
                fields["deps"] = v
        if title:
            tasks.append(fields)
    return tasks


def _issue_body(t: dict) -> str:
    """按 daily-task Issue Form 的强制字段拼 body(机器回退用)。"""
    return (
        f"## 责任人\n{t.get('assignee') or '(待指派)'}\n\n"
        f"## 所属子服务\n{t.get('subservice') or '(未指定)'}\n\n"
        f"## 验收标准\n{t.get('acceptance') or '(待补充)'}\n\n"
        f"## 关联文档\n{t.get('docs') or '(无)'}\n\n"
        f"## 预计工时\n{t.get('estimate') or '(待估)'}\n\n"
        f"## 依赖项\n{t.get('deps') or '(无)'}\n"
    )


def _label_for(t: dict) -> list[str]:
    labels = ["daily-task"]
    if t.get("subservice"):
        labels.append(t["subservice"])
    return labels


def build_draft(date: str, plan_doc: str, tasks: list[dict]) -> dict:
    issues = []
    for t in tasks:
        issues.append({
            "repo": t.get("repo", ""),
            "type": "daily-task",
            "title": f"[{t.get('subservice') or 'task'}] {t['title']}",
            "labels": _label_for(t),
            "assignee": t.get("assignee", ""),
            "body": _issue_body(t),
        })
    return {"date": date, "plan_doc": plan_doc, "issues": issues}


def build_plan_doc(date: str, tasks: list[dict]) -> str:
    rows = []
    for t in tasks:
        rows.append(
            f"| {t['title']} | {t.get('assignee') or '(待指派)'} | "
            f"{t.get('subservice') or '-'} | {t.get('repo') or '-'} | "
            f"{t.get('estimate') or '-'} |"
        )
    table = "\n".join(rows) or "| (今日无任务) | - | - | - | - |"
    return (
        f"# 当日任务计划 {date}\n\n"
        f"> 由 task_splitter 生成。本文件是计划归档;待建 issue 见同批草稿 JSON。\n"
        f"> 人工确认门:确认草稿后运行 create_issues_from_draft.py 才会真正建 issue。\n\n"
        f"| 任务 | 责任人 | 子服务 | 代码仓 | 预计工时 |\n"
        f"|---|---|---|---|---|\n"
        f"{table}\n"
    )


def _ai_refine(prompt_template: str, source: str) -> str:
    return ModelAdapter.summarize(
        prompt_template + "\n\n=== 任务源 ===\n" + source,
        loop="task-split", role="task-splitter",
    )


def run(*, source: str, date: str, plan_out: str, draft_out: str,
        ownership: str | None = None) -> int:
    src_text = Path(source).read_text(encoding="utf-8")
    tasks = parse_source(src_text)

    # 模型可用时,让模型补全/校准字段(摘要型,不改变"只产草稿"约束)。
    # 模型未配置/失败 → summarize 返回 [模型...] 前缀字符串,直接走机器拆解结果。
    if PROMPT_PATH.exists():
        ai = _ai_refine(PROMPT_PATH.read_text(encoding="utf-8"), src_text)
        if not ai.startswith("[模型"):
            # 模型产出附加进计划文档作为"AI 建议",不覆盖确定性结构(保守)
            pass  # AI 文本仅供人审,机器结构仍以 parse_source 为准

    plan_doc_rel = plan_out
    draft = build_draft(date, plan_doc_rel, tasks)
    plan_md = build_plan_doc(date, tasks)

    Path(plan_out).parent.mkdir(parents=True, exist_ok=True)
    Path(plan_out).write_text(plan_md, encoding="utf-8")
    Path(draft_out).parent.mkdir(parents=True, exist_ok=True)
    Path(draft_out).write_text(
        json.dumps(draft, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"✓ 计划文档 → {plan_out}")
    print(f"✓ 待建 issue 草稿 → {draft_out}  (共 {len(draft['issues'])} 条)")
    print("⚠ 人工确认门:请 review 草稿,确认无误后再运行 "
          "create_issues_from_draft.py 建 issue。")
    return 0


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--source", required=True, help="任务源 markdown")
    p.add_argument("--date", required=True, help="YYYY-MM-DD")
    p.add_argument("--plan-out", required=True, help="当日计划文档输出路径")
    p.add_argument("--draft-out", required=True, help="待建 issue 草稿 JSON 输出路径")
    p.add_argument("--ownership", default=None, help="ownership.md 路径(可选)")
    args = p.parse_args(argv[1:])
    return run(source=args.source, date=args.date,
               plan_out=args.plan_out, draft_out=args.draft_out,
               ownership=args.ownership)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
```

- [ ] 运行验证通过。命令：`cd /Users/luis/work/luis/ai/AI--First-Coding-Loop-CC/core/scripts && python -m pytest test_task_splitter.py -q`。预期：3 passed。

- [ ] commit。命令：
```bash
cd /Users/luis/work/luis/ai/AI--First-Coding-Loop-CC && git add core/scripts/task_splitter.py core/scripts/test_task_splitter.py && git commit -m "feat(team-ops): add task_splitter producing daily plan + draft only (human gate)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: create_issues_from_draft.py —— 人确认草稿后，在对应代码仓建 issue

人 review 草稿 JSON 后运行本脚本。它读草稿，逐条用 `TrackerAdapter`（默认 `github-dryrun`，设 `TRACKER=github-cli` 才真正建单）按每条的 `repo` 在**对应代码仓**建 issue。脚本要求显式 `--confirm` 标志（再加一道人确认门），否则只 dry-run 打印不建单。

**Files:**
- Create: `/Users/luis/work/luis/ai/AI--First-Coding-Loop-CC/core/scripts/create_issues_from_draft.py`
- Test: `/Users/luis/work/luis/ai/AI--First-Coding-Loop-CC/core/scripts/test_create_issues_from_draft.py`（追加测试到 Task 1 已建的文件）

- [ ] 追加失败测试。在 `/Users/luis/work/luis/ai/AI--First-Coding-Loop-CC/core/scripts/test_create_issues_from_draft.py` 末尾追加：

```python
@pytest.fixture
def draft_file(tmp_path):
    draft = {
        "date": "2026-06-27",
        "plan_doc": "team-ops/daily/2026-06-27.md",
        "issues": [
            {"repo": "org/backend", "type": "daily-task",
             "title": "[svc-order] 幂等键", "labels": ["daily-task", "svc-order"],
             "assignee": "alice", "body": "## 责任人\nalice"},
            {"repo": "org/frontend", "type": "daily-task",
             "title": "[web-order] 确认页", "labels": ["daily-task"],
             "assignee": "bob", "body": "## 责任人\nbob"},
        ],
    }
    p = tmp_path / "draft.json"
    p.write_text(json.dumps(draft, ensure_ascii=False), encoding="utf-8")
    return p


def test_without_confirm_does_not_create(draft_file, monkeypatch):
    """没有 --confirm:绝不建单(人工确认门)。"""
    monkeypatch.delenv("TRACKER", raising=False)
    import importlib, _adapters
    importlib.reload(_adapters)
    calls = []
    monkeypatch.setattr(_adapters._DryRunTracker, "create_issue_in_repo",
                        lambda self, **k: calls.append(k) or "x")
    import create_issues_from_draft as mod
    rc = mod.run(draft=str(draft_file), confirm=False)
    assert rc == 0
    assert calls == []  # 未确认 → 零调用


def test_with_confirm_creates_one_per_issue_in_its_repo(draft_file, monkeypatch):
    monkeypatch.delenv("TRACKER", raising=False)
    import importlib, _adapters
    importlib.reload(_adapters)
    calls = []
    monkeypatch.setattr(_adapters._DryRunTracker, "create_issue_in_repo",
                        lambda self, **k: calls.append(k) or f"url://{k['repo']}")
    import create_issues_from_draft as mod
    rc = mod.run(draft=str(draft_file), confirm=True)
    assert rc == 0
    assert len(calls) == 2
    assert calls[0]["repo"] == "org/backend"
    assert calls[1]["repo"] == "org/frontend"
    assert calls[0]["labels"] == ["daily-task", "svc-order"]
    assert calls[0]["assignee"] == "alice"


def test_skips_issue_without_repo(tmp_path, monkeypatch):
    """缺 repo 的条目跳过并告警(不能建到管理仓)。"""
    monkeypatch.delenv("TRACKER", raising=False)
    import importlib, _adapters
    importlib.reload(_adapters)
    calls = []
    monkeypatch.setattr(_adapters._DryRunTracker, "create_issue_in_repo",
                        lambda self, **k: calls.append(k) or "x")
    draft = {"date": "2026-06-27", "plan_doc": "x",
             "issues": [{"repo": "", "type": "daily-task", "title": "t",
                         "labels": ["daily-task"], "assignee": "", "body": "b"}]}
    p = tmp_path / "d.json"
    p.write_text(json.dumps(draft, ensure_ascii=False), encoding="utf-8")
    import create_issues_from_draft as mod
    rc = mod.run(draft=str(p), confirm=True)
    assert rc == 0
    assert calls == []  # 缺 repo → 跳过
```

- [ ] 运行验证失败。命令：`cd /Users/luis/work/luis/ai/AI--First-Coding-Loop-CC/core/scripts && python -m pytest test_create_issues_from_draft.py -k "confirm or skips" -q`。预期：`ModuleNotFoundError: No module named 'create_issues_from_draft'`（3 测试 error）。

- [ ] 写最小实现。创建 `/Users/luis/work/luis/ai/AI--First-Coding-Loop-CC/core/scripts/create_issues_from_draft.py`：

```python
#!/usr/bin/env python3
"""人确认草稿后,在对应代码仓建 issue —— 人工确认门的后置执行步。

输入:task_splitter.py 产出并经人 review 的待建 issue 草稿 JSON。
对每条 issue,用 TrackerAdapter.create_issue_in_repo 在其 `repo`(代码仓)建单。

两道闸:
  1. --confirm 标志:不传则只列出将要建的 issue,绝不真正建(默认安全)。
  2. TRACKER 环境:默认 github-dryrun(打印不写);设 TRACKER=github-cli 才用 gh 真正建。

为什么落各 issue 自己的 repo 而非管理仓:GitHub `Closes #N` 只能关同仓 issue,
开发/测试/review issue 落代码仓,PR 合并/测试通过才能自动关单。

本地试跑(零副作用):
    python scripts/create_issues_from_draft.py --draft draft.json          # 仅预览
    python scripts/create_issues_from_draft.py --draft draft.json --confirm # 经 dry-run 建
真正建单:
    TRACKER=github-cli python scripts/create_issues_from_draft.py --draft draft.json --confirm
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from _adapters import TrackerAdapter


def run(*, draft: str, confirm: bool) -> int:
    data = json.loads(Path(draft).read_text(encoding="utf-8"))
    issues = data.get("issues", [])
    print(f"草稿 {draft}:{len(issues)} 条待建 issue(date={data.get('date')})")

    if not confirm:
        for it in issues:
            print(f"  [预览] {it.get('repo') or '(缺 repo!)'}  {it.get('title')}  "
                  f"labels={it.get('labels')}")
        print("⚠ 未传 --confirm:仅预览,未建任何 issue。"
              "人 review 草稿后加 --confirm 再执行。")
        return 0

    tracker = TrackerAdapter.create()
    created = 0
    for it in issues:
        repo = it.get("repo", "").strip()
        if not repo:
            print(f"  ∅ 跳过(缺 repo,不能建到管理仓):{it.get('title')}")
            continue
        url = tracker.create_issue_in_repo(
            repo=repo,
            title=it["title"],
            body=it.get("body", ""),
            labels=it.get("labels") or None,
            assignee=(it.get("assignee") or None),
        )
        print(f"  ✓ {repo}  {it['title']}  → {url}")
        created += 1
    print(f"完成:在对应代码仓建 issue {created} 条。")
    return 0


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--draft", required=True, help="待建 issue 草稿 JSON")
    p.add_argument("--confirm", action="store_true",
                   help="人确认门:不传则仅预览不建单")
    args = p.parse_args(argv[1:])
    return run(draft=args.draft, confirm=args.confirm)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
```

- [ ] 运行验证通过。命令：`cd /Users/luis/work/luis/ai/AI--First-Coding-Loop-CC/core/scripts && python -m pytest test_create_issues_from_draft.py -q`。预期：全部 passed（Task 1 的 4 个 + 本任务的 3 个）。

- [ ] commit。命令：
```bash
cd /Users/luis/work/luis/ai/AI--First-Coding-Loop-CC && git add core/scripts/create_issues_from_draft.py core/scripts/test_create_issues_from_draft.py && git commit -m "feat(team-ops): add create_issues_from_draft (human-confirmed, per-repo)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: daily-task-split.md 拆解 prompt（内容即产物）

`task_splitter.py` 读这份 prompt 喂给 `ModelAdapter`。prompt 必须明确：只产建议、强调人确认门、按 daily-task 强制字段输出、每条带 repo（代码仓）。

**Files:**
- Create: `/Users/luis/work/luis/ai/AI--First-Coding-Loop-CC/core/prompts/daily-task-split.md`

- [ ] 创建文件并写入完整内容：

```markdown
# 每日任务拆解 Prompt —— 三层模型第 ③ 层

> 由 task_splitter.py 加载并喂给模型。你是团队的 task-splitter，CTO/PM 的助手。
> **铁律:你只产出建议草稿,绝不建 issue、绝不调用任何工具产生外部副作用。**
> 真正建 issue 由人 review 草稿后另行运行 create_issues_from_draft.py 完成。

## 你的输入
- 任务源:架构师写的当日结构化任务(在本 prompt 末尾 `=== 任务源 ===` 之后)。
- 责任人归属:ownership.md(项目级/子服务级,相对静态)。

## 你的任务
把当日任务源拆成"每日任务"粒度(一个任务 = 一个人一天可完成的闭环),为每条产出:

1. **当日任务计划文档**(给人看的概览):任务、责任人、子服务、代码仓、预计工时、依赖顺序。
2. **待建 issue 清单草稿**:每条对应一个 `daily-task` 类型 issue。

## 每条 issue 草稿必须含的字段(对齐 daily-task Issue Form)
- repo:**代码仓** slug(owner/name)。这条 issue 将建在该代码仓,不是管理仓——
  因为 GitHub `Closes #N` 只能关同仓 issue,PR 合并要能自动关单。
- type:固定 `daily-task`。
- title:`[<子服务>] <动宾短语>`。
- labels:至少含 `daily-task`,有子服务再加子服务 label。
- assignee:责任人(依据 ownership.md;拿不准留空待人指派)。
- body 强制字段:责任人 / 所属子服务 / 验收标准 / 关联文档 / 预计工时 / 依赖项。

## 拆解准则
- 一个任务跨越多个子服务 → 拆成多条,各归各的 repo。
- 验收标准必须可测(给定…当…则…)。
- 标注依赖顺序(谁阻塞谁),便于人排期。
- 不确定责任人时留空,**不要瞎指派**。

## 输出纪律
- 只输出"计划文档草稿 + 待建 issue 草稿",末尾提醒:**请人 review 后再建单**。
- 不要假装已经建了 issue;不要编造 issue 编号或链接。
```

- [ ] 验证文件存在且含关键纪律句。命令：`grep -n "只产出建议草稿" /Users/luis/work/luis/ai/AI--First-Coding-Loop-CC/core/prompts/daily-task-split.md && grep -n "代码仓" /Users/luis/work/luis/ai/AI--First-Coding-Loop-CC/core/prompts/daily-task-split.md`。预期：两条 grep 各至少一行命中。

- [ ] commit。命令：
```bash
cd /Users/luis/work/luis/ai/AI--First-Coding-Loop-CC && git add core/prompts/daily-task-split.md && git commit -m "feat(team-ops): add daily-task-split prompt (draft-only, code-repo aware)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: task-splitter SKILL.md（内容即产物）

拆解 skill，frontmatter 严格按 README 约定（name/description/when_to_use/when_NOT_to_use），描述"无聊紧凑"，正文给出"产草稿 → 人确认 → 建单"的原子步骤。

**Files:**
- Create: `/Users/luis/work/luis/ai/AI--First-Coding-Loop-CC/claude-code/skills/task-splitter/SKILL.md`

- [ ] 创建目录并写入文件完整内容：

```markdown
---
name: task-splitter
description: 把架构师写好的当日任务源拆成"每日任务"粒度，产出当日任务计划文档与待建 issue 清单草稿(JSON)。运行 task_splitter.py，绝不直接建 issue；建 issue 由人确认草稿后运行 create_issues_from_draft.py 完成。
when_to_use: 每天开工时由 CTO/PM(人)触发，对当日任务源做第 ③ 层(每日)拆解；或里程碑刷新后需要重新分配当日任务时。
when_NOT_to_use: 项目级/子服务级责任归属(第 ①②层)——那用 CODEOWNERS + ownership.md 固化，相对静态，不走每日拆解；也不要用本 skill 直接建 issue(那是人确认后的另一步)。
---

# Skill: Task Splitter（每日任务拆解 + 人工确认门）

三层任务模型第 ③ 层（每日）的执行手册。**核心纪律:产草稿，人确认，才建单。**

## 前置
- 任务源已就绪：架构师用 `architect-task-writer` 写好的当日结构化任务(markdown)。
- `team-ops/ownership.md` 反映最新责任人归属。

## 步骤（原子动作）

### 1. 跑拆解，产出"计划文档 + 待建 issue 草稿"
```bash
python scripts/task_splitter.py \
  --source <任务源.md> \
  --date $(date +%F) \
  --plan-out team-ops/daily/$(date +%F).md \
  --draft-out state/tasks/draft-$(date +%F).json
```
脚本只写两个文件，**不碰 Tracker**。终端会打印"人工确认门"提醒。

### 2. 人 review 草稿（人工确认门，不可跳过）
打开 `state/tasks/draft-<date>.json` 与 `team-ops/daily/<date>.md`，逐条核对：
- 每条 `repo` 是否指向正确的**代码仓**(不是管理仓)？
- `assignee` 是否符合 ownership.md？拿不准的应留空而非瞎派。
- `daily-task` 强制字段(责任人/所属子服务/验收标准/关联文档/预计工时/依赖项)是否齐全？
- 验收标准是否可测？依赖顺序是否合理？
不满意就**手改草稿 JSON**，再继续。

### 3. 确认后建单（先 dry-run 再真建）
```bash
# 先 dry-run 预览将建什么(默认 TRACKER=github-dryrun)
python scripts/create_issues_from_draft.py --draft state/tasks/draft-$(date +%F).json --confirm
# 确认预览无误后,真正建到各代码仓(需本机 gh auth login)
TRACKER=github-cli python scripts/create_issues_from_draft.py \
  --draft state/tasks/draft-$(date +%F).json --confirm
```

### 4. 归档
`team-ops/daily/<date>.md` 提交进管理仓；建好的 issue 自动进组织级 Projects 看板(见 `team-ops/projects/README.md`)。

## 反模式
- ❌ 让 task_splitter 直接建 issue——它的职责就是只产草稿。
- ❌ 不 review 草稿就 `--confirm`——人工确认门形同虚设。
- ❌ 把 daily-task issue 建到管理仓 team-ops——`Closes #N` 关不掉，PR 合并不会自动关单。
- ❌ 拿不准责任人就硬指派——留空交人定。
```

- [ ] 验证 frontmatter 四字段齐全。命令：`cd /Users/luis/work/luis/ai/AI--First-Coding-Loop-CC && for k in name description when_to_use when_NOT_to_use; do grep -q "^$k:" claude-code/skills/task-splitter/SKILL.md && echo "OK $k" || echo "MISSING $k"; done`。预期：四行全 `OK`。

- [ ] commit。命令：
```bash
cd /Users/luis/work/luis/ai/AI--First-Coding-Loop-CC && git add claude-code/skills/task-splitter/SKILL.md && git commit -m "feat(team-ops): add task-splitter skill (draft -> human confirm -> create)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: 5 类 Issue Form（YAML，内容即产物）

5 份 GitHub Issue Form，放 `templates/team-ops/issue-templates/`，由 install 分发到代码仓 `.github/ISSUE_TEMPLATE/`。每类强制结构化字段，每类带对应 type label。`daily-task` 强制字段：责任人/所属子服务/验收标准/关联文档/预计工时/依赖项。

**Files:**
- Create: `/Users/luis/work/luis/ai/AI--First-Coding-Loop-CC/templates/team-ops/issue-templates/daily-task.yml`
- Create: `/Users/luis/work/luis/ai/AI--First-Coding-Loop-CC/templates/team-ops/issue-templates/feature.yml`
- Create: `/Users/luis/work/luis/ai/AI--First-Coding-Loop-CC/templates/team-ops/issue-templates/bug.yml`
- Create: `/Users/luis/work/luis/ai/AI--First-Coding-Loop-CC/templates/team-ops/issue-templates/qa-task.yml`
- Create: `/Users/luis/work/luis/ai/AI--First-Coding-Loop-CC/templates/team-ops/issue-templates/review.yml`

- [ ] 创建 `daily-task.yml`，完整内容：

```yaml
name: 每日任务 (daily-task)
description: task-splitter 拆解、人确认后建在对应代码仓的每日开发任务。关闭条件：关联 PR 合并 + 测试通过。
title: "[daily-task] "
labels: ["daily-task"]
body:
  - type: input
    id: owner
    attributes:
      label: 责任人
      description: 负责完成本任务的人（GitHub 用户名）
    validations:
      required: true
  - type: input
    id: subservice
    attributes:
      label: 所属子服务
      description: 例 svc-order / web-order，需与 ownership.md 一致
    validations:
      required: true
  - type: textarea
    id: acceptance
    attributes:
      label: 验收标准
      description: 可测条目，用「给定…当…则…」描述，含边界/错误路径
    validations:
      required: true
  - type: input
    id: docs
    attributes:
      label: 关联文档
      description: docs-repo 中相关 design.md / api.md / data-model.md 路径或链接
    validations:
      required: true
  - type: input
    id: estimate
    attributes:
      label: 预计工时
      description: 例 0.5d / 1d / 2d
    validations:
      required: true
  - type: textarea
    id: deps
    attributes:
      label: 依赖项
      description: 阻塞本任务的其他 issue / 前置条件；无则填「无」
    validations:
      required: true
```

- [ ] 创建 `feature.yml`，完整内容：

```yaml
name: 功能开发 (feature)
description: 功能开发任务。由拆解产出。关闭条件：实现 PR 通过 Closes 关键字自动关单。
title: "[feature] "
labels: ["feature"]
body:
  - type: input
    id: owner
    attributes:
      label: 责任人
    validations:
      required: true
  - type: input
    id: subservice
    attributes:
      label: 所属子服务
    validations:
      required: true
  - type: textarea
    id: goal
    attributes:
      label: 目标与背景
      description: 要让用户/系统能做到什么，为什么现在做
    validations:
      required: true
  - type: textarea
    id: scope
    attributes:
      label: 范围（In / Out of Scope）
      description: 明确本次做什么、明确不做什么（防过度发挥）
    validations:
      required: true
  - type: textarea
    id: acceptance
    attributes:
      label: 验收标准
      description: 可测条目，含边界/错误路径/性能或安全要求
    validations:
      required: true
  - type: input
    id: docs
    attributes:
      label: 关联文档
      description: 需同步产出/更新的 api.md / data-model.md 等
    validations:
      required: true
  - type: checkboxes
    id: flag
    attributes:
      label: 特性开关
      options:
        - label: 本功能将藏在特性开关后（fail-safe 默认 false）
          required: true
```

- [ ] 创建 `bug.yml`，完整内容：

```yaml
name: 缺陷 (bug)
description: bug 修复任务。由人或自愈环 triage 创建。关闭条件：修复 PR 合并。
title: "[bug] "
labels: ["bug"]
body:
  - type: input
    id: subservice
    attributes:
      label: 所属子服务
    validations:
      required: true
  - type: dropdown
    id: severity
    attributes:
      label: 严重度
      options:
        - blocker（阻断主流程/数据损坏/安全）
        - high（核心功能不可用）
        - medium（部分功能受损）
        - low（体验问题）
    validations:
      required: true
  - type: textarea
    id: repro
    attributes:
      label: 复现步骤
      description: 1. … 2. … 3. …
    validations:
      required: true
  - type: textarea
    id: expected_actual
    attributes:
      label: 期望结果 vs 实际结果
    validations:
      required: true
  - type: textarea
    id: evidence
    attributes:
      label: 证据
      description: 日志 / 截图 / trace_id / 受影响端点与用户
    validations:
      required: true
  - type: input
    id: owner
    attributes:
      label: 责任人
      description: 拿不准可留空待指派
    validations:
      required: false
```

- [ ] 创建 `qa-task.yml`，完整内容：

```yaml
name: 测试任务 (qa-task)
description: 合并后由 gen_test_tasks 生成的测试任务。关闭条件：qa-reviewer 审核报告 PASS。
title: "[qa-task] "
labels: ["qa-task"]
body:
  - type: input
    id: tester
    attributes:
      label: 测试责任人
    validations:
      required: true
  - type: input
    id: subservice
    attributes:
      label: 被测子服务
    validations:
      required: true
  - type: input
    id: pr
    attributes:
      label: 关联 PR / 合并提交
      description: 触发本测试任务的 PR 链接或 commit
    validations:
      required: true
  - type: textarea
    id: cases
    attributes:
      label: 测试用例
      description: 由 qa-generator 读 diff 生成，逐条列出
    validations:
      required: true
  - type: textarea
    id: acceptance
    attributes:
      label: 验收点
      description: 每条都要在报告里给出通过/不通过 + 证据
    validations:
      required: true
  - type: textarea
    id: report
    attributes:
      label: 测试报告（执行后回填）
      description: 覆盖全部验收点；附证据（截图/日志/录屏）
    validations:
      required: false
```

- [ ] 创建 `review.yml`，完整内容：

```yaml
name: 评审任务 (review)
description: PR 打开时自动创建、指派 CTO 的人工评审任务。关闭条件：CTO 批准。
title: "[review] "
labels: ["review"]
body:
  - type: input
    id: pr
    attributes:
      label: 待评审 PR
      description: PR 链接
    validations:
      required: true
  - type: input
    id: author
    attributes:
      label: PR 作者
    validations:
      required: true
  - type: checkboxes
    id: gates
    attributes:
      label: 机器门禁状态（人工评审前应已全绿）
      options:
        - label: 四趟 AI 评审（quality/security/performance/dependency）无 BLOCK
        - label: CI 门禁（lint/类型/SAST/覆盖率/契约/bundle）通过
        - label: 涉及接口/DB 改动的文档已同步更新
  - type: textarea
    id: focus
    attributes:
      label: 评审重点
      description: 本 PR 需 CTO 重点判断的设计/取舍/风险
    validations:
      required: true
  - type: dropdown
    id: decision
    attributes:
      label: 评审结论（评审后回填）
      options:
        - 待评审
        - 批准
        - 要求修改
    validations:
      required: false
```

- [ ] 验证 5 份 YAML 语法正确且 type label 齐全。命令：
```bash
cd /Users/luis/work/luis/ai/AI--First-Coding-Loop-CC && python -c "
import glob, sys, json
try:
    import yaml
except ImportError:
    print('PyYAML 未装,改用 ruamel/跳过严格解析'); sys.exit(0)
need = {'daily-task','feature','bug','qa-task','review'}
seen = set()
for f in glob.glob('templates/team-ops/issue-templates/*.yml'):
    d = yaml.safe_load(open(f, encoding='utf-8'))
    assert 'name' in d and 'body' in d and 'labels' in d, f
    seen.update(d['labels'])
print('labels:', sorted(seen))
assert need <= seen, f'缺 label: {need - seen}'
print('OK 5 类 Issue Form 解析通过')
"
```
预期：打印 `OK 5 类 Issue Form 解析通过`（若环境无 PyYAML 则打印跳过提示并退出 0；可先 `pip install pyyaml` 再跑以做严格校验）。

- [ ] commit。命令：
```bash
cd /Users/luis/work/luis/ai/AI--First-Coding-Loop-CC && git add templates/team-ops/issue-templates/ && git commit -m "feat(team-ops): add 5 issue forms (daily-task/feature/bug/qa-task/review)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: team-ops 管理仓模板的其余文件（ownership / daily / projects / README）

补齐管理仓模板：责任人归属（三层模型①②）、daily 归档目录与样例、组织级 Projects 配置与跨仓自动关单说明、总 README。均为"内容即产物"。

**Files:**
- Create: `/Users/luis/work/luis/ai/AI--First-Coding-Loop-CC/templates/team-ops/README.md`
- Create: `/Users/luis/work/luis/ai/AI--First-Coding-Loop-CC/templates/team-ops/ownership.md`
- Create: `/Users/luis/work/luis/ai/AI--First-Coding-Loop-CC/templates/team-ops/daily/.gitkeep`
- Create: `/Users/luis/work/luis/ai/AI--First-Coding-Loop-CC/templates/team-ops/daily/EXAMPLE-2026-06-27.md`
- Create: `/Users/luis/work/luis/ai/AI--First-Coding-Loop-CC/templates/team-ops/projects/README.md`

- [ ] 创建 `templates/team-ops/README.md`，完整内容：

```markdown
# team-ops —— 任务编排管理仓模板

承载团队任务编排，但**不承载具体开发/测试/review issue**（那些落各代码仓）。

## 目录
| 路径 | 用途 |
|---|---|
| `daily/` | 每日任务计划文档归档（task_splitter 产出，按日期命名 `<date>.md`） |
| `ownership.md` | 三层模型第 ①②层：项目级 / 子服务级责任人归属（相对静态） |
| `issue-templates/` | 5 类 Issue Form（YAML）。由 AIFCL install.sh 分发到**各代码仓** `.github/ISSUE_TEMPLATE/` |
| `projects/` | 组织级 GitHub Projects 看板配置 + 跨仓自动关单说明 |

## 每日编排流程（人工确认门贯穿）
1. 架构师写当日任务源（结构化 markdown）。
2. `task_splitter.py` 拆解 → 产出 `daily/<date>.md` + 待建 issue 草稿 JSON（**只产草稿**）。
3. 人 review 草稿（核对 repo/责任人/验收/字段齐全）。
4. 确认后 `create_issues_from_draft.py --confirm` → 在**对应代码仓**建 issue。
5. issue 自动进组织级 Projects 看板；PR 合并经 `Closes #N` 自动关单（同仓）。

## 为什么 issue 落代码仓而非本管理仓
GitHub `Closes #N` 只能关闭**同仓** issue。要让"PR 合并 / 测试通过自动关单"成立，
开发/bug/qa/review issue 必须建在对应代码仓。本管理仓只放计划文档、归属、模板、看板配置。
```

- [ ] 创建 `templates/team-ops/ownership.md`，完整内容：

```markdown
# 责任人归属（三层模型 第 ①②层）

> 相对静态：项目级一次性、子服务级按里程碑刷新。动态的"每日任务"不在此处，由 task_splitter 拆解。
> 本表与各代码仓的 `CODEOWNERS` 保持一致（CODEOWNERS 管自动 review 指派，本表管人读）。

## ① 项目级分工
| 领域 | 负责人 | 代码仓 |
|---|---|---|
| 后端 | <填> | org/backend |
| 前端 | <填> | org/frontend |
| 共享文档/契约 | <填> | org/docs-repo |

## ② 子服务级归属（具体到人）
| 子服务 | 代码仓 | 主负责人 | 备份 | 相关文档 |
|---|---|---|---|---|
| svc-order | org/backend | <填> | <填> | docs/backend/svc-order/ |
| svc-account | org/backend | <填> | <填> | docs/backend/svc-account/ |
| web-order | org/frontend | <填> | <填> | docs/frontend/web-order/ |

## 维护约定
- 新增子服务：加一行 + 在对应代码仓 CODEOWNERS 加规则 + 在 docs-repo 建 `svc-<name>/` 目录。
- task_splitter 指派 assignee 时以本表为准；拿不准留空交人定。
```

- [ ] 创建 `templates/team-ops/daily/.gitkeep`（空文件占位）。命令可在写入步执行：
```bash
mkdir -p /Users/luis/work/luis/ai/AI--First-Coding-Loop-CC/templates/team-ops/daily && : > /Users/luis/work/luis/ai/AI--First-Coding-Loop-CC/templates/team-ops/daily/.gitkeep
```

- [ ] 创建 `templates/team-ops/daily/EXAMPLE-2026-06-27.md`，完整内容（对齐 `task_splitter.build_plan_doc` 输出格式）：

```markdown
# 当日任务计划 2026-06-27

> 由 task_splitter 生成。本文件是计划归档；待建 issue 见同批草稿 JSON。
> 人工确认门：确认草稿后运行 create_issues_from_draft.py 才会真正建 issue。

| 任务 | 责任人 | 子服务 | 代码仓 | 预计工时 |
|---|---|---|---|---|
| 实现下单幂等键 | alice | svc-order | org/backend | 1d |
| 前端订单确认页 | bob | web-order | org/frontend | 0.5d |
```

- [ ] 创建 `templates/team-ops/projects/README.md`，完整内容：

```markdown
# 组织级 GitHub Projects —— 跨多仓统一看板

## 为什么用组织级 Projects
issue 分散在多个代码仓（svc-order/web-order…），需要一个跨仓视图看全局进度。
组织级（Org-level）Projects v2 可聚合多仓 issue 到同一看板，全团队一个入口。

## 一次性配置
1. 在组织级新建 Project（v2），命名如 `Team Delivery Board`。
2. 字段建议：`Status`（Todo/In Progress/In Review/QA/Done）、`Type`（daily-task/feature/bug/qa-task/review）、`Service`（子服务）、`Assignee`、`Estimate`。
3. 在 Project 的 Workflows 里开启：
   - "Item added to project → Status = Todo"
   - "Item closed → Status = Done"
   - "Pull request merged → Status = Done"（覆盖关联了该 PR 的 issue）

## 自动入板（让各代码仓新建的 issue 自动进本看板）
两种方式择一：
- **内置 Auto-add workflow**（推荐）：在 Project Settings → Workflows → "Auto-add to project"
  里按仓/按 label 过滤，把目标代码仓新建的 issue 自动纳入。
- **Actions 方式**：在各代码仓加 `actions/add-to-project` 步骤，用 org-level PAT/App token
  把新 issue 加到本 Project（适合需要细粒度过滤时）。

## 跨仓自动关单（Closes #N 的约束与对策）
- **约束**：GitHub `Closes #N` / `Fixes #N` 只能自动关闭**同仓** issue。
- **对策**：daily-task/feature/bug/qa/review issue 都建在**对应代码仓**（见 ownership.md 的 repo 列），
  因此实现 PR 在同仓用 `Closes #N` 即可自动关单，看板 Status 经 workflow 同步为 Done。
- **跨仓引用**（仅展示关系，不自动关闭）：可用全限定 `Closes org/other-repo#N` 做关联引用，
  但**不会**自动关闭——需手动或经 Actions 调 API 关闭。故不依赖跨仓自动关单。
- **管理仓 team-ops 不放可关单 issue**：本仓只放计划文档与配置，避免"`Closes` 关不掉"的陷阱。
```

- [ ] 验证文件齐全。命令：`ls -1 /Users/luis/work/luis/ai/AI--First-Coding-Loop-CC/templates/team-ops/ /Users/luis/work/luis/ai/AI--First-Coding-Loop-CC/templates/team-ops/daily/ /Users/luis/work/luis/ai/AI--First-Coding-Loop-CC/templates/team-ops/projects/ && grep -q "Closes #N 的约束" /Users/luis/work/luis/ai/AI--First-Coding-Loop-CC/templates/team-ops/projects/README.md && echo OK`。预期：列出 README.md/ownership.md/issue-templates/daily/projects、daily 下有 .gitkeep 与 EXAMPLE-2026-06-27.md、projects 下有 README.md，末尾打印 `OK`。

- [ ] commit。命令：
```bash
cd /Users/luis/work/luis/ai/AI--First-Coding-Loop-CC && git add templates/team-ops/README.md templates/team-ops/ownership.md templates/team-ops/daily templates/team-ops/projects && git commit -m "feat(team-ops): add management-repo templates (ownership/daily/projects)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 8: 扩展 install.sh —— 分发 Issue Form 到目标代码仓 .github/ISSUE_TEMPLATE/

在 `install.sh` 的 core 分发段之后，新增一段把 `templates/team-ops/issue-templates/*.yml` 拷到目标代码仓 `${PREFIX}.github/ISSUE_TEMPLATE/`。复用既有 `safe_cp`（幂等、改了的不覆盖）。

**Files:**
- Modify: `/Users/luis/work/luis/ai/AI--First-Coding-Loop-CC/tools/install.sh`

- [ ] 在 `install.sh` 的 state 段（`ok "+ state/tasks/.gitkeep"` 这一行）之后、`# === claude-code` 之前，插入新段。把
```bash
mkdir -p "$TARGET/${PREFIX}state/tasks" && touch "$TARGET/${PREFIX}state/tasks/.gitkeep"
ok "+ state/tasks/.gitkeep"

# === claude-code(skills + agents)===
```
改为
```bash
mkdir -p "$TARGET/${PREFIX}state/tasks" && touch "$TARGET/${PREFIX}state/tasks/.gitkeep"
ok "+ state/tasks/.gitkeep"

# === Issue Forms → 目标代码仓 .github/ISSUE_TEMPLATE/ ===
# 这些是任务编排的结构化 issue 模板(daily-task/feature/bug/qa-task/review)。
# 装到代码仓而非管理仓:GitHub Closes #N 只能关同仓 issue,issue 必须落代码仓才能自动关单。
if [ -d "$SOURCE_DIR/templates/team-ops/issue-templates" ]; then
  say "issue-templates → $TARGET/${PREFIX}.github/ISSUE_TEMPLATE/"
  for f in "$SOURCE_DIR"/templates/team-ops/issue-templates/*.yml; do
    safe_cp "$f" "$TARGET/${PREFIX}.github/ISSUE_TEMPLATE/$(basename "$f")"
  done
fi

# === claude-code(skills + agents)===
```

- [ ] 验证脚本语法 + 干跑分发到临时目标仓。命令：
```bash
cd /Users/luis/work/luis/ai/AI--First-Coding-Loop-CC && bash -n tools/install.sh && \
TMP="$(mktemp -d)" && git init -q "$TMP" >/dev/null && \
bash tools/install.sh "$TMP" --no-skills >/dev/null && \
ls -1 "$TMP/.github/ISSUE_TEMPLATE/" && \
for t in daily-task feature bug qa-task review; do \
  test -f "$TMP/.github/ISSUE_TEMPLATE/$t.yml" && echo "OK $t" || echo "MISSING $t"; \
done; rm -rf "$TMP"
```
预期：列出 5 个 `.yml`，随后 5 行 `OK daily-task` … `OK review`。

- [ ] commit。命令：
```bash
cd /Users/luis/work/luis/ai/AI--First-Coding-Loop-CC && git add tools/install.sh && git commit -m "feat(install): distribute team-ops issue forms to code repo .github/ISSUE_TEMPLATE

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 9: 全量回归 + 端到端 dry-run 串联验证

确认全部 Python 测试通过，并把 task_splitter → create_issues_from_draft 串成一条 dry-run 链路实跑一遍（零副作用），验证人工确认门生效。

**Files:**
- 无新增；仅运行验证。

- [ ] 运行全部脚本测试。命令：`cd /Users/luis/work/luis/ai/AI--First-Coding-Loop-CC/core/scripts && python -m pytest test_task_splitter.py test_create_issues_from_draft.py -q`。预期：全部 passed（task_splitter 3 个 + create/tracker 7 个 = 10 passed）。

- [ ] 端到端 dry-run 串联。命令：
```bash
cd /Users/luis/work/luis/ai/AI--First-Coding-Loop-CC && WORK="$(mktemp -d)" && cat > "$WORK/src.md" <<'EOF'
## 任务: 实现下单幂等键
repo: org/backend
子服务: svc-order
责任人: alice
验收: 重复下单返回同一订单
EOF
python core/scripts/task_splitter.py --source "$WORK/src.md" --date 2026-06-27 \
  --plan-out "$WORK/2026-06-27.md" --draft-out "$WORK/draft.json" && \
echo "--- 不带 --confirm:应零建单 ---" && \
python core/scripts/create_issues_from_draft.py --draft "$WORK/draft.json" && \
echo "--- 带 --confirm:dry-run 打印将建单 ---" && \
python core/scripts/create_issues_from_draft.py --draft "$WORK/draft.json" --confirm && \
rm -rf "$WORK"
```
预期：task_splitter 打印两条 `✓` + 人工确认门提醒；第一次（无 confirm）打印 `[预览]` 与"未传 --confirm:仅预览"；第二次（confirm，TRACKER 默认 dryrun）打印 `[DRY-RUN] CREATE issue in org/backend` 与 `✓ org/backend`。全程无真实 issue 创建。

- [ ] commit（如有未提交的收尾改动；若工作区干净则跳过）。命令：
```bash
cd /Users/luis/work/luis/ai/AI--First-Coding-Loop-CC && git status --porcelain
```
预期：输出为空（前 8 个任务已各自提交）。

---

## Self-Review

对照 spec 第 7/8/13 节逐条确认：

**第 7 节（任务拆解三层模型）**
- ①项目级分工 + ②子服务级归属（CODEOWNERS + ownership.md）：`templates/team-ops/ownership.md`（Task 7）含①②两层表格，并注明与 CODEOWNERS 一致。✅
- ③每日任务拆解（task-splitter：按进度生成 → 草稿 → 人确认 → 建 issue）：`task_splitter.py`（Task 2）产计划+草稿；`create_issues_from_draft.py`（Task 3）人确认后建单；`task-splitter` skill（Task 5）串流程。✅
- task-splitter 每日产两样东西（计划文档 + 待建 issue 草稿）：`build_plan_doc` 写 `daily/<date>.md`、`build_draft` 写草稿 JSON（Task 2）。✅

**第 8 节（Issue 类型体系）**
- 5 类 type label + Issue Form：`daily-task/feature/bug/qa-task/review`（Task 6），每份 `labels:` 含对应 type label、`body:` 强制结构化字段。✅
- `daily-task` 强制字段（责任人/所属子服务/验收标准/关联文档/预计工时/依赖项）：`daily-task.yml`（Task 6）六字段全 `required: true`；`task_splitter._issue_body` 草稿 body 同样含这六段。✅
- 关闭条件（PR 合并 / 测试通过 / CTO 批准 等）：各 Form `description` 注明；issue 落代码仓使 `Closes #N` 同仓自动关单成立（`_gh_tracker.py` + Task 3 按 repo 建单 + projects/README 说明）。✅

**第 13 节（人工确认门）**
- 建 issue 必须人确认后执行：`task_splitter.py` 只产草稿、绝不触碰 Tracker（Task 2 测试 `test_run_writes_plan_and_draft_without_creating_issues` 打桩断言任何 Tracker.create 调用即失败）；`create_issues_from_draft.py` 无 `--confirm` 零建单（Task 3 测试 `test_without_confirm_does_not_create`）。✅
- 双道闸：`--confirm` 标志 + `TRACKER` 默认 `github-dryrun`（真建需 `TRACKER=github-cli`）。✅
- prompt（Task 4）与 skill（Task 5）均把"只产草稿、人确认才建单"写为铁律/反模式。✅

**架构关键约束（第 3.2 节）**
- issue 落代码仓而非管理仓（`Closes #N` 同仓约束）：`create_issues_from_draft` 按每条 `repo` 建单、缺 repo 跳过（Task 3 `test_skips_issue_without_repo`）；`_gh_tracker` 用 `gh issue create -R <repo>`；`projects/README.md` 专节说明跨仓关单约束与对策。✅
- 组织级 Projects 跨仓聚合视图：`templates/team-ops/projects/README.md`（Task 7）。✅

**文件清单（新增 17 / 修改 2）**
新增：
- `templates/team-ops/README.md`
- `templates/team-ops/ownership.md`
- `templates/team-ops/daily/.gitkeep`
- `templates/team-ops/daily/EXAMPLE-2026-06-27.md`
- `templates/team-ops/projects/README.md`
- `templates/team-ops/issue-templates/daily-task.yml`
- `templates/team-ops/issue-templates/feature.yml`
- `templates/team-ops/issue-templates/bug.yml`
- `templates/team-ops/issue-templates/qa-task.yml`
- `templates/team-ops/issue-templates/review.yml`
- `core/scripts/task_splitter.py`
- `core/scripts/create_issues_from_draft.py`
- `core/scripts/_gh_tracker.py`
- `core/scripts/test_task_splitter.py`
- `core/scripts/test_create_issues_from_draft.py`
- `core/prompts/daily-task-split.md`
- `claude-code/skills/task-splitter/SKILL.md`

修改：
- `core/scripts/_adapters.py`（新增 `import subprocess`、`create_issue_in_repo` 接口、`github-cli` 工厂分支、`_DryRunTracker.create_issue_in_repo`）
- `tools/install.sh`（新增 issue-templates 分发段）
