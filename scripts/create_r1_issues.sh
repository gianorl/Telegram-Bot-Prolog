#!/usr/bin/env bash
# Creates one GitHub issue per file in docs/issues/, labeled "R1".
# Requires the GitHub CLI: brew install gh && gh auth login
set -euo pipefail

cd "$(dirname "$0")/.."

gh label create R1 --color 1f6feb --description "Release 1: Money core" --force >/dev/null

for f in docs/issues/*.md; do
  title="$(head -n 1 "$f" | sed 's/^# //')"
  body="$(tail -n +2 "$f")"
  echo "Creating: $title"
  gh issue create --title "$title" --body "$body" --label R1 >/dev/null
done

echo "Done. See: gh issue list --label R1"
