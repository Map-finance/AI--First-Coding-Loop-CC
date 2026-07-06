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
#   --profile <single|monorepo> 项目形态(默认 monorepo,向后兼容):
#                        monorepo = 单仓多微服务(apps/ + services/ + docs/services/…)
#                        single   = 单体单服务(代码在根 + 扁平 docs/,命名无 service scope)
#                        决定装哪个 CLAUDE.md 变体与哪个 ci.yml。
#   --stacks <csv>     按技术栈选装 skill 包(go,node,java,rust,python,frontend);
#                        缺省时自动探测(go.mod/package.json/Cargo.toml…)。universal 恒装。
#   --domains <csv>    按业务域选装(finance,web3-solidity)。finance 不自动探测,需显式。
#   --frontend-platforms <csv>  前端端选择(web,mobile,desktop);缺省探测,探不到则全装。
#   --list-packs       只列出每个 skill 的 pack 与选中的包集合,不安装。
#   --gate-branches <csv>  CI/AI-review 触发分支(拦 dev 裸奔);缺省探测该仓存在的
#                        默认分支 ∪ {dev,develop,test,staging}。例:--gate-branches main,dev,test
#   --skip-graphify    跳过 graphify 安装尝试(graphify 为可选,不影响其他安装步骤)
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
SKIP_GRAPHIFY=0
PROFILE=monorepo
STACKS=""
DOMAINS=""
FE_PLATFORMS=""
LIST_PACKS=0
GATE_BRANCHES=""
while [ $# -gt 0 ]; do
  case "$1" in
    --codex)         USE_CODEX=1 ;;
    --no-skills)     NO_SKILLS=1 ;;
    --skip-graphify) SKIP_GRAPHIFY=1 ;;
    --strategy)      STRATEGY="$2"; shift ;;
    --profile)       PROFILE="$2"; shift ;;
    --stacks)        STACKS="$2"; shift ;;
    --domains)       DOMAINS="$2"; shift ;;
    --frontend-platforms) FE_PLATFORMS="$2"; shift ;;
    --list-packs)    LIST_PACKS=1 ;;
    --gate-branches) GATE_BRANCHES="$2"; shift ;;
    -h|--help)   sed -n '2,31p' "$0"; exit 0 ;;
    -*)          echo "未知选项 $1" >&2; exit 2 ;;
    *)           TARGET="$1" ;;
  esac
  shift
done

case "$PROFILE" in
  single|monorepo) ;;
  *) echo "未知 --profile '$PROFILE'(合法值:single | monorepo)" >&2; exit 2 ;;
esac

[ -n "$TARGET" ] || { echo "用法:bash install.sh <target-repo-dir> [选项]" >&2; exit 2; }
[ -d "$TARGET" ] || { echo "目标目录不存在:$TARGET" >&2; exit 2; }
TARGET="$(cd "$TARGET" && pwd)"

# === 技能包选择(按栈/域 + 探测)===
. "$SCRIPT_DIR/detect_stacks.sh"
. "$SCRIPT_DIR/gate_branches.sh"

skill_pack() { sed -n 's/^pack:[[:space:]]*//p' "$1" | head -1; }  # 读某 SKILL.md 的 pack 值(保留 stack:go 里的冒号)

