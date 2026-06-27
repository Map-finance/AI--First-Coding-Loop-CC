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
