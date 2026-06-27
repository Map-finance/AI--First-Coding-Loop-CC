#!/usr/bin/env bash
# =============================================================================
# ensure_skills.sh — 幂等确保必备 skill 就位（团队规范 skill + superpowers）
# 用法: bash ensure_skills.sh <target-repo-dir>
# 环境: DRY_RUN=1 只检测与报告，不真正安装
# 设计: 已存在则跳过（"有了就不用"）；缺失才安装。
# =============================================================================
set -euo pipefail

TARGET="${1:?用法: bash ensure_skills.sh <target-repo-dir>}"
TARGET="$(cd "$TARGET" && pwd)"
DRY_RUN="${DRY_RUN:-0}"

say() { printf '\033[1;36m▶ %s\033[0m\n' "$*"; }
ok()  { printf '\033[1;32m✓ %s\033[0m\n' "$*"; }

# 团队规范 skill 随代码仓 .claude/skills/ 下发，这里只校验存在性
TEAM_SKILLS=(secure-coding clean-code testing-standards sql-optimization performance-review financial-numerics)

say "校验团队规范 skill"
missing_team=0
for s in "${TEAM_SKILLS[@]}"; do
  if [ -d "$TARGET/.claude/skills/$s" ] || [ -d "$TARGET/.codex/skills/$s" ]; then
    ok "$s: 已存在"
  else
    printf '\033[1;33m∅ %s: 缺失（应随仓下发，请检查 install.sh）\033[0m\n' "$s"
    missing_team=1
  fi
done

# superpowers：用户级或项目级任一存在即视为已装
say "检查 superpowers"
if [ -d "$HOME/.claude/skills/superpowers" ] || [ -d "$TARGET/.claude/skills/superpowers" ] \
   || [ -d "$HOME/.claude/plugins/superpowers" ]; then
  ok "superpowers: 已存在，跳过"
else
  echo "superpowers: 缺失"
  if [ "$DRY_RUN" = "1" ]; then
    echo "  (DRY_RUN) 将安装 superpowers"
  else
    echo "  请用官方方式安装（plugin marketplace 或 git clone 到 ~/.claude/skills/superpowers）。"
    echo "  落地时用 claude-code-guide 核实当前官方命令；本脚本不写死可能过期的命令。"
  fi
fi

[ "$missing_team" = "0" ] && ok "全部团队 skill 就位" || true
