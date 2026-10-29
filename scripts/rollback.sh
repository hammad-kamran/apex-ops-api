#!/usr/bin/env bash
# Manual rollback to the previous successful release (or to an explicit tag).
# Usage: rollback.sh            -> previous version from .deploy/history
#        rollback.sh <tag>      -> a specific earlier version
set -euo pipefail
cd "$(dirname "$0")/.."

HISTORY=".deploy/history"
IMAGE="${API_IMAGE:-apex-ops-api}"
[[ -s "$HISTORY" ]] || { echo "[rollback] no deployment history found" >&2; exit 1; }

CURRENT=$(tail -n 1 "$HISTORY")
if [[ $# -ge 1 ]]; then
  TARGET="$1"
else
  [[ $(wc -l < "$HISTORY") -ge 2 ]] || { echo "[rollback] only one release recorded; nothing to roll back to" >&2; exit 1; }
  TARGET=$(tail -n 2 "$HISTORY" | head -n 1)
fi

docker image inspect "$IMAGE:$TARGET" >/dev/null 2>&1 || docker pull "$IMAGE:$TARGET"

echo "[rollback] $CURRENT -> $TARGET"
export IMAGE_TAG="$TARGET" API_IMAGE="$IMAGE"
docker compose up -d --no-build api
./scripts/smoke_test.sh "$TARGET"

if [[ $# -ge 1 ]]; then
  echo "$TARGET" >> "$HISTORY"
else
  sed -i.bak '$d' "$HISTORY" && rm -f "$HISTORY.bak"   # pop the release we rolled back from
fi
echo "[rollback] SUCCESS: $TARGET is live (database volume untouched)"
