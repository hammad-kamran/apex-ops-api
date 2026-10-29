"""Tiny Prometheus text-format exporter (no extra dependency).

Counters live in process memory, so Gunicorn runs a single worker with
threads. See docs/DECISIONS.md for the trade-off.
"""
import threading
from collections import defaultdict


class Metrics:
    def __init__(self, version: str):
        self.version = version
        self._lock = threading.Lock()
        self._requests = defaultdict(int)  # (method, path, status) -> count
        self._duration_sum = defaultdict(float)  # path -> seconds
        self._duration_count = defaultdict(int)  # path -> count
        self.db_up = 0

    def observe_request(self, method: str, path: str, status: int, seconds: float) -> None:
        with self._lock:
            self._requests[(method, path, str(status))] += 1
            self._duration_sum[path] += seconds
            self._duration_count[path] += 1

    def set_db_up(self, up: bool) -> None:
        with self._lock:
            self.db_up = 1 if up else 0

    def render(self) -> str:
        with self._lock:
            lines = [
                "# HELP apex_app_info Application build information.",
                "# TYPE apex_app_info gauge",
                f'apex_app_info{{version="{self.version}"}} 1',
                "# HELP apex_db_up Whether the last database check succeeded (1) or failed (0).",
                "# TYPE apex_db_up gauge",
                f"apex_db_up {self.db_up}",
                "# HELP apex_http_requests_total Total HTTP requests.",
                "# TYPE apex_http_requests_total counter",
            ]
            for (method, path, status), count in sorted(self._requests.items()):
                lines.append(f'apex_http_requests_total{{method="{method}",path="{path}",status="{status}"}} {count}')
            lines += [
                "# HELP apex_http_request_duration_seconds Request latency summary.",
                "# TYPE apex_http_request_duration_seconds summary",
            ]
            for path in sorted(self._duration_count):
                lines.append(f'apex_http_request_duration_seconds_sum{{path="{path}"}} {self._duration_sum[path]:.6f}')
                lines.append(f'apex_http_request_duration_seconds_count{{path="{path}"}} {self._duration_count[path]}')
        return "\n".join(lines) + "\n"
