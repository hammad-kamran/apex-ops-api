# Evidence checklist

Everything here must come from a real run. Replace each item with the actual file.

| # | Evidence | How to produce | File |
|---|---|---|---|
| 1 | Green CI run (all jobs) | Push to `main` on GitHub → Actions tab screenshot | `evidence/01_ci_green.png` |
| 2 | Blocked release (intentional failure) | Actions → CI → Run workflow → tick `demo_failure` → screenshot showing `test` failed and `build-scan-deploy` skipped | `evidence/02_ci_blocked.png` |
| 3 | Test results | `pytest -v` output or downloaded `test-report` artifact | `evidence/03_tests.txt` |
| 4 | Deployment demo | `./scripts/deploy.sh 1.0.0` output + `docker compose ps` | `evidence/04_deploy.png` |
| 5 | Release + automatic and manual rollback | `./scripts/release_demo.sh` | `evidence/release_demo.log` |
| 6 | Failure investigation | `./scripts/failure_drill.sh` | `evidence/failure_drill.log` |
| 7 | Structured logs and metrics | `docker compose logs api` and `curl :8000/metrics` | `evidence/07_logs_metrics.png` |
| 8 | Non-root + scan results | CI step "Verify container runs as non-root" and Trivy step | `evidence/08_security.png` |
| 9 | (Optional) Prometheus alerts page | `--profile monitoring`, open :9090/alerts | `evidence/09_prometheus.png` |
