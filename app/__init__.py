"""Apex Operations API: a small task-tracking service used to demonstrate
a reliable path from commit to release."""
import logging
import time
import uuid

from flask import Flask, g, jsonify, request

from .config import Config
from .db import Database, DatabaseError
from .logging_setup import configure_logging
from .metrics import Metrics
from .routes import register_routes

log = logging.getLogger("apex.api")


def create_app(config: Config | None = None) -> Flask:
    config = config or Config.from_env()
    configure_logging(config.log_level)

    app = Flask(__name__)
    app.config["APEX"] = config
    app.extensions["db"] = Database(config)
    app.extensions["metrics"] = Metrics(version=config.app_version)

    @app.before_request
    def _start_request():
        g.start = time.perf_counter()
        incoming = request.headers.get("X-Request-ID", "")
        # Accept a caller-supplied ID only if it looks sane; never trust raw input.
        g.request_id = incoming if 0 < len(incoming) <= 64 and incoming.isprintable() else uuid.uuid4().hex

    @app.after_request
    def _finish_request(response):
        duration = time.perf_counter() - g.get("start", time.perf_counter())
        route = request.url_rule.rule if request.url_rule else "unmatched"
        app.extensions["metrics"].observe_request(request.method, route, response.status_code, duration)
        response.headers["X-Request-ID"] = g.get("request_id", "")
        if route != "/metrics":
            log.info(
                "request completed",
                extra={
                    "request_id": g.get("request_id"),
                    "method": request.method,
                    "path": route,
                    "status": response.status_code,
                    "duration_ms": round(duration * 1000, 2),
                },
            )
        return response

    @app.errorhandler(DatabaseError)
    def _db_error(err):
        log.error("database error", extra={"request_id": g.get("request_id"), "error": str(err)})
        return jsonify(error="database unavailable", request_id=g.get("request_id")), 503

    @app.errorhandler(404)
    def _not_found(_err):
        return jsonify(error="not found"), 404

    @app.errorhandler(500)
    def _internal(_err):
        log.exception("unhandled error", extra={"request_id": g.get("request_id")})
        return jsonify(error="internal error", request_id=g.get("request_id")), 500

    register_routes(app)
    log.info("application started", extra={"version": config.app_version, "database": config.database_kind})
    return app
