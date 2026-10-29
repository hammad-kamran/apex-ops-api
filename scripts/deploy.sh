#!/usr/bin/env bash
# Deploys a versioned image with Docker Compose, verifies it, and rolls back
# automatically to the last known-good version if verification fails.
# Usage: deploy.sh <image-tag>          e.g. deploy.sh 1.0.0
# Env:   API_IMAGE (default apex-ops-api; set to ghcr.io/<owner>/<repo> to pull from the registry)
set -euo pipefail
cd "$(dirname "$0")/.."

TAG="${1:?usage: deploy.sh <image-tag>}"
IMAGE="${API_IMAGE:-apex-ops-api}"
HISTORY=".deploy/history"
mkdir -p .deploy
touch "$HISTORY"

./scripts/init_secrets.sh

if ! docker image inspect "$IMAGE:$TAG" >/dev/null 2>&1; then
  if [[ "$IMAGE" == "apex-ops-api" ]]; then
    echo "[deploy] building $IMAGE:$TAG locally"
    docker build --build-arg APP_VERSION="$TAG" -t "$IMAGE:$TAG" .
  else
    echo "[deploy] pulling $IMAGE:$TAG"
    docker pull "$IMAGE:$TAG"
  fi
fi

LAST_GOOD=$(tail -n 1 "$HISTORY" || true)
echo "[deploy] current: ${LAST_GOOD:-none} -> target: $TAG"

export IMAGE_TAG="$TAG" API_IMAGE="$IMAGE"
docker compose up -d --no-build --wait db
docker compose up -d --no-build api

if ./scripts/smoke_test.sh "$TAG"; then
  echo "$TAG" >> "$HISTORY"
  echo "[deploy] SUCCESS: $TAG is live and recorded in $HISTORY"
else
  echo "[deploy] verification FAILED for $TAG" >&2
  docker compose logs --tail=30 api >&2 || true
  if [[ -n "$LAST_GOOD" ]]; then
    echo "[deploy] automatic rollback to last known-good version $LAST_GOOD" >&2
    IMAGE_TAG="$LAST_GOOD" docker compose up -d --no-build api
    ./scripts/smoke_test.sh "$LAST_GOOD"
    echo "[deploy] rolled back to $LAST_GOOD" >&2
  else
    echo "[deploy] no previous version to roll back to; stopping api" >&2
    docker compose stop api
  fi
  exit 1
fi
