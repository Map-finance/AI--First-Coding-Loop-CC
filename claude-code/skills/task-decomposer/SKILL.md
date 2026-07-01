---
name: task-decomposer
description: 主 session 收到需求后第一件事——判断是否可并行分解。输出 DAG(JSON),节点=子任务,边=强依赖。判定保守:有疑虑就串行(并行错的代价远大于串行慢)。
when_to_use: 用户提出任何"加 X / 改 Y / 实现 Z"的需求时,architect-task-writer 之前先跑这一步。
when_NOT_to_use: 已经是单文件 typo 修复 / 单测试调整 / 单文档改这种明显原子操作;复用现有 skill 的标准化任务(feature-flag-setup 等)。
---

# Skill: Task Decomposer

> 主 session 是"指挥",不是"实施"。**收到任何需求,第一件事是决定"这是 1 个任务还是 N 个可并行任务"**。
> 这一步做对,后面的速度差 3~5 倍;做错,merger 就成了瓶颈。
> 默认规则:**有疑虑就串行**(parallelize-by-default 会带翻全场)。

---

## 判定矩阵(贴墙)

| 信号 | 可并行 ✅ | 必须串行 ❌ |
|---|---|---|
| **触及不同的服务/包** | ✅ | — |
| **触及不同的目录(无重叠文件)** | ✅ | — |
| **每个子任务有独立的测试 / 验证标准** | ✅ | — |
| **共享 schema / DB 迁移** | — | ❌(迁移要先做,其他依赖) |
| **共享契约修改**(packages/contracts 改了类型) | — | ❌(其他要等契约稳定) |
| **触及同一个文件** | — | ❌(merge conflict 几乎注定) |
| **后端契约新增 + 前端消费** | — | ❌(后端先 deploy,前端才能 build) |
| **跨服务的全链路重构** | — | ❌(改顺序敏感) |

**判定决策树**:
```
有任何"必须串行"信号?
  ├── 是 → 整体串行(或拆成"串行多轮,每轮内部可并行"——下一节)
  └── 否 → 看是否有 ≥2 个独立子任务?
            ├── 是 → 并行 DAG
            └── 否 → 单任务,不必走 orchestrator
```

---

## 分多轮的判定

如果需求**部分**可并行、**部分**必须串行,**分轮**:

```
Round 1:迁移 schema(单任务)
Round 2:实现 3 个 OAuth provider(并行 3 个)
Round 3:加前端 Login 选择器(单任务,依赖 Round 2)
```

每一轮内部尽量塞满可并行的子任务。**轮之间是串行的**。

---

## 输出格式(给 parallel-orchestrator 吃)

写到 `state/orchestration/<task-id>/decomposition.json`:

```json
{
  "task_id": "add-oauth-providers",
  "requirement": "加 OAuth 三家:Google / GitHub / Microsoft",
  "rounds": [
    {
      "round": 1,
      "parallel": true,
      "subtasks": [
        {
          "id": "oauth-google",
          "scope": "services/auth/providers/google.ts + 测试",
          "no_touch": ["services/auth/index.ts", "packages/contracts/auth.ts"],
          "verifies": "make test-unit services/auth/providers/google"
        },
        {
          "id": "oauth-github",
          "scope": "services/auth/providers/github.ts + 测试",
          "no_touch": ["services/auth/index.ts", "packages/contracts/auth.ts"],
          "verifies": "make test-unit services/auth/providers/github"
        },
        {
          "id": "oauth-microsoft",
          "scope": "services/auth/providers/microsoft.ts + 测试",
          "no_touch": ["services/auth/index.ts", "packages/contracts/auth.ts"],
          "verifies": "make test-unit services/auth/providers/microsoft"
        }
      ]
    },
    {
      "round": 2,
      "parallel": false,
      "subtasks": [
        {
          "id": "wire-providers-in-index",
          "scope": "services/auth/index.ts 注册 3 个 provider",
          "depends_on_round": 1
        }
      ]
    }
  ],
  "rationale": "3 个 provider 文件独立,可并行写;但最后要在 index 里统一注册,这步必须等 3 个文件都存在后串行做。"
}
```

## 关键字段含义

- **`scope`**:子任务被允许触及的范围(文件/目录)。**实施 agent 越界 = block**。
- **`no_touch`**:**显式禁止**修改的文件(防止并行子任务同时改同一个文件)。
- **`verifies`**:子任务完成的客观检查命令(merger 据此判断 done)。
- **`depends_on_round`**:本子任务依赖哪一轮完成。

## 给主 session 的固定指令

> 1. 写完 decomposition.json 后,**给用户看 decomposition 表格,让用户确认**。
>    用户认为某子任务该再拆 / 不该并行 → 改 json 重来。
> 2. 用户 OK 后,把 `state/orchestration/<task-id>/decomposition.json` 路径
>    传给 parallel-orchestrator skill 继续。

## 反模式(BLOCK 自己)

- ❌ 默认并行 —— 应该默认串行,只有清晰边界才并行
- ❌ 把"提示词差不多就能拆"当并行候选 —— 必须是**文件级别不重叠**
- ❌ 不写 `no_touch` —— sub-agent 不知道边界,会越界改共享文件
- ❌ 不写 `verifies` —— merger 无法机械判断 done,变成"靠 LLM 猜"
- ❌ 把跨服务契约改动塞进并行 —— 契约改 = 串行先做,这条没商量
