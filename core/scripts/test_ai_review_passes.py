"""验证四趟评审的注册表完整且自洽。"""
import importlib.util
import pathlib
import sys

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE))  # 让 ai_review 能 import _adapters

spec = importlib.util.spec_from_file_location("ai_review", HERE / "ai_review.py")
ai_review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ai_review)


def test_performance_pass_registered():
    assert "performance" in ai_review.PROMPTS
    assert ai_review.PROMPTS["performance"].endswith("review-performance.md")


def test_performance_role_mapping():
    assert ai_review.PASS_ROLE["performance"] == "verifier-performance"


def test_all_passes_have_role():
    # 每个 PROMPTS 趟都必须有对应 role,否则 main() 里 PASS_ROLE[pass_name] 会 KeyError
    assert set(ai_review.PROMPTS) == set(ai_review.PASS_ROLE)
