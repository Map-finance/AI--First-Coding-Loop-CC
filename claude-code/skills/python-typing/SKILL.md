---
name: python-typing
pack: stack:python
description: Python类型标注规范——mypy严格模式、避免Any、用Protocol做结构化子类型、泛型TypeVar、Optional显式处理不隐式None。
when_to_use: 新增或修改Python函数签名、公共接口、数据模型时。
when_NOT_to_use: 非Python项目，或一次性脚本无需长期维护。
---

# Skill: Python 类型标注 (mypy 严格)

## 强制规则

1. **公共函数全标注** — 所有参数与返回值都有类型；开 mypy `--strict`（含 `disallow_untyped_defs`、`no_implicit_optional`）
2. **避免 `Any`** — `Any` 关闭类型检查形同裸奔；不知道类型用 `object` 或泛型，边界处必须显式 `cast` 并注释理由
3. **接口用 `Protocol`** — 依赖抽象用结构化子类型（鸭子类型 + 静态检查），不强制继承 ABC
4. **`Optional` 显式处理** — `X | None` 必须在使用前判空/收窄，禁直接当非空用
5. **禁隐式 Optional** — 参数默认 `None` 时类型必须写 `X | None`，不写裸 `X`

## Protocol 结构化子类型

```python
from typing import Protocol

class OrderRepository(Protocol):
    def get(self, order_id: str) -> "Order | None": ...
    def save(self, order: "Order") -> None: ...

# 任何满足签名的类都可传入，无需显式继承
class OrderService:
    def __init__(self, repo: OrderRepository) -> None:
        self._repo = repo
```

## 泛型

```python
from typing import TypeVar, Generic

T = TypeVar("T")

class Result(Generic[T]):
    def __init__(self, value: T | None, error: str | None = None) -> None:
        self._value = value
        self._error = error

    def unwrap(self) -> T:
        if self._value is None:
            raise ValueError(self._error or "empty result")
        return self._value
```

## Optional 收窄

```python
def total(order: Order | None) -> Decimal:
    if order is None:                 # ✅ 显式收窄，之后 order 是 Order
        return Decimal("0")
    return order.amount

# ❌ 未判空直接用，mypy 报错、运行时 AttributeError
def total_bad(order: Order | None) -> Decimal:
    return order.amount
```

## 反模式
- ❌ `def handle(data): ...` — 无标注，strict 下直接报错
- ❌ `def parse(x: Any) -> Any` — 关闭检查，形同无类型
- ❌ `def f(name: str = None)` — 隐式 Optional，应 `name: str | None = None`
- ❌ `# type: ignore` 无理由裸用 — 掩盖真问题，必须写明 `# type: ignore[code]  # 原因`
- ❌ `cast(Order, obj)` 随手强转绕过检查 — 只在类型系统确实无法表达时用并注释
