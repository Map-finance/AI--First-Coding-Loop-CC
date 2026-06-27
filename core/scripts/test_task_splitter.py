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
