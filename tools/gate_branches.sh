#!/usr/bin/env bash
# =============================================================================
# gate_branches.sh — 把带 "# gate-branches" 标记的 workflow 触发分支列表重写
# -----------------------------------------------------------------------------
# 门禁 workflow 的 on: 段里,需要按安装配置调整的 `branches:` 行末尾带注释
# `# gate-branches`。apply_gate_branches 把这些行的 [...] 换成给定分支列表。
# 可被 install.sh source,也可:bash gate_branches.sh <file> "main dev test"
# =============================================================================

# apply_gate_branches <yaml-file> "b1 b2 b3"(或逗号分隔)
apply_gate_branches() {
  local f="$1" list="$2" joined
  [ -f "$f" ] || return 0
  joined="$(printf '%s' "$list" | tr ' ,' '\n\n' | grep -v '^$' | paste -sd, - | sed 's/,/, /g')"
  # 仅替换带 # gate-branches 标记的 branches 行,保留缩进与标记
  perl -i -pe 'BEGIN{$j=shift @ARGV} s/^(\s*branches:\s*)\[[^\]]*\](\s*#\s*gate-branches.*)$/$1\[$j\]$2/' "$joined" "$f"
}

# default_gate_branches <repo-dir> → "main dev test"(默认分支 ∪ 存在的环境分支)
default_gate_branches() {
  local repo="$1" def="" b out=""
  for b in main master; do
    git -C "$repo" show-ref --verify --quiet "refs/heads/$b" 2>/dev/null && { def="$b"; break; }
  done
  [ -z "$def" ] && def="$(git -C "$repo" symbolic-ref --short HEAD 2>/dev/null || echo main)"
  out="$def"
  for b in dev develop test staging; do
    git -C "$repo" show-ref --verify --quiet "refs/heads/$b" 2>/dev/null && out="$out $b"
  done
  printf '%s' "$out" | tr ' ' '\n' | awk 'NF && !seen[$0]++' | tr '\n' ' ' | sed 's/ *$//'
}

if [ "${BASH_SOURCE[0]:-$0}" = "$0" ]; then
  apply_gate_branches "$1" "$2"
fi
