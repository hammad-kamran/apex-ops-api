"""Automated checks for the Apex Operations API."""
import json
import logging
import os

import pytest

from app import create_app
from app.config import Config, read_secret
from app.logging_setup import JsonFormatter


# 1. Liveness
def test_liveness_returns_ok(client):
    resp = client.get("/health/live")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


# 2. Readiness when the database is reachable
def test_readiness_ok_when_database_up(client):
    resp = client.get("/health/ready")
    assert resp.status_code == 200
    assert resp.get_json()["checks"]["database"] == "up"


# 3. Readiness fails (503) when the database is unreachable
def test_readiness_fails_when_database_down(tmp_path):
    bad = Config(database_url=f"sqlite:///{tmp_path / 'missing-dir' / 'db.sqlite'}")
    resp = create_app(bad).test_client().get("/health/ready")
    assert resp.status_code == 503
    assert resp.get_json()["checks"]["database"] == "down"


# 4. Create and read back a task
def test_create_and_get_task(client):
    created = client.post("/api/v1/tasks", json={"title": "Rotate TLS certificate"})
    assert created.status_code == 201
    task_id = created.get_json()["id"]
    fetched = client.get(f"/api/v1/tasks/{task_id}")
    assert fetched.status_code == 200
    assert fetched.get_json()["title"] == "Rotate TLS certificate"
    assert fetched.get_json()["status"] == "open"


# 5. Input validation
@pytest.mark.parametrize("payload", [{}, {"title": ""}, {"title": "   "}, {"title": "x" * 201}, {"title": 5}])
def test_create_task_rejects_invalid_title(client, payload):
    assert client.post("/api/v1/tasks", json=payload).status_code == 400


# 6. Status transitions are validated
def test_update_status_valid_and_invalid(client):
    task_id = client.post("/api/v1/tasks", json={"title": "Patch base image"}).get_json()["id"]
    ok = client.patch(f"/api/v1/tasks/{task_id}", json={"status": "done"})
    assert ok.status_code == 200 and ok.get_json()["status"] == "done"
    assert client.patch(f"/api/v1/tasks/{task_id}", json={"status": "deleted"}).status_code == 400
    assert client.patch("/api/v1/tasks/9999", json={"status": "done"}).status_code == 404


# 7. Metrics endpoint exposes Prometheus data
def test_metrics_exposed(client):
    client.get("/health/live")
    body = client.get("/metrics").get_data(as_text=True)
    assert 'apex_app_info{version="test-1.0.0"} 1' in body
    assert 'apex_http_requests_total{method="GET",path="/health/live",status="200"}' in body


# 8. Version endpoint reports the deployed build (used by smoke tests and rollback checks)
def test_version_endpoint(client):
    assert client.get("/api/v1/version").get_json() == {"version": "test-1.0.0"}


# 9. Structured logs are valid JSON and redact secret-looking fields
def test_structured_logs_are_json_and_redacted():
    record = logging.LogRecord("apex.api", logging.INFO, __file__, 1, "request completed", None, None)
    record.request_id = "abc123"
    record.db_password = "should-not-leak"
    payload = json.loads(JsonFormatter().format(record))
    assert payload["message"] == "request completed"
    assert payload["request_id"] == "abc123"
    assert payload["db_password"] == "[REDACTED]"


# 10. Secrets are read from a mounted file, not hard-coded
def test_secret_read_from_file(tmp_path, monkeypatch):
    secret_file = tmp_path / "db_password"
    secret_file.write_text("from-file\n")
    monkeypatch.setenv("DB_PASSWORD_FILE", str(secret_file))
    monkeypatch.delenv("DB_PASSWORD", raising=False)
    assert read_secret("DB_PASSWORD") == "from-file"


# 11. Request IDs are propagated for tracing across logs
def test_request_id_header_propagated(client):
    resp = client.get("/health/live", headers={"X-Request-ID": "trace-42"})
    assert resp.headers["X-Request-ID"] == "trace-42"


# 12. INTENTIONAL FAILURE (demo): proves CI blocks the release when a test fails.
#     Skipped by default; enabled with DEMO_FAIL=1 (CI "Run workflow" -> demo_failure).
@pytest.mark.skipif(os.getenv("DEMO_FAIL") != "1", reason="intentional failure demo is disabled")
def test_intentional_failure_blocks_release(client):
    resp = client.get("/api/v1/version")
    assert resp.get_json()["version"] == "this-will-never-match", "Intentional failure: CI must stop here"
