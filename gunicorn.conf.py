bind = "0.0.0.0:8000"
workers = 1          # single process keeps in-memory metrics consistent
threads = 4          # concurrency via threads instead
timeout = 30
graceful_timeout = 20
worker_tmp_dir = "/tmp"  # noqa: S108 - read-only root FS; /tmp is a private tmpfs
accesslog = None     # the app emits its own structured request logs
errorlog = "-"
