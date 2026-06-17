#!/usr/bin/env bash
# Run one full feature-loop cycle (dry-run safe steps + optional verify).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

DRY=""
FEATURE=""
SKIP_VERIFY=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY="--dry-run"; shift ;;
    --feature) FEATURE="$2"; shift 2 ;;
    --skip-verify) SKIP_VERIFY=1; shift ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

echo "== Loop triage =="
python3 scripts/loop_triage.py $DRY

echo "== Loop select =="
if [[ -n "$FEATURE" ]]; then
  python3 scripts/loop_select.py --feature "$FEATURE" $DRY
else
  SELECTED=$(python3 scripts/loop_select.py $DRY | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('selected',{}).get('id',''))")
  FEATURE="$SELECTED"
fi

if [[ -z "$FEATURE" ]]; then
  echo "No feature selected."
  exit 1
fi

echo "== Loop plan ($FEATURE) =="
python3 scripts/loop_plan.py --feature "$FEATURE" $DRY

if [[ -z "$DRY" ]]; then
  echo "== Worktree =="
  bash scripts/loop_spawn_worktree.sh "$FEATURE" || true
fi

if [[ -z "$SKIP_VERIFY" ]]; then
  echo "== Loop verify ($FEATURE) =="
  python3 scripts/loop_verify.py --feature "$FEATURE" $DRY || true
fi

echo "Done. Next: implement in worktree, reviewer, human merge."
