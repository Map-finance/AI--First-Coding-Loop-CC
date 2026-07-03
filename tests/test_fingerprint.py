"""ErrorEvent.fingerprint 的聚类语义 —— triage 去重/回归识别全靠它,锁死防回归。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "core" / "scripts"))

from _adapters import ErrorEvent  # noqa: E402


def _fp(service: str, message: str) -> str:
    return ErrorEvent(service=service, message=message).fingerprint()


def test_same_error_different_ids_cluster_together():
    # 只有事件 id 不同的同类错误必须落进同一簇
    a = _fp("billing", "Stripe webhook signature verification failed for event evt_0a1b2c3d")
    b = _fp("billing", "Stripe webhook signature verification failed for event evt_ffee9988")
    assert a == b


def test_numbers_and_durations_normalized():
    a = _fp("ml", "Inference timeout after 30000ms on model rerank-v3")
    b = _fp("ml", "Inference timeout after 45000ms on model rerank-v3")
    assert a == b


def test_different_message_different_cluster():
    a = _fp("api", "NullPointerException reading user.profile.avatar")
    b = _fp("api", "Connection refused to redis")
    assert a != b


def test_service_isolates_clusters():
    # 同一条消息、不同 service 不能混簇
    a = _fp("api", "Connection refused")
    b = _fp("worker", "Connection refused")
    assert a != b


def test_whitespace_and_case_insensitive():
    a = _fp("api", "Connection   Refused")
    b = _fp("api", "connection refused")
    assert a == b


def test_fingerprint_is_stable_12_hex():
    fp = _fp("api", "boom")
    assert len(fp) == 12
    int(fp, 16)  # 不抛 = 合法 hex
