#!/usr/bin/env bash
# =============================================================================
# verify.sh — 5 项 sanity 校验目标仓的 harness 装配完整
# 在目标仓根目录运行:bash <path-to-this>/verify.sh
# 不调用真实 LLM,所有 mock 模式。
# =============================================================================
set -uo pipefail
pass=0; fail=0
ok()  { printf '\033[1;32m✓ %s\033[0m\n' "$*"; pass=$((pass+1)); }
bad() { printf '\033[1;31m✗ %s\033[0m\n' "$*"; fail=$((fail+1)); }

cd "$(pwd)"

# 1. env parity(如果有 .env 模板)
if [ -f config/.env.dev.example ] && [ -f config/.env.prod.example ]; then
  if python3 scripts/check_env_parity.py config/.env.dev.example config/.env.prod.example >/dev/null 2>&1; then
    ok "env parity"
  else
    bad "env parity 失败:dev/prod 模板 key 集合不一致"
  fi
else
  ok "(无 env 模板,跳过 env parity)"
fi

# 2. triage_engine mock
if OBSERVABILITY_BACKEND=mock TRACKER=github-dryrun python3 scripts/triage_engine.py >/dev/null 2>&1; then
  ok "triage_engine mock 跑通"
else
  bad "triage_engine 失败"
fi

# 3. ai_review.py 三趟 mock
for p in quality security dependency; do
  if python3 scripts/ai_review.py --pass $p --mock >/dev/null 2>&1; then
    ok "ai_review --pass $p mock"
  else
    bad "ai_review --pass $p 失败"
  fi
done

# 4. ModelAdapter 切厂商验证(走 stub,无 key)
for prov in anthropic openai deepseek; do
  if LLM_PROVIDER=$prov OBSERVABILITY_BACKEND=mock python3 scripts/health_report.py >/dev/null 2>&1; then
    ok "ModelAdapter provider=$prov stub 路径 OK"
  else
    bad "ModelAdapter provider=$prov 失败"
  fi
done

# 5. YAML / TOML 健全性
# pyyaml 不是 stdlib —— 干净机器(系统 python3)往往没装。区分两种情况:
# import 失败 = 缺依赖,跳过不算失败;解析失败 = YAML 真的非法,才 bad。
if ! python3 -c "import yaml" 2>/dev/null; then
  ok "(未装 pyyaml,跳过 workflow YAML 校验 —— pip install pyyaml 可启用)"
elif python3 -c "import yaml,glob; [yaml.safe_load(open(f)) for f in glob.glob('.github/workflows/*.yml')]" 2>/dev/null; then
  ok "workflow YAML 合法"
else
  bad "workflow YAML 解析失败"
fi
if compgen -G ".claude/agents/*.toml" > /dev/null; then
  if python3 -c "
try: import tomllib as t
except: import tomli as t
import glob
for f in glob.glob('.claude/agents/*.toml'):
    d=t.loads(open(f,'rb').read().decode())
    assert 'provider' in d and 'model' in d, f
" 2>/dev/null; then
    ok "agent TOMLs 合法且含 provider/model"
  else
    bad "agent TOMLs 解析失败"
  fi
elif compgen -G ".codex/agents/*.toml" > /dev/null; then
  ok "(.codex agents 找到,跳过 .claude 检查)"
else
  ok "(无 agent TOMLs,跳过)"
fi

echo
printf "\033[1m通过 %d / 失败 %d\033[0m\n" "$pass" "$fail"
[ "$fail" -eq 0 ]
