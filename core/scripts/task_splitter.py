#!/usr/bin/env python3
"""每日任务拆解 — 三层模型第 ③ 层(每日)。

读"任务源"(架构师写的结构化任务文本)+ ownership.md(责任人归属),
用纯确定性机器拆解(parse_source 解析结构化字段),产出两样东西:
  1. 当日任务计划文档(markdown,归档到 team-ops/daily/<date>.md)
  2. 待建 issue 清单草稿(JSON)

不调模型:拆解完全确定、零副作用。prompts/daily-task-split.md 保留供人/未来使用。
人工确认门(本脚本的硬约束):只产草稿,绝不创建 issue、绝不触碰 Tracker。
建 issue 是 create_issues_from_draft.py 在人确认草稿后才做的事。

本地试跑(确定性拆解,零副作用):
    python scripts/task_splitter.py --source tasks-source.md --date 2026-06-27 \
        --plan-out team-ops/daily/2026-06-27.md --draft-out draft.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


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


def run(*, source: str, date: str, plan_out: str, draft_out: str,
        ownership: str | None = None) -> int:
    # 纯确定性机器拆解:parse_source 即唯一事实来源,零模型调用、零副作用。
    src_text = Path(source).read_text(encoding="utf-8")
    tasks = parse_source(src_text)

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
