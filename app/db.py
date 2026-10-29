"""Minimal data access layer. PostgreSQL in Compose, SQLite in unit tests."""
import sqlite3
from datetime import UTC, datetime

from .config import Config

VALID_STATUSES = ("open", "in_progress", "done")


class DatabaseError(Exception):
    """Raised when the database cannot be reached or a query fails."""


class Database:
    def __init__(self, config: Config):
        self.config = config
        self.kind = config.database_kind
        self._schema_ready = False

    # -- connection handling -------------------------------------------------
    def _connect(self):
        try:
            if self.kind == "sqlite":
                return sqlite3.connect(self.config.database_url.removeprefix("sqlite:///"), timeout=3)
            import psycopg2  # imported lazily so unit tests don't need it

            return psycopg2.connect(
                host=self.config.db_host,
                port=self.config.db_port,
                dbname=self.config.db_name,
                user=self.config.db_user,
                password=self.config.db_password,
                connect_timeout=3,
            )
        except Exception as exc:  # noqa: BLE001 - normalise driver errors
            raise DatabaseError(f"connection failed: {type(exc).__name__}") from exc

    def _run(self, sql: str, params: tuple = (), fetch: str | None = None):
        if self.kind == "sqlite":
            sql = sql.replace("%s", "?")
        conn = self._connect()
        try:
            cur = conn.cursor()
            cur.execute(sql, params)
            result = None
            if fetch == "one":
                result = cur.fetchone()
            elif fetch == "all":
                result = cur.fetchall()
            conn.commit()
            return result
        except Exception as exc:  # noqa: BLE001
            raise DatabaseError(f"query failed: {type(exc).__name__}") from exc
        finally:
            conn.close()

    # -- schema ----------------------------------------------------------------
    def ensure_schema(self) -> None:
        if self._schema_ready:
            return
        id_col = "INTEGER PRIMARY KEY AUTOINCREMENT" if self.kind == "sqlite" else "SERIAL PRIMARY KEY"
        self._run(
            f"""CREATE TABLE IF NOT EXISTS tasks (
                    id {id_col},
                    title TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'open',
                    created_at TEXT NOT NULL
                )"""
        )
        self._schema_ready = True

    # -- health ----------------------------------------------------------------
    def ping(self) -> bool:
        try:
            self._run("SELECT 1", fetch="one")
            self.ensure_schema()
            return True
        except DatabaseError:
            self._schema_ready = False
            return False

    # -- tasks -----------------------------------------------------------------
    @staticmethod
    def _row(row) -> dict:
        return {"id": row[0], "title": row[1], "status": row[2], "created_at": row[3]}

    def list_tasks(self) -> list[dict]:
        self.ensure_schema()
        rows = self._run("SELECT id, title, status, created_at FROM tasks ORDER BY id", fetch="all")
        return [self._row(r) for r in rows]

    def create_task(self, title: str) -> dict:
        self.ensure_schema()
        now = datetime.now(UTC).isoformat()
        if self.kind == "sqlite":
            self._run("INSERT INTO tasks (title, status, created_at) VALUES (%s, 'open', %s)", (title, now))
            row = self._run("SELECT id, title, status, created_at FROM tasks ORDER BY id DESC LIMIT 1", fetch="one")
        else:
            row = self._run(
                "INSERT INTO tasks (title, status, created_at) VALUES (%s, 'open', %s) "
                "RETURNING id, title, status, created_at",
                (title, now),
                fetch="one",
            )
        return self._row(row)

    def get_task(self, task_id: int) -> dict | None:
        self.ensure_schema()
        row = self._run("SELECT id, title, status, created_at FROM tasks WHERE id = %s", (task_id,), fetch="one")
        return self._row(row) if row else None

    def update_status(self, task_id: int, status: str) -> dict | None:
        self.ensure_schema()
        self._run("UPDATE tasks SET status = %s WHERE id = %s", (status, task_id))
        return self.get_task(task_id)
