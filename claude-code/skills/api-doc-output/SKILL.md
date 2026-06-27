---
name: api-doc-output
description: 改动 HTTP/RPC 接口时强制同步更新接口文档——在 docs/api（经 submodule 指向 docs-repo）记录路径、方法、入参/出参、错误码、鉴权要求。CI 会检查接口改了文档没改则拦。
when_to_use: 新增/修改/删除任何对外接口、请求或响应结构、错误码时。
when_NOT_to_use: 仅内部函数重构、不影响对外契约。
---

# Skill: 接口文档产出

改接口必须同步更新 `docs/<backend|frontend>/<svc>/api.md`，否则 CI 拦截。

## 每个接口需记录
1. 路径 + 方法 + 简述
2. 鉴权要求（是否需登录、需要的权限）
3. 入参（字段、类型、必填、约束）
4. 出参（成功结构）
5. 错误码与含义
6. 跨端共享的类型放 docs-repo 的 `contracts/`，前后端引用同一份

## 反模式
- ❌ 改了响应字段不更新文档（前端按旧契约对接 → 线上故障）
- ❌ 接口文档与 contracts/ 类型不一致
