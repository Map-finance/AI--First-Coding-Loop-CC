#!/usr/bin/env bash
# =============================================================================
# install_matrix.test.sh — 技能包按栈/域选装 + 门禁分支 的集成测试
# 造临时"目标仓",跑 install.sh,断言只落该装的 skill 包。
# 用法:bash tools/install_matrix.test.sh
# =============================================================================
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
. "$HERE/detect_stacks.sh"

pass=0; fail=0
ok()   { echo "  ✓ $1"; pass=$((pass+1)); }
bad()  { echo "  ✗ $1"; fail=$((fail+1)); }
has()  { case " $1 " in *" $2 "*) return 0 ;; *) return 1 ;; esac; }

echo "== 1) detect_stacks 单元 =="
d=$(mktemp -d); echo 'module x' >"$d/go.mod"
out="$(detect_stacks "$d")"; has "$out" "stack:go" && ok "go.mod→stack:go" || bad "go.mod→$out"; rm -rf "$d"

d=$(mktemp -d); echo '{"dependencies":{"react-dom":"18"}}' >"$d/package.json"
out="$(detect_stacks "$d")"; { has "$out" "frontend:web" && has "$out" "frontend:common"; } && ok "react-dom→frontend:web+common" || bad "react-dom→$out"; rm -rf "$d"

d=$(mktemp -d); echo '[package]' >"$d/Cargo.toml"
out="$(detect_stacks "$d")"; has "$out" "stack:rust" && ok "Cargo.toml→stack:rust" || bad "Cargo.toml→$out"; rm -rf "$d"

d=$(mktemp -d); echo 'x' >"$d/foundry.toml"
out="$(detect_stacks "$d")"; has "$out" "domain:web3-solidity" && ok "foundry.toml→web3" || bad "foundry.toml→$out"; rm -rf "$d"

echo "== 2) install 按 pack 选装 =="
# ① 纯 Go 仓:装 go-* + universal,不装 financial-numerics
t=$(mktemp -d); echo 'module x' >"$t/go.mod"
bash "$ROOT/tools/install.sh" "$t" --skip-graphify >/dev/null 2>&1
[ -f "$t/.claude/skills/go-logging/SKILL.md" ]        && ok "go 仓:装了 go-logging"            || bad "go 仓:缺 go-logging"
[ -f "$t/.claude/skills/agent-coding-discipline/SKILL.md" ] && ok "go 仓:装了 universal"        || bad "go 仓:缺 universal"
[ ! -f "$t/.claude/skills/financial-numerics/SKILL.md" ] && ok "go 仓:未装 financial(未选中)"  || bad "go 仓:误装 financial"
rm -rf "$t"

# ② 纯前端仓:装 frontend:* + universal,不装 go-*
t=$(mktemp -d); echo '{"dependencies":{"react-dom":"18"}}' >"$t/package.json"
bash "$ROOT/tools/install.sh" "$t" --skip-graphify >/dev/null 2>&1
[ ! -f "$t/.claude/skills/go-logging/SKILL.md" ]      && ok "前端仓:未装 go-logging"            || bad "前端仓:误装 go-logging"
[ -f "$t/.claude/skills/clean-code/SKILL.md" ]        && ok "前端仓:装了 universal"             || bad "前端仓:缺 universal"
rm -rf "$t"

# ③ 显式 --domains finance:装 financial-numerics
t=$(mktemp -d); echo 'module x' >"$t/go.mod"
bash "$ROOT/tools/install.sh" "$t" --stacks go --domains finance --skip-graphify >/dev/null 2>&1
[ -f "$t/.claude/skills/financial-numerics/SKILL.md" ] && ok "--domains finance:装了 financial" || bad "--domains finance:缺 financial"
rm -rf "$t"


echo "== 3) 门禁分支模板 =="
t=$(mktemp -d); ( cd "$t" && git init -q -b main && git commit -q --allow-empty -m x && git branch dev && git branch test ); echo "module x" >"$t/go.mod"
bash "$ROOT/tools/install.sh" "$t" --skip-graphify >/dev/null 2>&1
grep -q "branches: \[main, dev, test\]" "$t/.github/workflows/ci.yml" && ok "探测到 dev/test → ci.yml 门禁含三分支" || bad "ci.yml 门禁未含 dev/test:$(grep -m1 gate-branches "$t/.github/workflows/ci.yml")"
grep -q "branches: \[main, dev, test\]" "$t/.github/workflows/ai-review.yml" && ok "ai-review.yml pull_request 门禁含三分支" || bad "ai-review 门禁未含 dev/test"
rm -rf "$t"

t=$(mktemp -d); ( cd "$t" && git init -q -b main && git commit -q --allow-empty -m x && git branch dev ); echo "module x" >"$t/go.mod"
bash "$ROOT/tools/install.sh" "$t" --gate-branches main --skip-graphify >/dev/null 2>&1
grep -q "branches: \[main\]  # gate-branches" "$t/.github/workflows/ci.yml" && ok "--gate-branches main 覆盖:只含 main" || bad "覆盖失败"
rm -rf "$t"

echo
echo "== 结果:$pass 通过,$fail 失败 =="
[ "$fail" = "0" ]
