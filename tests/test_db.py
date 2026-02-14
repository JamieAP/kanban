"""Tests for database module."""

import sqlite3
import pytest

from src.db import get_connection, get_memory_connection, init_db


def test_memory_connection_creates_tables():
    """In-memory connection should create all tables."""
    with get_memory_connection() as conn:
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        table_names = [t[0] for t in tables]

        assert "plan" in table_names
        assert "task" in table_names
        assert "note" in table_names
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


def test_note_requires_text(db_with_task):
    """Note text column should be NOT NULL."""
    with pytest.raises(sqlite3.IntegrityError):
        db_with_task.execute(
            "INSERT INTO note (task_id, text) VALUES (1, NULL)"
        )


def test_linked_doc_requires_exactly_one_parent(db_with_plan):
    """LinkedDoc must have exactly one of plan_id or task_id."""
    # Neither set - should fail
    with pytest.raises(sqlite3.IntegrityError):
        db_with_plan.execute(
            "INSERT INTO linked_doc (path, relevance, content) VALUES ('x', 'y', 'z')"
        )


def test_soft_delete_plan(db_with_task):
    """Soft deleting a plan should set deleted_at."""
    db_with_task.execute("UPDATE plan SET deleted_at = datetime('now') WHERE id = 1")
    db_with_task.commit()

    # Plan still exists but is marked deleted
    plan = db_with_task.execute("SELECT * FROM plan WHERE id = 1").fetchone()
    assert plan is not None
    assert plan["deleted_at"] is not None

    # Filtering by deleted_at IS NULL excludes it
    active_plans = db_with_task.execute("SELECT * FROM plan WHERE deleted_at IS NULL").fetchall()
    assert len(active_plans) == 0


def test_soft_delete_task(db_with_task):
    """Soft deleting a task should set deleted_at."""
    db_with_task.execute(
        "INSERT INTO note (task_id, text) VALUES (1, 'test note')"
    )
    db_with_task.commit()

    db_with_task.execute("UPDATE task SET deleted_at = datetime('now') WHERE id = 1")
    db_with_task.commit()

    # Task still exists but is marked deleted
    task = db_with_task.execute("SELECT * FROM task WHERE id = 1").fetchone()
    assert task is not None
    assert task["deleted_at"] is not None

    # Notes still exist (soft delete doesn't cascade automatically at DB level)
    notes = db_with_task.execute("SELECT * FROM note").fetchall()
    assert len(notes) == 1


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
