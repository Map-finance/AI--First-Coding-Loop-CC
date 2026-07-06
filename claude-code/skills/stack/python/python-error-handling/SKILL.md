---
name: python-error-handling
pack: stack:python
description: Python错误处理规范——捕获具体异常不裸except、raise from保留异常链、自定义业务异常层次、禁静默pass吞异常、上下文管理器管资源。
when_to_use: 新增或修改Python异常处理逻辑，或涉及资源管理/业务错误建模时。
when_NOT_to_use: 非Python代码，或与错误处理无关的改动。
---

# Skill: Python 错误处理

## 强制规则

1. **捕获具体异常** — `except ValueError:` 而非裸 `except:` 或 `except Exception:`（裸 except 会吞 `KeyboardInterrupt`/`SystemExit`）
2. **异常链 `raise from`** — 包装重抛用 `raise XxxError(...) from e`，保留原因链，堆栈可溯源
3. **禁静默吞异常** — `except: pass` 一律禁止；捕获后必须处理之一：重抛、包装、记录并降级
4. **自定义业务异常继承统一基类** — 建包级异常层次，便于上层分类捕获
5. **资源用上下文管理器** — `with open(...)` / `with lock:`，禁手写 try/finally close

## 自定义异常层次

```python
class AppError(Exception):
    """所有业务异常的基类，便于统一捕获。"""

class NotFoundError(AppError):
    def __init__(self, resource: str, key: str) -> None:
        super().__init__(f"{resource} not found: {key}")
        self.resource = resource
        self.key = key

class InsufficientBalanceError(AppError):
    ...
```

## 异常链 raise from

```python
try:
    row = db.query_one(SQL_GET_ORDER, order_id)
except DatabaseError as e:
    # ✅ from e 保留底层原因，traceback 显示 "The above exception was the direct cause"
    raise NotFoundError("order", order_id) from e

# ❌ 丢失原始异常，排障时看不到根因
except DatabaseError:
    raise NotFoundError("order", order_id)
```

## 上下文管理器管资源

```python
# ✅ 异常也保证关闭
with db.transaction() as tx:
    tx.execute(...)
    tx.execute(...)          # 出错自动回滚 + 关闭

# ❌ 手写 finally，易漏、易吞关闭异常
```

## 禁静默吞异常

```python
# ❌ 问题人间蒸发
try:
    charge(order)
except Exception:
    pass

# ✅ 至少记录，且不吞 KeyboardInterrupt
try:
    charge(order)
except PaymentError:
    logger.exception("charge failed", order_id=order.id)
    raise
```

## 反模式
- ❌ `except:` / `except Exception:` 宽泛捕获 — 吞掉不该吞的（含中断信号）
- ❌ `except X: pass` — 静默吞异常，故障不可见
- ❌ `raise NewError(str(e))` — 丢异常链，应 `raise NewError(...) from e`
- ❌ `except Exception as e: logger.error(e); return None` — 吞错误后返回 None，污染上层
- ❌ 手写 `f = open(...); ... f.close()` — 异常路径漏关，用 `with`
