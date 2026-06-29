#!/usr/bin/env bash
# 给指定仓的分支开保护:require PR + required checks + 禁绕过 + 禁直接 push
# 用法: bash setup-branch-protection.sh <owner/repo> [branch]  (默认 main)
# 需要: gh auth login,且对该仓有 admin 权限
set -euo pipefail
REPO="${1:?用法: bash setup-branch-protection.sh <owner/repo> [branch]}"
BRANCH="${2:-main}"
gh api -X PUT "repos/$REPO/branches/$BRANCH/protection" --input - <<'JSON'
{
  "required_status_checks": { "strict": true, "contexts": ["ci-gate", "ai-review-gate"] },
  "enforce_admins": true,
  "required_pull_request_reviews": { "required_approving_review_count": 1 },
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false
}
JSON
echo "✓ $REPO@$BRANCH 已开分支保护(require PR + ci-gate/ai-review-gate + enforce_admins + 禁 force/删除)"
