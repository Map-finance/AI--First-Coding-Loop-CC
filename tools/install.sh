#!/usr/bin/env bash
# =============================================================================
# install.sh — 把 AI-First Coding Loop 装到目标仓库
# -----------------------------------------------------------------------------
# 用法:
#   bash install.sh <target-repo-dir> [选项]
#
# 选项:
#   --codex            把 skills/agents 装到 .codex/ 而非 .claude/
#   --no-skills        只装 core/,不装 claude-code/(适合不用 CC/Codex 的项目)
#   --strategy <1|2|3> 合并策略(默认 2):
#                        1 = 直接平铺(适合空仓)
#                        2 = 主体直接装,保留用户已有 README/Makefile/Dockerfile(默认)
#                        3 = 装到子目录 .harness/(适合有冲突的仓)
#
# 设计:幂等。再跑一次只会更新,不破坏用户改动(改了的文件被检测并跳过 + 提示)。
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SOURCE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

TARGET=""
USE_CODEX=0
NO_SKILLS=0
STRATEGY=2
while [ $# -gt 0 ]; do
  case "$1" in
    --codex)     USE_CODEX=1 ;;
    --no-skills) NO_SKILLS=1 ;;
    --strategy)  STRATEGY="$2"; shift ;;
    -h|--help)   sed -n '2,20p' "$0"; exit 0 ;;
    -*)          echo "未知选项 $1" >&2; exit 2 ;;
    *)           TARGET="$1" ;;
  esac
  shift
done

[ -n "$TARGET" ] || { echo "用法:bash install.sh <target-repo-dir> [选项]" >&2; exit 2; }
[ -d "$TARGET" ] || { echo "目标目录不存在:$TARGET" >&2; exit 2; }
TARGET="$(cd "$TARGET" && pwd)"

say() { printf '\033[1;36m▶ %s\033[0m\n' "$*"; }
ok()  { printf '\033[1;32m✓ %s\033[0m\n' "$*"; }
skip(){ printf '\033[1;33m∅ %s\033[0m\n' "$*"; }

# 决定 base prefix
PREFIX=""
if [ "$STRATEGY" = "3" ]; then PREFIX=".harness/"; fi

CC_DIR=".claude"
[ "$USE_CODEX" = "1" ] && CC_DIR=".codex"

# 安全拷贝:目标文件已存在且内容不同 → 跳过 + 提示
# 对非常规文件(目录、__pycache__、.DS_Store 等)静默跳过——让 for-loop 不会被它们绊倒
safe_cp() {
  local src="$1" dst="$2"
  [ -f "$src" ] || return 0
  case "$(basename "$src")" in
    __pycache__|.DS_Store|*.pyc|*.tsbuildinfo) return 0 ;;
  esac
  if [ -e "$dst" ]; then
    if cmp -s "$src" "$dst"; then
      return
    fi
    skip "已存在且不同,跳过(请人工合并):$dst"
    return
  fi
  mkdir -p "$(dirname "$dst")"
  cp "$src" "$dst"
  ok "+ $dst"
}

say "装到 $TARGET (策略 $STRATEGY,客户端目录 $CC_DIR)"

# === core ===
say "core/ → 目标仓"
# scripts/
for f in "$SOURCE_DIR"/core/scripts/*; do
  safe_cp "$f" "$TARGET/${PREFIX}scripts/$(basename "$f")"
done
# .github/workflows/
for f in "$SOURCE_DIR"/core/workflows/*.yml; do
  safe_cp "$f" "$TARGET/${PREFIX}.github/workflows/$(basename "$f")"
done
# prompts/
for f in "$SOURCE_DIR"/core/prompts/*.md; do
  safe_cp "$f" "$TARGET/${PREFIX}prompts/$(basename "$f")"
done
# flags/
for f in "$SOURCE_DIR"/core/flags/*; do
  safe_cp "$f" "$TARGET/${PREFIX}flags/$(basename "$f")"
done
# state/
safe_cp "$SOURCE_DIR/core/state/README.md"       "$TARGET/${PREFIX}state/README.md"
safe_cp "$SOURCE_DIR/core/state/known-flakes.txt" "$TARGET/${PREFIX}state/known-flakes.txt"
mkdir -p "$TARGET/${PREFIX}state/tasks" && touch "$TARGET/${PREFIX}state/tasks/.gitkeep"
ok "+ state/tasks/.gitkeep"

# === claude-code(skills + agents)===
if [ "$NO_SKILLS" = "0" ]; then
  say "claude-code/ → $TARGET/$CC_DIR/"
  for skill in "$SOURCE_DIR"/claude-code/skills/*/; do
    name="$(basename "$skill")"
    [ "$name" = "README.md" ] && continue
    for f in "$skill"*; do
      safe_cp "$f" "$TARGET/$CC_DIR/skills/$name/$(basename "$f")"
    done
  done
  for f in "$SOURCE_DIR"/claude-code/agents/*.toml; do
    safe_cp "$f" "$TARGET/$CC_DIR/agents/$(basename "$f")"
  done
  # CLAUDE.md 只在目标仓没有时装(它太关键,不允许自动覆盖)
  if [ ! -f "$TARGET/CLAUDE.md" ]; then
    cp "$SOURCE_DIR/claude-code/CLAUDE.md.template" "$TARGET/CLAUDE.md"
    ok "+ CLAUDE.md(从模板,你需要替换占位)"
  else
    skip "CLAUDE.md 已存在,跳过(请手动 merge claude-code/CLAUDE.md.template 的新增内容)"
  fi
  # .claude/settings.json:仅在目标仓没有时装(含 skill-reminder hook)
  if [ ! -f "$TARGET/$CC_DIR/settings.json" ]; then
    safe_cp "$SOURCE_DIR/claude-code/settings.json.template" "$TARGET/$CC_DIR/settings.json"
  else
    skip "$CC_DIR/settings.json 已存在,跳过(请手动 merge hook)"
  fi
fi

# === .gitignore 追加(若有需要)===
GI="$TARGET/.gitignore"
NEEDED=(
  "state/tasks/*.tmp.*"
  "state/_local/"
  "__pycache__/"
  ".worktrees/"
)
touch "$GI"
for line in "${NEEDED[@]}"; do
  if ! grep -qxF "$line" "$GI" 2>/dev/null; then
    echo "$line" >> "$GI"
    ok "+ .gitignore: $line"
  fi
done

# === 确保必备 skill 就位 ===
if [ "$NO_SKILLS" = "0" ]; then
  bash "$SCRIPT_DIR/ensure_skills.sh" "$TARGET" || skip "ensure_skills 有告警,请查看上方输出"
fi

cat <<EOF

============================================================
✅ 安装完成

下一步:
  1. 编辑 CLAUDE.md 把 [占位] 换成项目真实信息
  2. 编辑 ${PREFIX}.github/workflows/ci.yml 注释掉用不到的语言 job
  3. 在 GitHub Repo Settings 配 LLM_PROVIDER + LLM_API_KEY(详见 docs/多模型适配.md)
  4. 跑 bash tools/verify.sh 做 5 项 sanity
  5. 推到分支 + 开 draft PR,自己 review 后再合 main
============================================================
EOF
