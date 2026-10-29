"""HTTP endpoints."""
from flask import Flask, Response, jsonify, request

from .db import VALID_STATUSES


def register_routes(app: Flask) -> None:
    db = app.extensions["db"]
    metrics = app.extensions["metrics"]
    config = app.config["APEX"]

    @app.get("/health/live")
    def live():
        # Liveness: the process is up. No dependency checks, so a database
        # outage does not trigger container restart loops.
        return jsonify(status="ok")

    @app.get("/health/ready")
    def ready():
        # Readiness: can we actually serve traffic (database reachable)?
        db_ok = db.ping()
        metrics.set_db_up(db_ok)
        if config.fault_ready:
            return jsonify(status="unavailable", checks={"fault_injection": "enabled"}), 503
        if not db_ok:
            return jsonify(status="unavailable", checks={"database": "down"}), 503
        return jsonify(status="ready", checks={"database": "up"})

    @app.get("/metrics")
    def prometheus_metrics():
        return Response(metrics.render(), mimetype="text/plain; version=0.0.4")

    @app.get("/api/v1/version")
    def version():
        return jsonify(version=config.app_version)

    @app.get("/api/v1/tasks")
    def list_tasks():
        return jsonify(tasks=db.list_tasks())

    @app.post("/api/v1/tasks")
    def create_task():
        body = request.get_json(silent=True) or {}
        title = body.get("title")
        if not isinstance(title, str) or not title.strip() or len(title) > 200:
            return jsonify(error="title is required (1-200 characters)"), 400
        return jsonify(db.create_task(title.strip())), 201

    @app.get("/api/v1/tasks/<int:task_id>")
    def get_task(task_id: int):
        task = db.get_task(task_id)
        return (jsonify(task), 200) if task else (jsonify(error="not found"), 404)

    @app.patch("/api/v1/tasks/<int:task_id>")
    def update_task(task_id: int):
        body = request.get_json(silent=True) or {}
        status = body.get("status")
        if status not in VALID_STATUSES:
            return jsonify(error=f"status must be one of {list(VALID_STATUSES)}"), 400
        task = db.update_status(task_id, status)
        return (jsonify(task), 200) if task else (jsonify(error="not found"), 404)
