#!/usr/bin/env bash
# tools/ensure_skills.test.sh — 验证幂等安装脚本的核心行为
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# 造一个假的 target 仓，预置 4 个团队 skill 但缺 superpowers
mkdir -p "$TMP/.claude/skills/secure-coding" "$TMP/.claude/skills/clean-code"
mkdir -p "$TMP/.claude/skills/testing-standards" "$TMP/.claude/skills/sql-optimization"

# 用 DRY_RUN 跑（不真正 git clone），断言它报告"superpowers 缺失、将安装"且"团队 skill 已存在、跳过"
OUT="$(DRY_RUN=1 bash "$SCRIPT_DIR/ensure_skills.sh" "$TMP" 2>&1)"
echo "$OUT" | grep -q 'superpowers: 缺失' || { echo "FAIL: 未检测到 superpowers 缺失"; exit 1; }
echo "$OUT" | grep -q 'secure-coding: 已存在' || { echo "FAIL: 未跳过已存在 skill"; exit 1; }
echo "PASS"
