#!/usr/bin/env bash
# End-to-end evidence run: v1.0.0 -> v1.1.0 -> broken v1.2.0 (auto rollback) -> manual rollback.
# Output is saved to evidence/release_demo.log
set -uo pipefail
cd "$(dirname "$0")/.."
mkdir -p evidence
exec > >(tee evidence/release_demo.log) 2>&1

step() { echo; echo "================ $* ================"; }

step "1. Deploy v1.0.0"
./scripts/deploy.sh 1.0.0

step "2. Deploy v1.1.0"
./scripts/deploy.sh 1.1.0

step "3. Build a deliberately broken v1.2.0 (readiness always fails)"
docker build --build-arg APP_VERSION=1.2.0 --build-arg APEX_FAULT_READY=1 -t apex-ops-api:1.2.0 .
./scripts/deploy.sh 1.2.0 || echo ">>> deploy of 1.2.0 failed as expected and was rolled back automatically"
curl -s http://127.0.0.1:${API_PORT:-8000}/api/v1/version; echo

step "4. Manual rollback 1.1.0 -> 1.0.0"
./scripts/rollback.sh
curl -s http://127.0.0.1:${API_PORT:-8000}/api/v1/version; echo

step "5. Data persisted across all releases"
curl -s http://127.0.0.1:${API_PORT:-8000}/api/v1/tasks; echo

step "Release history"
cat .deploy/history
