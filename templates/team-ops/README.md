# team-ops —— 任务编排管理仓模板

承载团队任务编排，但**不承载具体开发/测试/review issue**（那些落各代码仓）。

## 目录
| 路径 | 用途 |
|---|---|
| `daily/` | 每日任务计划文档归档（task_splitter 产出，按日期命名 `<date>.md`） |
| `ownership.md` | 三层模型第 ①②层：项目级 / 子服务级责任人归属（相对静态） |
| `issue-templates/` | 5 类 Issue Form（YAML）。由 AIFCL install.sh 分发到**各代码仓** `.github/ISSUE_TEMPLATE/` |
| `projects/` | 组织级 GitHub Projects 看板配置 + 跨仓自动关单说明 |

## 每日编排流程（人工确认门贯穿）
1. 架构师写当日任务源（结构化 markdown）。
2. `task_splitter.py` 拆解 → 产出 `daily/<date>.md` + 待建 issue 草稿 JSON（**只产草稿**）。
3. 人 review 草稿（核对 repo/责任人/验收/字段齐全）。
4. 确认后 `create_issues_from_draft.py --confirm` → 在**对应代码仓**建 issue。
5. issue 自动进组织级 Projects 看板；PR 合并经 `Closes #N` 自动关单（同仓）。

## 为什么 issue 落代码仓而非本管理仓
GitHub `Closes #N` 只能关闭**同仓** issue。要让"PR 合并 / 测试通过自动关单"成立，
开发/bug/qa/review issue 必须建在对应代码仓。本管理仓只放计划文档、归属、模板、看板配置。
