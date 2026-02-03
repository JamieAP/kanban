"""Configuration and path resolution."""

import os
from pathlib import Path

DEFAULT_DB_DIR = Path.home() / ".kanban"
DEFAULT_DB_NAME = "kanban.db"


def get_db_path(override: str | None = None) -> Path:
    """Get database path from override, env var, or default.

    Priority:
    1. Explicit override argument
    2. KANBAN_DB environment variable
    3. Default: ~/.kanban/kanban.db
    """
    if override:
        return Path(override)

    env_path = os.environ.get("KANBAN_DB")
    if env_path:
        return Path(env_path)

    return DEFAULT_DB_DIR / DEFAULT_DB_NAME


def ensure_db_dir(db_path: Path) -> None:
    """Create database directory if it doesn't exist."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
