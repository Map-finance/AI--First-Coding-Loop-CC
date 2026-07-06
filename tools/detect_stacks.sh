#!/usr/bin/env bash
# =============================================================================
# detect_stacks.sh — 探测目标仓的技术栈/业务域,输出空格分隔的 pack 集合
# -----------------------------------------------------------------------------
# 输出形如:"stack:go frontend:common frontend:web domain:web3-solidity"
# 零依赖(不引 jq),package.json 依赖判断用 grep。可被 install.sh source,
# 也可直接:bash detect_stacks.sh <dir>
# 探测规则见 claude-code/skills/PACKS.md。
# =============================================================================

detect_stacks() {
  local t="$1" out=""

  # 后端语言栈
  [ -f "$t/go.mod" ] && out="$out stack:go"
  { [ -f "$t/pom.xml" ] || ls "$t"/build.gradle* >/dev/null 2>&1; } && out="$out stack:java"
  [ -f "$t/Cargo.toml" ] && out="$out stack:rust"
  { [ -f "$t/pyproject.toml" ] || ls "$t"/requirements*.txt >/dev/null 2>&1; } && out="$out stack:python"

  # web3 / solidity
  if [ -f "$t/foundry.toml" ] || ls "$t"/hardhat.config.* >/dev/null 2>&1 \
     || [ -n "$(find "$t" -name '*.sol' -not -path '*/node_modules/*' 2>/dev/null | head -1)" ]; then
    out="$out domain:web3-solidity"
  fi

  # Node 后端 + 前端平台(读 package.json 依赖)
  local pkg="$t/package.json" fe=""
  if [ -f "$pkg" ]; then
    grep -Eq '"(express|koa|@nestjs/core|fastify|hapi|@hapi/hapi)"' "$pkg" && out="$out stack:node"
    grep -Eq '"(next|nuxt|react-dom|vue|svelte|@angular/core|vite)"' "$pkg" && fe="$fe frontend:web"
    grep -Eq '"(react-native|expo|@ionic/[a-z-]+)"'                  "$pkg" && fe="$fe frontend:mobile"
    grep -Eq '"(electron|@tauri-apps/[a-z-]+)"'                      "$pkg" && fe="$fe frontend:desktop"
  fi
  # Flutter 移动端
  [ -f "$t/pubspec.yaml" ] && fe="$fe frontend:mobile"
  # 任一前端平台命中 → 补 frontend:common
  [ -n "$fe" ] && out="$out frontend:common$fe"

  # 去重、去空、稳定排序
  printf '%s\n' $out | grep -v '^$' | sort -u | tr '\n' ' ' | sed 's/ *$//'
}

# 直接调用入口
if [ "${BASH_SOURCE[0]:-$0}" = "$0" ]; then
  detect_stacks "${1:-.}"
fi