compute_selected() {  # 输出生效的包集合(含 universal)
  local sel="universal" st dm p plats
  if [ -n "$STACKS$DOMAINS" ]; then
    for st in ${STACKS//,/ }; do
      if [ "$st" = "frontend" ]; then
        sel="$sel frontend:common"
        plats="$FE_PLATFORMS"
        [ -z "$plats" ] && plats="$(detect_stacks "$TARGET" | tr ' ' '\n' | sed -n 's/^frontend:\(web\|mobile\|desktop\)$/\1/p' | tr '\n' ' ')"
        [ -z "$plats" ] && plats="web mobile desktop"
        for p in ${plats//,/ }; do sel="$sel frontend:$p"; done
      else
        sel="$sel stack:$st"
      fi
    done
    for dm in ${DOMAINS//,/ }; do sel="$sel domain:$dm"; done
  else
    sel="$sel $(detect_stacks "$TARGET")"
  fi
  printf '%s\n' $sel | grep -v '^$' | sort -u | tr '\n' ' '
}
SELECTED="$(compute_selected)"
pack_selected() { case " $SELECTED " in *" $1 "*) return 0 ;; *) return 1 ;; esac; }

if [ "$LIST_PACKS" = "1" ]; then
  echo "选中的包集合:$SELECTED"
  # 源 skills 已按 pack 分类到子目录(universal/stack/frontend/domain),递归找 SKILL.md
  while IFS= read -r skmd; do
    printf '  %-28s pack=%s\n' "$(basename "$(dirname "$skmd")")" "$(skill_pack "$skmd")"
  done < <(find "$SOURCE_DIR/claude-code/skills" -name SKILL.md | sort)
  exit 0
fi

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

# 从变体文件抽取 <!-- SECTION:name --> 到下一个 SECTION 标记(或 EOF)之间的内容
# 去掉该 section 尾部的连续空行,避免拼接后堆叠多余空行。
extract_section() {  # extract_section <variant-file> <name>
  awk -v n="$2" '
    $0 == "<!-- SECTION:" n " -->" { p=1; next }
    /^<!-- SECTION:/               { p=0 }
    p { buf[++i]=$0 }
    END {
      while (i>0 && buf[i] ~ /^[[:space:]]*$/) i--
      for (j=1; j<=i; j++) print buf[j]
    }
  ' "$1"
}

# 把 common 模板里的 <!-- @VARIANT:name --> 占位替换为变体文件对应 section,输出到 stdout
render_claude() {  # render_claude <common-file> <variant-file>
  local common="$1" variant="$2" line name
  while IFS= read -r line || [ -n "$line" ]; do
    case "$line" in
      '<!-- @VARIANT:'*' -->')
        name="${line#<!-- @VARIANT:}"; name="${name% -->}"
        extract_section "$variant" "$name"
        ;;
      *) printf '%s\n' "$line" ;;
    esac
  done < "$common"
}

say "装到 $TARGET (策略 $STRATEGY,形态 $PROFILE,客户端目录 $CC_DIR)"

