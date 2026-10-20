#!/bin/zsh
set -u
ROOT=/Users/yongbiaoli/lei-signal-integration-20260909
OUT="$ROOT/docs/experiments/raw/agent-03b-runtime-integration-2026-09-09/browser"
FILES=(
  web/src/components/PlanDraftCard.tsx
  web/src/components/AgentConsole.tsx
  web/src/pages/AgentWorkspacePage.tsx
  web/src/App.tsx
  web/src/api/client.ts
  web/src/types.ts
  web/src/utils/resolveRoute.ts
  web/src/utils/backtestTasks.ts
  src/lei_signal/api/routes/agent.py
  src/lei_signal/api/routes/plans.py
)
cd "$ROOT" || exit 2
shasum -a 256 "${FILES[@]}" > "$OUT/source-before.sha256"
git status --short > "$OUT/git-status-before.txt"
node "$OUT/e2e_browser.mjs" > "$OUT/run.log" 2>&1
CODE=$?
print -r -- "$CODE" > "$OUT/exit-code.txt"
shasum -a 256 "${FILES[@]}" > "$OUT/source-after.sha256"
cmp -s "$OUT/source-before.sha256" "$OUT/source-after.sha256"
print -r -- "$?" > "$OUT/source-hash-compare-exit.txt"
git status --short > "$OUT/git-status-after.txt"
tail -120 "$OUT/run.log"
exit "$CODE"
