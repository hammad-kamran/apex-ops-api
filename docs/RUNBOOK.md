# Runbook: Apex Operations API

All commands run from the repository root. Base URL: `http://127.0.0.1:8000`.

## 1. Deploy

```bash
./scripts/deploy.sh <version>                         # build locally if the image is missing
API_IMAGE=ghcr.io/<owner>/<repo> ./scripts/deploy.sh <version>   # deploy an image built by CI
```

What it does: creates the DB secret if missing, starts PostgreSQL and waits until healthy, replaces the API
container with the requested version, runs `scripts/smoke_test.sh` (readiness, version match, write/read, metrics).
On success the version is appended to `.deploy/history`. **On failure it automatically rolls back to the last
known-good version** and exits non-zero.

Verify: `curl -s :8000/api/v1/version` and `docker compose ps` (api should be `healthy`).

## 2. Rollback

| Situation | Command |
|---|---|
| Bad release detected by smoke test | Automatic (inside `deploy.sh`) |
| Problem found after a successful deploy | `./scripts/rollback.sh` (previous release) |
| Go to a specific version | `./scripts/rollback.sh <version>` |

Rollback only swaps the API image. The database volume is untouched. **Schema changes must stay
backward-compatible** (expand/contract) so an older version can run against the newer schema.

Verify: version endpoint shows the target version, `/health/ready` returns 200.

## 3. Incident response

1. **Acknowledge** the alert and note the start time.
2. **Assess impact:** `curl -s -w ' %{http_code}\n' :8000/health/ready` and `:8000/api/v1/tasks`.
3. **Mitigate first:** if the incident started after a release, roll back (`./scripts/rollback.sh`) before deep debugging.
4. **Diagnose** using the playbooks below.
5. **Recover and verify** with `./scripts/smoke_test.sh $(tail -n1 .deploy/history)`.
6. **Follow up:** short post-incident note (timeline, root cause, fix, prevention).

### Incident: API down
- `docker compose ps` → is `api` running or restarting?
- `docker compose logs --tail=100 api` → startup errors (bad config, missing secret file).
- `docker inspect --format '{{json .State.Health}}' apex-ops-api-1` → recent health check results.
- Fix: correct config and redeploy, or roll back.

### Incident: database unreachable
Symptoms: `/health/ready` 503 with `"database": "down"`, API calls 503, `apex_db_up 0`, `ApexDatabaseDown` alert. `/health/live` stays 200 (by design, so the API is not restarted in a loop).
- `docker compose ps db` and `docker compose logs --tail=50 db`
- `docker compose exec db pg_isready -U apex -d apex_ops`
- Error logs: `docker compose logs api | grep '"level": "ERROR"'` (each entry carries a `request_id`)
- Fix: `docker compose up -d --wait db`; check disk space (`docker system df`) and volume health.

### Incident: high error rate
- Find failing routes: `curl -s :8000/metrics | grep 'status="5'`
- Correlate with the request IDs in error logs.
- If it began with a release → roll back. Otherwise check the database playbook.

## 4. Troubleshooting

| Symptom | Likely cause | Check / fix |
|---|---|---|
| `deploy.sh` fails at "waiting for readiness" | DB not ready, wrong secret, fault-injected build | `docker compose logs api db` |
| `permission denied` reading secret | secret file not readable by uid 10001 | `chmod 0644 secrets/db_password.txt` |
| Port 8000 in use | another process | `API_PORT=8080 ./scripts/deploy.sh <v>` |
| Old version still served | image tag not changed / container not recreated | `docker compose ps`, check `IMAGE_TAG` |
| Slow responses | DB latency, single worker saturated | latency metric per path; scale threads/workers |
| Database password changed but DB rejects it | Postgres only reads the password on first init | recreate volume (`down -v`, **data loss**) or `ALTER USER` |

Useful commands: `docker compose ps`, `docker compose logs -f api`, `docker stats`, `docker compose exec db psql -U apex apex_ops`.