# === core ===
say "core/ → 目标仓"
# scripts/
for f in "$SOURCE_DIR"/core/scripts/*; do
  safe_cp "$f" "$TARGET/${PREFIX}scripts/$(basename "$f")"
done
# .github/workflows/
# ci.yml 按 profile 选源(monorepo → ci.yml,single → ci.single.yml),统一落成 ci.yml;
# ci.single.yml 本身不单独铺(它只是 single 的 ci.yml 源)。其余 workflow 两形态通用,照铺。
for f in "$SOURCE_DIR"/core/workflows/*.yml; do
  base="$(basename "$f")"
  [ "$base" = "ci.single.yml" ] && continue
  if [ "$base" = "ci.yml" ]; then
    src_ci="$f"
    [ "$PROFILE" = "single" ] && src_ci="$SOURCE_DIR/core/workflows/ci.single.yml"
    safe_cp "$src_ci" "$TARGET/${PREFIX}.github/workflows/ci.yml"
    continue
  fi
  safe_cp "$f" "$TARGET/${PREFIX}.github/workflows/$base"
done
# 门禁分支:把带 "# gate-branches" 标记的 workflow 触发分支改成配置/探测的分支列表
GB="${GATE_BRANCHES:-$(default_gate_branches "$TARGET")}"
for wf in "$TARGET/${PREFIX}.github/workflows"/*.yml; do
  [ -f "$wf" ] && apply_gate_branches "$wf" "$GB"
done
ok "门禁分支(CI/AI-review 触发)= [$GB]"

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

# v2.4: PR 模板(自动出现在每个新 PR 描述里)
if [ -f "$SOURCE_DIR/.github/pull_request_template.md" ]; then
  safe_cp "$SOURCE_DIR/.github/pull_request_template.md" \
          "$TARGET/${PREFIX}.github/pull_request_template.md"
fi

# === claude-code(skills + agents)===
if [ "$NO_SKILLS" = "0" ]; then
  say "claude-code/ → $TARGET/$CC_DIR/"
  # 源 skills 按 pack 分类到子目录;这里递归找每个 SKILL.md,按 pack 过滤后
  # **拍平**安装到 .claude/skills/<name>/(Claude Code 按扁平一层发现 skill)。
  while IFS= read -r skmd; do
    sdir="$(dirname "$skmd")"
    name="$(basename "$sdir")"
    pack="$(skill_pack "$skmd" 2>/dev/null || true)"
    if [ -n "$pack" ] && ! pack_selected "$pack"; then
      skip "跳过 $name(pack=$pack 未在选中集 [$SELECTED] 内)"
      continue
    fi
    for f in "$sdir"/*; do
      safe_cp "$f" "$TARGET/$CC_DIR/skills/$name/$(basename "$f")"
    done
  done < <(find "$SOURCE_DIR/claude-code/skills" -name SKILL.md | sort)
  # PACKS.md(包分类单一信源)随 skills 一起铺
  safe_cp "$SOURCE_DIR/claude-code/skills/PACKS.md" "$TARGET/$CC_DIR/skills/PACKS.md"
  for f in "$SOURCE_DIR"/claude-code/agents/*.toml; do
    safe_cp "$f" "$TARGET/$CC_DIR/agents/$(basename "$f")"
  done
  # CLAUDE.md 只在目标仓没有时装(它太关键,不允许自动覆盖)
  # 由 common 模板 + <profile> 变体拼接生成(见 templates/)。
  if [ ! -f "$TARGET/CLAUDE.md" ]; then
    render_claude \
      "$SOURCE_DIR/claude-code/templates/CLAUDE.common.md" \
      "$SOURCE_DIR/claude-code/templates/CLAUDE.$PROFILE.md" \
      > "$TARGET/CLAUDE.md"
    ok "+ CLAUDE.md(profile=$PROFILE,你需要替换占位)"
  else
    skip "CLAUDE.md 已存在,跳过(请手动 merge claude-code/templates/CLAUDE.{common,$PROFILE}.md 的新增内容)"
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

# === 装 git hooks(pre-push 拦直接 push main;pre-commit 提交前自检)===
if [ -d "$TARGET/.git" ]; then
  cp "$SOURCE_DIR/core/hooks/pre-push" "$TARGET/.git/hooks/pre-push" && chmod +x "$TARGET/.git/hooks/pre-push"
  ok "+ .git/hooks/pre-push(拦直接 push main)"
  cp "$SOURCE_DIR/core/hooks/pre-commit" "$TARGET/.git/hooks/pre-commit" && chmod +x "$TARGET/.git/hooks/pre-commit"
  ok "+ .git/hooks/pre-commit(提交前自检,调项目 precommit 入口)"
fi

# === Graphify 知识图谱(可选,best-effort 安装)===
# install.sh 会尝试安装 graphify 并接入(CLAUDE.md 规则 / PreToolUse hook / 自动更新 git hook)。
# graphify 为可选:装不上不阻塞安装(只提示);--skip-graphify 可跳过整段。
# 初始图谱(graphify build)需 LLM key,缺 key 时跳过,留待项目内配好 key 后再跑。
if [ "$SKIP_GRAPHIFY" = "0" ]; then
  say "Graphify 知识图谱 → 尝试安装 + 接入(可选)"
  if ! command -v graphify >/dev/null 2>&1; then
    if command -v pipx >/dev/null 2>&1; then
      pipx install graphifyy >/dev/null 2>&1 || true
    elif command -v pip3 >/dev/null 2>&1; then
      pip3 install --user graphifyy >/dev/null 2>&1 || true
    elif command -v pip >/dev/null 2>&1; then
      pip install --user graphifyy >/dev/null 2>&1 || true
    fi
  fi
  if command -v graphify >/dev/null 2>&1; then
    if ( cd "$TARGET" && graphify claude install ) >/dev/null 2>&1; then
      ok "graphify claude install(CLAUDE.md 规则 + PreToolUse hook)"
    else
      skip "graphify claude install 告警——请在项目内手动跑一次"
    fi
    if ( cd "$TARGET" && graphify hook install ) >/dev/null 2>&1; then
      ok "graphify hook install(post-commit/post-checkout 自动更新)"
    else
      skip "graphify hook install 告警——请在项目内手动跑一次"
    fi
    if ( cd "$TARGET" && graphify build ) >/dev/null 2>&1; then
      ok "graphify build → graphify-out/ 初始图谱已生成"
    else
      skip "graphify build 未出图(通常缺 LLM key)——配好 key 后在项目内跑 'graphify build' 并提交 graphify-out/"
    fi
  else
    skip "graphify 未安装且无法自动安装(缺 pipx/pip 或网络)——可选,跳过。想启用:pipx install graphifyy 后重跑,或在项目内跑 graphify build。"
  fi
else
  skip "Graphify 安装被 --skip-graphify 跳过(graphify 为可选)。"
fi

cat <<EOF

============================================================
✅ 安装完成

下一步:
  1. 编辑 CLAUDE.md 把 [占位] 换成项目真实信息
  2. 编辑 ${PREFIX}.github/workflows/ci.yml 注释掉用不到的语言 job
  3. 在 GitHub Repo Settings 配 LLM_PROVIDER + LLM_API_KEY(详见 docs/多模型适配.md)
  4. 生成知识图谱(可选):配好 key 后跑 graphify build,把 graphify-out/ 提交进仓库
  5. 给本仓(及 docs-repo)开分支保护:bash tools/setup-branch-protection.sh <owner/repo>
  6. 跑 bash tools/verify.sh 做 5 项 sanity
  7. 推到分支 + 开 draft PR,自己 review 后再合 main
============================================================
EOF
