"""parse_verdict 的判定语义 —— 这是门禁的核心开关,锁死行为防回归。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "core" / "scripts"))

from ai_review import parse_verdict  # noqa: E402


def test_block_at_end():
    assert parse_verdict("发现 SQL 注入。\nVERDICT: BLOCK") == "BLOCK"


def test_pass_at_end():
    assert parse_verdict("没问题。\nVERDICT: PASS") == "PASS"


def test_verdict_in_middle_is_found():
    # 容错:模型有时把判定写在中间
    assert parse_verdict("VERDICT: BLOCK\n后面还有解释文字") == "BLOCK"


def test_last_verdict_wins():
    # 从末尾倒着找 —— 最后一个 VERDICT 生效
    text = "VERDICT: PASS\n……重新审视后:\nVERDICT: BLOCK"
    assert parse_verdict(text) == "BLOCK"


def test_case_insensitive_and_padded():
    assert parse_verdict("  verdict: pass  ") == "PASS"


def test_no_verdict_returns_none():
    # v2.11:找不到明确判定返回 None(由调用方显式处理,不许静默当 PASS)
    assert parse_verdict("模型絮絮叨叨但没给判定") is None


def test_empty_returns_none():
    assert parse_verdict("") is None


def test_degraded_stub_text_returns_none():
    # 无凭证 stub 文案不含 VERDICT → None → main 里标记 degraded
    assert parse_verdict("[模型未配置:跳过 AI 摘要,以下为机器统计]") is None
