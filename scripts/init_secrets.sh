#!/usr/bin/env bash
# Generates a random local database password. Never committed (see .gitignore).
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p secrets
if [[ -s secrets/db_password.txt ]]; then
  echo "secrets/db_password.txt already exists, keeping it."
  exit 0
fi
umask 022
openssl rand -base64 24 | tr -d '/+=\n' > secrets/db_password.txt
# 0644 so the non-root container user (uid 10001) can read the bind-mounted secret.
# Acceptable for local development only; cloud hosting uses a managed secret store.
chmod 0644 secrets/db_password.txt
echo "Created secrets/db_password.txt"
