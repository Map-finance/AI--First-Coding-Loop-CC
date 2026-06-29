# assets-for-deepdog — 供 deepdog 复用的知识资产

本目录下的 prompt 是从 AI-First Coding Loop harness 中抽取出来的**知识资产**。

## 背景

harness 原本内置了「任务拆解」「测试闭环编排」两块执行代码。由于外部管理端
**deepdog** 已接管这两类职责(issue / agent_task_queue 负责任务拆解与分发,
verification gate 负责测试闭环编排),harness 中对应的执行代码已被移除,避免与
deepdog 重叠维护。

但这些 prompt 本身记录了 deepdog 目前**尚未实现、将来要复用**的能力,因此保留
在此存档,供 deepdog 后续实现时直接复用。

## 文件清单

| 文件 | 能力 | deepdog 复用场景 |
|------|------|------------------|
| `daily-task-split.md` | 任务拆解 prompt | 实现「AI 任务拆解」 |
| `gen-test-tasks.md`   | 读 diff 生成测试用例 / 验收标准 | 实现「自动生成验收标准」 |
| `review-qa-report.md` | AI 审核测试报告 PASS / BLOCK | 实现「AI 预审测试报告」 |

## 说明

这些文件不参与 harness 的安装与运行(install.sh 不再分发),仅作为文档资产保留。
