#!/usr/bin/env bash
# Create an isolated git worktree for a loop feature branch.
set -euo pipefail

FEATURE_ID="${1:?Usage: loop_spawn_worktree.sh FEAT-001}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BRANCH="loop/${FEATURE_ID}"
WORKTREE_DIR="$(dirname "$ROOT")/wt-${FEATURE_ID}"

cd "$ROOT"

if git worktree list | grep -q "wt-${FEATURE_ID}"; then
  echo "Worktree already exists: $WORKTREE_DIR"
  exit 0
fi

if git show-ref --verify --quiet "refs/heads/${BRANCH}"; then
  git worktree add "$WORKTREE_DIR" "$BRANCH"
else
  git worktree add -b "$BRANCH" "$WORKTREE_DIR"
fi

echo "Worktree ready: $WORKTREE_DIR (branch $BRANCH)"
echo "Implement feature $FEATURE_ID inside the worktree only."
