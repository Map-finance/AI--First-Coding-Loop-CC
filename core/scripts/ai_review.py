#!/usr/bin/env python3
"""ai_review — 模型无关的 PR 评审脚本(替代 anthropics/claude-code-action)。

为什么独立写:
  anthropics/claude-code-action 只能跑 Claude。v2.1 起 harness 支持任意 LLM
  (Anthropic/OpenAI/DeepSeek/Qwen/Kimi/GLM/...),所以评审 workflow 不能锁死在
  某一家 action。本脚本把"读 diff → 调 LLM → 解析 VERDICT → 发评审 → 决定门禁"
  做成一段可移植的 Python,任何厂商都能跑。

用法(在 GitHub Actions 里):
  python3 scripts/ai_review.py --pass quality      # 第 1 趟:质量
  python3 scripts/ai_review.py --pass security     # 第 2 趟:安全
  python3 scripts/ai_review.py --pass performance  # 第 3 趟:性能/韧性/可观测
  python3 scripts/ai_review.py --pass dependency   # 第 4 趟:依赖

退出码:
  0 = PASS,1 = BLOCK(让 ci-gate 红),2 = 配置错误

读取的 env(在 workflow 里设):
  LLM_PROVIDER, LLM_API_KEY[, LLM_BASE_URL], LLM_MODEL_<ROLE>
  GITHUB_TOKEN, GITHUB_REPOSITORY, PR_NUMBER, BASE_REF

零凭证试跑:
  python3 scripts/ai_review.py --pass quality --mock
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from _adapters import ModelAdapter, record_token_usage

# v2.2: 支持 reusable workflow 场景——被另一个仓 uses: 调用时,prompts/ 不在 cwd 下;
# 工作流可设 AIFCL_PROMPTS_DIR=_aifcl/core/prompts 指过去。默认仍是 ./prompts。
_PROMPTS_DIR = os.getenv("AIFCL_PROMPTS_DIR", "prompts")
PROMPTS = {
    "quality":     f"{_PROMPTS_DIR}/review-quality.md",
    "security":    f"{_PROMPTS_DIR}/review-security.md",
    "performance": f"{_PROMPTS_DIR}/review-performance.md",
    "dependency":  f"{_PROMPTS_DIR}/review-dependency.md",
}

# 四趟与 sub-agent 的对应关系(影响 LLM_MODEL_<ROLE> 的覆盖键)
PASS_ROLE = {
    "quality":     "verifier-quality",
    "security":    "verifier-security",
    "performance": "verifier-performance",
    "dependency":  "verifier-dependency",
}


def sh(*args: str, **kw) -> str:
    return subprocess.run(args, capture_output=True, text=True, **kw).stdout


def collect_diff(base_ref: str) -> str:
    sh("git", "fetch", "--quiet", "origin", base_ref, check=False)
    return sh("git", "diff", f"origin/{base_ref}...HEAD")


def collect_dep_diff(base_ref: str) -> str:
    """依赖趟只看依赖清单变化,降本。"""
    return sh(
        "git", "diff", f"origin/{base_ref}...HEAD", "--",
        "**/package.json", "pnpm-lock.yaml",
        "go.mod", "go.sum",
        "requirements*.txt", "pyproject.toml",
        "Cargo.toml", "Cargo.lock",
    )


def post_pr_comment(repo: str, pr: str, token: str, body: str) -> None:
    """用 gh CLI 发 PR 评论(workflow 里 gh 总是装好的)。"""
    env = os.environ.copy()
    env["GH_TOKEN"] = token
    subprocess.run(
        ["gh", "pr", "comment", pr, "--repo", repo, "--body", body],
        env=env, check=False,
    )


def parse_verdict(text: str) -> str:
    """从模型输出末尾找 VERDICT: PASS|BLOCK。容错:有时模型会写在中间。"""
    for line in reversed(text.splitlines()):
        s = line.strip().upper()
        if s.startswith("VERDICT:"):
            if "BLOCK" in s:
                return "BLOCK"
            if "PASS" in s:
                return "PASS"
    # 模型未明确判定 → 保守视为 PASS(避免噪音),但在 PR 评论里指出
    return "PASS"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--pass", dest="pass_", required=True, choices=list(PROMPTS))
    p.add_argument("--mock", action="store_true",
                   help="不调真实 LLM,只读 prompt 与 diff,验证骨架")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    pass_name = args.pass_
    role = PASS_ROLE[pass_name]

    base_ref = os.getenv("BASE_REF", "main")
    pr = os.getenv("PR_NUMBER", "")
    repo = os.getenv("GITHUB_REPOSITORY", "")
    gh_token = os.getenv("GITHUB_TOKEN", "")

    prompt_path = Path(PROMPTS[pass_name])
    if not prompt_path.exists():
        print(f"::error::找不到 prompt 文件 {prompt_path}", file=sys.stderr)
        return 2

    base_prompt = prompt_path.read_text(encoding="utf-8")

    if pass_name == "dependency":
        diff = collect_dep_diff(base_ref)
        if not diff.strip():
            print("✓ 本 PR 未改依赖,跳过依赖评审。")
            return 0
        context_label = "DEPENDENCY DIFF"
    else:
        diff = collect_diff(base_ref)
        context_label = "FULL DIFF"

    # 让 diff 太大时不至于一次性烧爆 context;按 80k tokens ≈ 320k chars 粗截
    MAX_DIFF_CHARS = int(os.getenv("AI_REVIEW_MAX_DIFF_CHARS", "320000"))
    if len(diff) > MAX_DIFF_CHARS:
        diff = diff[:MAX_DIFF_CHARS] + f"\n\n[…diff 超长,截断到 {MAX_DIFF_CHARS} 字符,这是评审噪音信号——拆 PR…]"

    full_prompt = (
        base_prompt
        + f"\n\n---\n\n{context_label}\n```diff\n{diff}\n```\n"
        + "\n请按规则输出发现,末尾给出 `VERDICT: PASS` 或 `VERDICT: BLOCK`。"
    )

    if args.mock:
        print(f"=== MOCK pass={pass_name} role={role} prompt_chars={len(full_prompt)} ===")
        verdict = "PASS"
        review_body = f"[MOCK] {pass_name} pass — 假装通过,真跑时配 LLM_API_KEY 即可。"
    else:
        review_body = ModelAdapter.summarize(
            full_prompt, loop="ai-review", role=role,
        )
        verdict = parse_verdict(review_body)

    print(f"--- {pass_name} verdict: {verdict} ---")
    print(review_body[:2000])

    # 发评论(真跑时)。verdict 一行单独高亮放头部,方便人扫
    if pr and repo and gh_token and not args.mock:
        header = ("✅ **AI Review · " + pass_name + " · PASS**"
                  if verdict == "PASS"
                  else "🛑 **AI Review · " + pass_name + " · BLOCK**")
        post_pr_comment(repo, pr, gh_token, header + "\n\n" + review_body)

    return 1 if verdict == "BLOCK" else 0


if __name__ == "__main__":
    raise SystemExit(main())
