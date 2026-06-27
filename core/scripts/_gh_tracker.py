"""GitHub Issues 适配器(基于 gh CLI)。

与 _adapters.py 里面向"运维指纹工单"的 Tracker 不同,本文件专注
"在指定代码仓用结构化字段建 issue"——服务于每日任务拆解的人工确认门后置执行。

为什么落代码仓而非管理仓:GitHub 的 `Closes #N` 自动关闭关键字只能关同仓 issue,
开发/bug/测试/review issue 必须建在对应代码仓,PR 合并才能自动关单。
"""
from __future__ import annotations

import _adapters


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
        proc = _adapters.subprocess.run(args, capture_output=True, text=True, check=True)
        return proc.stdout.strip()
