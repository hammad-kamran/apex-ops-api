# Evidence

All files below come from real runs on 29 Oct 2026 (local WSL2 + Docker Desktop, and GitHub Actions).

| # | Evidence | File |
|---|---|---|
| 1 | Green CI run: lint/test/audit, hadolint, build + non-root check + Trivy + compose deploy + smoke test + GHCR publish | `evidence/01_ci_green.png` |
| 2 | Blocked release: intentional failing test enabled via "Run workflow", test job failed, build/deploy skipped | `evidence/02_ci_blocked.png` |
| 3 | Test results (15 passed, 1 intentional-failure test skipped by default) | `evidence/03_tests.txt` |
| 4 | Local deployment with smoke test PASS and healthy containers | `evidence/04_deploy.log` |
| 5 | Release 1.0.0 -> 1.1.0, broken 1.2.0 auto-rolled back to 1.1.0, manual rollback to 1.0.0, data preserved | `evidence/release_demo.log` |
| 6 | Failure investigation: database outage detected, diagnosed and recovered | `evidence/failure_drill.log`, `docs/FAILURE_INVESTIGATION.md` |
| 7 | Structured JSON logs and Prometheus metrics | `evidence/07_logs_metrics.txt` |
| 8 | Security gate: pip-audit blocked a real vulnerability (Flask 3.1.1, PYSEC-2026-2151) on the first CI run | `evidence/08_security_gate.png` |

GitHub Actions run history: https://github.com/hammad-kamran/apex-ops-api/actions
