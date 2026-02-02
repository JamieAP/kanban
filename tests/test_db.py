"""Tests for database module."""

import sqlite3
import pytest

from kanban.db import get_connection, get_memory_connection, init_db


def test_memory_connection_creates_tables():
    """In-memory connection should create all tables."""
    with get_memory_connection() as conn:
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        table_names = [t[0] for t in tables]

        assert "plan" in table_names
        assert "task" in table_names
        assert "task_update" in table_names
        assert "linked_doc" in table_names


def test_foreign_keys_enabled(db_conn):
    """Foreign keys should be enabled."""
    result = db_conn.execute("PRAGMA foreign_keys").fetchone()
    assert result[0] == 1


def test_task_status_check_constraint(db_with_plan):
    """Task status should be constrained to valid values."""
    with pytest.raises(sqlite3.IntegrityError):
        db_with_plan.execute(
            "INSERT INTO task (plan_id, title, status) VALUES (1, 'Bad', 'invalid')"
        )


def test_update_status_check_constraint(db_with_task):
    """Update status should be constrained to valid values."""
    with pytest.raises(sqlite3.IntegrityError):
        db_with_task.execute(
            "INSERT INTO task_update (task_id, status) VALUES (1, 'invalid')"
        )


def test_linked_doc_requires_exactly_one_parent(db_with_plan):
    """LinkedDoc must have exactly one of plan_id or task_id."""
    # Neither set - should fail
    with pytest.raises(sqlite3.IntegrityError):
        db_with_plan.execute(
            "INSERT INTO linked_doc (path, relevance, content) VALUES ('x', 'y', 'z')"
        )


def test_cascade_delete_plan(db_with_task):
    """Deleting a plan should cascade to tasks."""
    db_with_task.execute("DELETE FROM plan WHERE id = 1")
    db_with_task.commit()

    tasks = db_with_task.execute("SELECT * FROM task").fetchall()
    assert len(tasks) == 0


def test_cascade_delete_task(db_with_task):
    """Deleting a task should cascade to updates."""
    db_with_task.execute(
        "INSERT INTO task_update (task_id, status, note) VALUES (1, 'continuing', 'test')"
    )
    db_with_task.commit()

    db_with_task.execute("DELETE FROM task WHERE id = 1")
    db_with_task.commit()

    updates = db_with_task.execute("SELECT * FROM task_update").fetchall()
    assert len(updates) == 0


def test_file_connection(tmp_db):
    """File-based connection should work."""
    with get_connection(tmp_db) as conn:
        conn.execute("INSERT INTO plan (name) VALUES ('Test')")
        conn.commit()

    # Reconnect and verify
    with get_connection(tmp_db) as conn:
        plans = conn.execute("SELECT * FROM plan").fetchall()
        assert len(plans) == 1
        assert plans[0]["name"] == "Test"
