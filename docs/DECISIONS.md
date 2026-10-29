# Decision memo

## Summary
A deliberately small, boring stack (Flask + Gunicorn + PostgreSQL + Docker Compose + GitHub Actions) so the
focus stays on release safety, security hygiene and operability rather than application complexity.

## Key decisions and trade-offs

| Decision | Why | Trade-off |
|---|---|---|
| Flask + Gunicorn | Small, well understood, quick to review | Less built-in validation than FastAPI |
| Separate liveness and readiness | A DB outage should stop traffic, not trigger restart loops | Readiness must be wired to the orchestrator (Compose healthcheck here) |
| Single Gunicorn worker, 4 threads | In-memory metrics stay consistent without a multiprocess metrics setup | Lower CPU parallelism; at scale use `prometheus_client` multiprocess mode or more replicas |
| Hand-written Prometheus exporter | Zero extra dependency, easy to explain | `prometheus_client` would be preferred in production |
| Immutable versioned images (`1.0.0`, `sha-<commit>`) | Every release is reproducible and rollback is just "run the old tag" | Registry storage grows; add retention policy |
| Smoke test gates every deploy, auto rollback | Bad releases never stay live | Short window where the bad version runs before rollback (no blue/green locally) |
| Rollback swaps the app only, never the DB | Data safety | Requires backward-compatible schema changes |
| Fault injection via build arg (`APEX_FAULT_READY`) | Reproducible "bad release" for demos | Must never be set in real builds (defaults to off) |

## Secrets handling
- No secrets in code, images, Compose file or Git. `secrets/` is git-ignored; `scripts/init_secrets.sh` generates a random password.
- Delivered as a **Docker secret file** (`DB_PASSWORD_FILE`), not an environment variable, so it does not appear in `docker inspect` env output.
- Logs redact fields whose names contain password/secret/token/authorization.
- CI uses only the built-in, short-lived `GITHUB_TOKEN`.
- Cloud: Azure Key Vault (or GitHub/ACA secrets) accessed via **managed identity**; CI authenticates to Azure with **OIDC federation**, so no long-lived keys are stored anywhere.
- Known local trade-off: the secret file is mode 0644 so the non-root container user can read it.

## Least privilege
- Container runs as uid 10001 (verified in CI), read-only root filesystem, `/tmp` tmpfs, all Linux capabilities dropped, `no-new-privileges`.
- Database is on a private network and **not published** to the host; API bound to `127.0.0.1` only.
- Workflow default permission is `contents: read`; only the publish job gets `packages: write`.
- Improvement: separate DB roles (migration owner vs. runtime user with only DML rights).

## Dependency and image scanning
- `pip-audit` fails CI on known-vulnerable Python dependencies.
- `hadolint` lints the Dockerfile.
- `Trivy` scans the built image and fails on fixable HIGH/CRITICAL vulnerabilities.
- Pinned dependency versions; slim base image; multi-stage build keeps build tools out of the runtime image.
- Improvements: pin base image and Actions by digest/SHA, Dependabot/Renovate, SBOM generation and image signing (cosign).

## Cost-aware path to cloud (Azure)
Ordered from cheapest to most resilient. Prices change, so verify with the Azure Pricing Calculator before choosing.

1. **Single small Linux VM running this exact Compose stack.** Lowest cost and zero re-architecture; but a single point of failure and you patch the OS yourself. Good for a pilot.
2. **Recommended: Azure Container Apps (consumption plan) + Azure Database for PostgreSQL Flexible Server (Burstable tier) + Key Vault + managed identity.** Scales to zero when idle, pay per use, managed TLS and revisions (built-in traffic splitting makes rollback a revision switch). Images from GHCR or ACR Basic. Logs to Log Analytics with a daily cap to control cost.
3. **AKS** only when there are many services and a platform team; the cluster overhead is not justified for one API.

Cost controls: budgets and alerts on the resource group, scale-to-zero, smallest DB tier with auto-grow storage, log retention limits, and tagging resources by environment. All infrastructure would be defined in Terraform.

## What I would improve with more time
- Terraform for the Azure path, plus a staging environment with manual approval before production.
- Blue/green or canary releases (Container Apps revisions) instead of in-place replacement.
- Proper DB migrations (Alembic) with expand/contract pattern, automated backups and restore test.
- Integration tests against real PostgreSQL in CI, load test with k6, and Grafana dashboards with Alertmanager routing.
- OpenTelemetry tracing using the existing request IDs.

## Lessons from running it
- **The security gates caught real problems.** pip-audit blocked a vulnerable Flask version on the first CI run, before anything was built.
- **Supply-chain risk in CI is real.** The Trivy action tag I first used had been removed after the March 2026 trivy-action tag-hijacking incident. I moved to the immutable `v0.35.0` release. Next step: pin every third-party action by full commit SHA and let Dependabot propose updates.
- **Follow-up:** GitHub warns that checkout, setup-python and upload-artifact still target Node.js 20; upgrade them to their current major versions.
