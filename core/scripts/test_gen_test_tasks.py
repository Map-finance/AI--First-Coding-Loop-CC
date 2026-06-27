import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import gen_test_tasks as g


def test_make_qa_title_truncates_and_tags():
    title = g.make_qa_title("abc1234", "feat: 新增支付回调幂等校验，避免重复入账问题非常长" * 5)
    assert title.startswith("[qa] ")
    assert "[merge:abc1234]" in title
    assert len(title) <= 120


def test_build_qa_task_body_has_all_sections():
    body = g.build_qa_task_body(
        merge_sha="abc1234",
        generated="## 测试用例\n- TC1: 正常入账\n## 验收标准\n- 幂等",
    )
    # AI 生成段落原样嵌入
    assert "TC1: 正常入账" in body
    # 必带可去重的 merge 标记（仿 triage 的 [fp:..]）
    assert "[merge:abc1234]" in body
    # 必带 QA 报告模板段，提示 QA 在评论里贴报告
    assert "测试报告（QA 填写）" in body
    assert "QA-REPORT" in body


def test_append_qa_history_writes_jsonl(tmp_path, monkeypatch):
    monkeypatch.setattr(g, "STATE", tmp_path)
    g.append_qa_history(merge_sha="abc1234", action="created",
                        issue="42", extra={"repo": "org/svc"})
    line = (tmp_path / "qa-history.jsonl").read_text(encoding="utf-8").strip()
    rec = json.loads(line)
    assert rec["merge_sha"] == "abc1234"
    assert rec["action"] == "created"
    assert rec["issue"] == "42"
    assert rec["repo"] == "org/svc"
    assert "ts" in rec


def test_collect_merge_diff_uses_git(monkeypatch):
    calls = []

    def fake_sh(*args, **kw):
        calls.append(args)
        return "diff --git a/x b/x\n+changed\n"

    monkeypatch.setattr(g, "sh", fake_sh)
    diff = g.collect_merge_diff("abc1234")
    assert "changed" in diff
    # 取 merge commit 自身的改动（first-parent）
    assert any("abc1234" in " ".join(a) for a in calls)


def test_collect_merge_diff_truncates_when_huge(monkeypatch):
    monkeypatch.setattr(g, "sh", lambda *a, **k: "x" * 500000)
    monkeypatch.setenv("QA_GEN_MAX_DIFF_CHARS", "1000")
    diff = g.collect_merge_diff("abc1234")
    assert len(diff) < 2000
    assert "截断" in diff


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
