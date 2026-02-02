"""Database connection and schema management."""

import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from .config import ensure_db_dir, get_db_path

SCHEMA = """
CREATE TABLE IF NOT EXISTS plan (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS task (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id INTEGER NOT NULL REFERENCES plan(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'todo' CHECK (status IN ('todo', 'in_progress', 'done')),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    cwd TEXT,
    reference_repo TEXT,
    reference_repo_path TEXT,
    reference_repo_branch TEXT,
    reference_repo_worktree TEXT,
    current_commit TEXT,
    repo_dirty INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS task_update (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL REFERENCES task(id) ON DELETE CASCADE,
    status TEXT NOT NULL CHECK (status IN ('continuing', 'blocked', 'abandoned')),
    note TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    current_commit TEXT,
    repo_dirty INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS linked_doc (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id INTEGER REFERENCES plan(id) ON DELETE CASCADE,
    task_id INTEGER REFERENCES task(id) ON DELETE CASCADE,
    path TEXT NOT NULL,
    relevance TEXT NOT NULL,
    content TEXT NOT NULL,
    linked_at TEXT NOT NULL DEFAULT (datetime('now')),
    CHECK ((plan_id IS NULL) != (task_id IS NULL))
);

CREATE INDEX IF NOT EXISTS idx_task_plan_id ON task(plan_id);
CREATE INDEX IF NOT EXISTS idx_task_status ON task(status);
CREATE INDEX IF NOT EXISTS idx_task_update_task_id ON task_update(task_id);
CREATE INDEX IF NOT EXISTS idx_linked_doc_plan_id ON linked_doc(plan_id);
CREATE INDEX IF NOT EXISTS idx_linked_doc_task_id ON linked_doc(task_id);
"""

MAX_RETRIES = 3
RETRY_DELAY = 0.1  # seconds


def _execute_with_retry(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> sqlite3.Cursor:
    """Execute SQL with retry on SQLITE_BUSY."""
    for attempt in range(MAX_RETRIES):
        try:
            return conn.execute(sql, params)
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e) and attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
            else:
                raise
    raise sqlite3.OperationalError("Database locked after retries")


def init_db(conn: sqlite3.Connection) -> None:
    """Initialize database schema."""
    conn.executescript(SCHEMA)
    conn.commit()


@contextmanager
def get_connection(db_path: Path | str | None = None) -> Generator[sqlite3.Connection, None, None]:
    """Get a database connection with proper settings.

    Args:
        db_path: Optional path override. Uses config resolution if None.

    Yields:
        Configured SQLite connection.
    """
    path = get_db_path(str(db_path) if db_path else None)
    ensure_db_dir(path)

    conn = sqlite3.connect(str(path), timeout=10.0)
    conn.row_factory = sqlite3.Row

    try:
        # Enable foreign keys and WAL mode
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")

        # Initialize schema if needed
        init_db(conn)

        yield conn
    finally:
        conn.close()


@contextmanager
def get_memory_connection() -> Generator[sqlite3.Connection, None, None]:
    """Get an in-memory database connection for testing."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row

    try:
        conn.execute("PRAGMA foreign_keys = ON")
        init_db(conn)
        yield conn
    finally:
        conn.close()
