"""oauth 路的 claude-only 模型守护(v2.11 修的洞)—— 任何来源的 gpt-* 残留都必须被忽略。

不真调网络:直接测 summarize 在 oauth 分支里最终选中的模型——通过 fail-safe 文案
里回显的 model= 值断言(本机无 anthropic SDK / 假 token 时调用必失败,文案稳定)。
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "core" / "scripts"))

import _adapters  # noqa: E402


def _summarize_with_env(env: dict) -> str:
    saved = {}
    keys = ["CLAUDE_CODE_OAUTH_TOKEN", "ANTHROPIC_AUTH_TOKEN", "LLM_API_KEY",
            "ANTHROPIC_API_KEY", "LLM_MODEL", "CC_MODEL", "LLM_MODEL_VERIFIER_QUALITY"]
    for k in keys:
        saved[k] = os.environ.pop(k, None)
    os.environ.update(env)
    try:
        return _adapters.ModelAdapter.summarize("hi", loop="test", role="verifier-quality")
    finally:
        for k in keys:
            os.environ.pop(k, None)
            if saved[k] is not None:
                os.environ[k] = saved[k]


def test_role_env_gpt_leftover_ignored():
    out = _summarize_with_env({
        "CLAUDE_CODE_OAUTH_TOKEN": "sk-ant-oat01-FAKE",
        "LLM_MODEL_VERIFIER_QUALITY": "gpt-5.5",
        "LLM_MODEL": "gpt-5.5",
    })
    assert "model=claude-sonnet-4-6" in out, out


def test_claude_role_env_respected():
    out = _summarize_with_env({
        "CLAUDE_CODE_OAUTH_TOKEN": "sk-ant-oat01-FAKE",
        "LLM_MODEL_VERIFIER_QUALITY": "claude-opus-4-8",
        "LLM_MODEL": "gpt-5.5",
    })
    assert "model=claude-opus-4-8" in out, out


def test_no_credentials_returns_stub():
    out = _summarize_with_env({})
    assert out.startswith("[模型未配置")
