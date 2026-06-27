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
