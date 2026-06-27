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
            # 歧义行（同含 BLOCK 与 PASS）保守取更严的 BLOCK，与缺判定默认一致
            if "BLOCK" in s:
                return "BLOCK"
            if "PASS" in s:
                return "PASS"
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
