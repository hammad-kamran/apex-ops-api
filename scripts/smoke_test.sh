#!/usr/bin/env bash
# Post-deployment verification. Exit code 0 = healthy release.
# Usage: smoke_test.sh <expected-version>
set -euo pipefail
EXPECTED="${1:?usage: smoke_test.sh <expected-version>}"
BASE="http://127.0.0.1:${API_PORT:-8000}"

echo "[smoke] waiting for readiness at $BASE/health/ready"
for i in $(seq 1 30); do
  if curl -fsS "$BASE/health/ready" >/dev/null 2>&1; then
    echo "[smoke] ready after ${i} attempt(s)"
    break
  fi
  if [[ "$i" == 30 ]]; then
    echo "[smoke] FAIL: service never became ready" >&2
    curl -sS "$BASE/health/ready" >&2 || true
    exit 1
  fi
  sleep 2
done

actual=$(curl -fsS "$BASE/api/v1/version" | python3 -c 'import json,sys; print(json.load(sys.stdin)["version"])')
if [[ "$actual" != "$EXPECTED" ]]; then
  echo "[smoke] FAIL: expected version $EXPECTED but got $actual" >&2
  exit 1
fi
echo "[smoke] version OK: $actual"

id=$(curl -fsS -X POST "$BASE/api/v1/tasks" -H 'Content-Type: application/json' \
       -d '{"title":"smoke test task"}' | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')
curl -fsS "$BASE/api/v1/tasks/$id" >/dev/null
echo "[smoke] write/read OK (task $id)"
curl -fsS "$BASE/metrics" | grep -q "apex_app_info" && echo "[smoke] metrics OK"
echo "[smoke] PASS"
