# AI-use disclosure

AI assistance was permitted for this assessment. This is exactly how I used it.

**Tool:** Claude (Anthropic), via claude.ai.

**What the AI did**
- Proposed the architecture and file structure.
- Drafted the application code, tests, Dockerfile, Compose file, CI workflow, deploy/rollback/drill scripts, monitoring configuration, the architecture diagram, and first drafts of the README, runbook and decision memo.
- Helped me diagnose the issues listed below and suggested fixes.

**What I did myself**
- Set up the environment (WSL2 Ubuntu, Docker Desktop integration, GitHub CLI) and ran every step on my own machine and in GitHub Actions.
- Applied and verified each fix, and reviewed the code and decisions so I can explain them.
- Captured all evidence in `evidence/` from my own runs. No evidence was generated or edited by AI.

**Issues found during my runs and how they were fixed**
1. `psycopg2-binary==2.9.10` had no wheel for Python 3.14 on my machine, so the install failed. Upgraded to 2.9.11.
2. ruff reported UP017 (use `datetime.UTC`) and S108 (`/tmp` usage). Applied the auto-fix for UP017; S108 is intentional (read-only root filesystem with a private tmpfs at `/tmp`) and is documented inline with `noqa`.
3. On the first CI run, pip-audit found a real vulnerability in Flask 3.1.1 (PYSEC-2026-2151). The pipeline blocked the release as designed; upgraded Flask to 3.1.3.
4. The workflow referenced `aquasecurity/trivy-action@0.28.0`, which no longer exists: older tags were removed after the March 2026 trivy-action supply-chain incident. Moved to `v0.35.0`, an immutable release.

**Verification:** every claim in the documentation is backed by a file in `evidence/`.
