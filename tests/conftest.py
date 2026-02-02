"""Pytest fixtures for kanban tests."""

import pytest
import sqlite3

from kanban.db import init_db, get_memory_connection


@pytest.fixture
def db_conn():
    """In-memory database connection for testing."""
    with get_memory_connection() as conn:
        yield conn


@pytest.fixture
def db_with_plan(db_conn):
    """Database with a test plan."""
    db_conn.execute("INSERT INTO plan (name, description) VALUES (?, ?)", ("Test Plan", "A test plan"))
    db_conn.commit()
    return db_conn


@pytest.fixture
def db_with_task(db_with_plan):
    """Database with a test plan and task."""
    db_with_plan.execute(
        "INSERT INTO task (plan_id, title, description, status) VALUES (?, ?, ?, ?)",
        (1, "Test Task", "A test task", "todo"),
    )
    db_with_plan.commit()
    return db_with_plan


@pytest.fixture
def tmp_db(tmp_path):
    """Temporary database file path."""
    return str(tmp_path / "test.db")
