"""Configuration loaded from environment variables.

Secrets are never hard-coded. A secret can be supplied as <NAME>_FILE
(preferred: a mounted file, e.g. a Docker secret) or as <NAME> directly.
"""
import os
from dataclasses import dataclass


def read_secret(name: str) -> str | None:
    file_path = os.getenv(f"{name}_FILE")
    if file_path:
        with open(file_path, encoding="utf-8") as fh:
            return fh.read().strip()
    return os.getenv(name)


@dataclass(frozen=True)
class Config:
    app_version: str = "dev"
    log_level: str = "INFO"
    database_url: str | None = None  # only "sqlite:///path" is supported (used by tests)
    db_host: str = "db"
    db_port: int = 5432
    db_name: str = "apex_ops"
    db_user: str = "apex"
    db_password: str | None = None
    fault_ready: bool = False  # fault injection for the bad-release demo only

    @property
    def database_kind(self) -> str:
        return "sqlite" if (self.database_url or "").startswith("sqlite:///") else "postgres"

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            app_version=os.getenv("APP_VERSION", "dev"),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
            database_url=os.getenv("DATABASE_URL"),
            db_host=os.getenv("DB_HOST", "db"),
            db_port=int(os.getenv("DB_PORT", "5432")),
            db_name=os.getenv("DB_NAME", "apex_ops"),
            db_user=os.getenv("DB_USER", "apex"),
            db_password=read_secret("DB_PASSWORD"),
            fault_ready=os.getenv("APEX_FAULT_READY", "0") == "1",
        )
