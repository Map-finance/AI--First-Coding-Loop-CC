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
