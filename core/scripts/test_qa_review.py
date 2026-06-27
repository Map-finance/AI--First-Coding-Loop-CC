import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import qa_review as q


def test_parse_verdict_block():
    assert q.parse_verdict("一些发现\nVERDICT: BLOCK\n") == "BLOCK"


def test_parse_verdict_pass():
    assert q.parse_verdict("看起来覆盖完整\nVERDICT: PASS") == "PASS"


def test_parse_verdict_defaults_block_when_missing():
    # 报告审核场景下，模型没明确判定时保守视为 BLOCK（与 ai_review 的保守 PASS 相反，
    # 因为这里"放过未审核的报告"风险更高）
    assert q.parse_verdict("没有给出判定") == "BLOCK"


def test_is_qa_report_detects_sentinel():
    assert q.is_qa_report("QA-REPORT\n### 覆盖的验收点\n- [x] ok") is True
    assert q.is_qa_report("普通讨论评论，不是报告") is False


def test_extract_merge_sha_from_title():
    assert q.extract_merge_sha("[qa] feat: x [merge:abc1234]") == "abc1234"
    assert q.extract_merge_sha("没有标记的标题") == ""


def test_build_block_comment_mentions_reason():
    body = q.build_block_comment("缺少 TC3 的证据，验收点 2 未覆盖")
    assert "BLOCK" in body
    assert "TC3" in body
    assert "重测" in body


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
