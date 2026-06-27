# 责任人归属（三层模型 第 ①②层）

> 相对静态：项目级一次性、子服务级按里程碑刷新。动态的"每日任务"不在此处，由 task_splitter 拆解。
> 本表与各代码仓的 `CODEOWNERS` 保持一致（CODEOWNERS 管自动 review 指派，本表管人读）。

## ① 项目级分工
| 领域 | 负责人 | 代码仓 |
|---|---|---|
| 后端 | <填> | org/backend |
| 前端 | <填> | org/frontend |
| 共享文档/契约 | <填> | org/docs-repo |

## ② 子服务级归属（具体到人）
| 子服务 | 代码仓 | 主负责人 | 备份 | 相关文档 |
|---|---|---|---|---|
| svc-order | org/backend | <填> | <填> | docs/backend/svc-order/ |
| svc-account | org/backend | <填> | <填> | docs/backend/svc-account/ |
| web-order | org/frontend | <填> | <填> | docs/frontend/web-order/ |

## 维护约定
- 新增子服务：加一行 + 在对应代码仓 CODEOWNERS 加规则 + 在 docs-repo 建 `svc-<name>/` 目录。
- task_splitter 指派 assignee 时以本表为准；拿不准留空交人定。
