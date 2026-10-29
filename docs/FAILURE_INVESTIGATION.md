# Failure investigation: database outage

Reproduce with `./scripts/failure_drill.sh` (full output saved to `evidence/failure_drill.log`).

**Scenario:** PostgreSQL stops while the API is running.

| Step | Signal | What it told me |
|---|---|---|
| Detect | `/health/ready` → 503 `{"checks":{"database":"down"}}`; `apex_db_up 0`; `ApexDatabaseDown` would fire after 1 minute | Service is not able to serve traffic |
| Scope | `/health/live` → 200; `/api/v1/tasks` → 503 JSON with `request_id` | The API process is fine; the dependency is the problem. No restart loop |
| Diagnose | Error logs: `{"level": "ERROR", "message": "database error", "error": "connection failed: OperationalError", "request_id": "..."}`; `docker compose ps` shows `db` exited | Root cause: database container stopped |
| Recover | `docker compose up -d --wait db` | Readiness returns 200 and `apex_db_up 1` automatically; no API restart needed (schema check re-runs on reconnect) |
| Prevent | `restart: unless-stopped` on db, alert on `apex_db_up`, managed PostgreSQL with HA in cloud | |

**Timeline from my run (29 Oct 2026, UTC):** database stopped at about 09:25:45; outage detected at 09:25:48 (readiness 503, ERROR log with request_id a6c2ad6b, apex_db_up 0); database restarted and readiness recovered automatically within seconds, with no API restart.
