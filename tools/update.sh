#!/usr/bin/env bash
# =============================================================================
# update.sh — 把已安装的 harness 更新到当前版本
# -----------------------------------------------------------------------------
# 用法:
#   bash update.sh <target-repo-dir> [选项]
#
# 选项:
#   --codex      客户端目录用 .codex/ 而非 .claude/
#   --dry-run    只打印将做什么,不实际改动
#
# 与 install.sh 的区别:
#   install = 首次安装,safe_cp 保护所有已存在文件(不覆盖你的改动)
#   update  = 三件事 install 做不到的:
#     1) 强制覆盖 harness 自身文件(脚本/prompt/skill/agent/hook/ai-review 等)→ 拿新版
#     2) 保护你的定制文件(CLAUDE.md / ci.yml / settings.json / flags)→ 不覆盖,提示手动 merge
#     3) 删除上游已移除的文件(见 removed-files.txt)→ 自动清理(如已废弃的 deploy.yml)
#
# 哲学:harness 自身的东西随版本走;你填过的东西归你。
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SOURCE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

TARGET=""
USE_CODEX=0
DRY_RUN=0
while [ $# -gt 0 ]; do
  case "$1" in
    --codex)   USE_CODEX=1 ;;
    --dry-run) DRY_RUN=1 ;;
    -h|--help) sed -n '2,20p' "$0"; exit 0 ;;
    -*)        echo "未知选项 $1" >&2; exit 2 ;;
    *)         TARGET="$1" ;;
  esac
  shift
done

[ -n "$TARGET" ] || { echo "用法: bash update.sh <target-repo-dir> [--codex] [--dry-run]" >&2; exit 2; }
[ -d "$TARGET" ] || { echo "目标目录不存在: $TARGET" >&2; exit 2; }
TARGET="$(cd "$TARGET" && pwd)"

CC_DIR=".claude"; [ "$USE_CODEX" = "1" ] && CC_DIR=".codex"

say() { printf '\033[1;36m▶ %s\033[0m\n' "$*"; }
ok()  { printf '\033[1;32m✓ %s\033[0m\n' "$*"; }
skip(){ printf '\033[1;33m∅ %s\033[0m\n' "$*"; }
del() { printf '\033[1;31m− %s\033[0m\n' "$*"; }

[ "$DRY_RUN" = "1" ] && say "DRY-RUN(只预览,不改动)"

# 工作区干净提醒(强烈建议:先 commit/stash,再 update,便于用 git diff 审查)
if git -C "$TARGET" rev-parse --git-dir >/dev/null 2>&1; then
  if [ -n "$(git -C "$TARGET" status --porcelain 2>/dev/null)" ]; then
    skip "目标仓工作区不干净——建议先在目标仓 commit/stash,再 update(这样能用 git diff 审查更新内容)"
  fi
fi

# 强制覆盖一个文件(update 语义:harness 自身文件随版本走)
over() {
  local src="$1" dst="$2"
  [ -f "$src" ] || return 0
  case "$(basename "$src")" in __pycache__|.DS_Store|*.pyc) return 0 ;; esac
  if [ "$DRY_RUN" = "1" ]; then
    if [ -e "$dst" ] && cmp -s "$src" "$dst"; then return 0; fi   # 相同不提
    echo "  would overwrite: ${dst#$TARGET/}"; return 0
  fi
  mkdir -p "$(dirname "$dst")"
  if [ -e "$dst" ] && cmp -s "$src" "$dst"; then return 0; fi
  cp "$src" "$dst"; ok "覆盖 ${dst#$TARGET/}"
}

# ── 1. 强制覆盖 harness 自身文件 ──
say "覆盖 harness 自身文件(脚本/prompt/skill/agent/hook/harness-workflow)"
for f in "$SOURCE_DIR"/core/scripts/*;  do over "$f" "$TARGET/scripts/$(basename "$f")"; done
for f in "$SOURCE_DIR"/core/prompts/*.md; do over "$f" "$TARGET/prompts/$(basename "$f")"; done
# harness 拥有的 workflow(ci.yml 归你定制,见保护清单,不在此覆盖)
for wf in ai-review.yml daily-health.yml triage.yml; do
  over "$SOURCE_DIR/core/workflows/$wf" "$TARGET/.github/workflows/$wf"
done
# pre-push hook
if git -C "$TARGET" rev-parse --git-dir >/dev/null 2>&1; then
  over "$SOURCE_DIR/core/hooks/pre-push" "$TARGET/.git/hooks/pre-push"
  [ "$DRY_RUN" = "0" ] && [ -f "$TARGET/.git/hooks/pre-push" ] && chmod +x "$TARGET/.git/hooks/pre-push"
fi
# agents + skills
for f in "$SOURCE_DIR"/claude-code/agents/*.toml; do over "$f" "$TARGET/$CC_DIR/agents/$(basename "$f")"; done
for skill in "$SOURCE_DIR"/claude-code/skills/*/; do
  name="$(basename "$skill")"
  for f in "$skill"*; do over "$f" "$TARGET/$CC_DIR/skills/$name/$(basename "$f")"; done
done

# ── 2. 保护你的定制文件(不覆盖,提示手动 merge harness 新约束)──
say "保护你的定制文件(不覆盖)"
for p in "CLAUDE.md" ".github/workflows/ci.yml" "$CC_DIR/settings.json"; do
  [ -e "$TARGET/$p" ] && skip "保留 $p(如需并入 harness 新约束,请手动 merge \`claude-code/\`/\`core/\` 对应文件的变更)"
done
[ -d "$TARGET/flags" ] && skip "保留 flags/(你的特性开关)"

# ── 3. 删除上游已移除的文件 ──
if [ -f "$SCRIPT_DIR/removed-files.txt" ]; then
  say "清理上游已移除的文件"
  while IFS= read -r rel; do
    [ -z "$rel" ] && continue
    case "$rel" in \#*) continue ;; esac
    if [ -e "$TARGET/$rel" ]; then
      if [ "$DRY_RUN" = "1" ]; then echo "  would delete: $rel"; else rm -f "$TARGET/$rel"; del "删除 $rel(上游已移除)"; fi
    fi
  done < "$SCRIPT_DIR/removed-files.txt"
fi

cat <<EOF

============================================================
✅ 更新完成${DRY_RUN:+(DRY-RUN 预览,未实际改动)}

下一步:
  1. 在目标仓 \`git diff\` 审查这次更新带来的变化
  2. 手动检查被保护的文件是否要并入 harness 新约束:
     - CLAUDE.md(如分支纪律铁律、docs-repo 多项目骨架)
     - .github/workflows/ci.yml(如门禁逻辑更新——你改过语言 job,需手动 merge)
  3. 确认无误后在目标仓提交
============================================================
EOF
