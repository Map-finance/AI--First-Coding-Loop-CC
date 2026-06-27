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
