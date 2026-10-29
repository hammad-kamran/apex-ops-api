#!/usr/bin/env bash
# Failure investigation drill: simulate a database outage, detect it, diagnose, recover.
# Output is saved to evidence/failure_drill.log
set -uo pipefail
cd "$(dirname "$0")/.."
mkdir -p evidence
exec > >(tee evidence/failure_drill.log) 2>&1
BASE="http://127.0.0.1:${API_PORT:-8000}"

echo "== Baseline =="
curl -s "$BASE/health/ready"; echo
curl -s "$BASE/metrics" | grep '^apex_db_up'

echo; echo "== Inject failure: stop the database =="
docker compose stop db
sleep 3

echo; echo "== Detect: readiness, API and metrics =="
curl -s -w '  (HTTP %{http_code})\n' "$BASE/health/ready"
curl -s -w '  (HTTP %{http_code})\n' "$BASE/api/v1/tasks"
curl -s -w '  (HTTP %{http_code})\n' "$BASE/health/live"
curl -s "$BASE/metrics" | grep '^apex_db_up'

echo; echo "== Diagnose: structured logs (errors only) =="
docker compose logs --no-log-prefix --tail=50 api | grep '"level": "ERROR"' | tail -n 5
echo; docker compose ps

echo; echo "== Recover: start the database =="
docker compose up -d --wait db
sleep 2
curl -s "$BASE/health/ready"; echo
curl -s "$BASE/metrics" | grep '^apex_db_up'
echo; echo "== Drill complete =="
