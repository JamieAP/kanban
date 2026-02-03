"""Data models for kanban tracker."""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from sqlite3 import Row
from typing import Any


@dataclass
class GitContext:
    """Git repository context captured at a point in time."""

    branch: str | None = None
    commit: str | None = None
    dirty: bool = False
    worktree: str | None = None


@dataclass
class Plan:
    """A top-level plan that contains tasks."""

    id: int | None = None
    name: str = ""
    description: str | None = None
    created_at: datetime | None = None

    @classmethod
    def from_row(cls, row: Row) -> "Plan":
        return cls(
            id=row["id"],
            name=row["name"],
            description=row["description"],
            created_at=datetime.fromisoformat(row["created_at"])
            if row["created_at"]
            else None,
        )

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        if d["created_at"]:
            d["created_at"] = d["created_at"].isoformat()
        return d


@dataclass
class Task:
    """A task belonging to a plan."""

    id: int | None = None
    plan_id: int | None = None
    title: str = ""
    description: str | None = None
    status: str = "todo"
    created_at: datetime | None = None
    cwd: str | None = None
    reference_repo: str | None = None
    reference_repo_path: str | None = None
    reference_repo_branch: str | None = None
    reference_repo_worktree: str | None = None
    current_commit: str | None = None
    repo_dirty: bool = False

    @classmethod
    def from_row(cls, row: Row) -> "Task":
        return cls(
            id=row["id"],
            plan_id=row["plan_id"],
            title=row["title"],
            description=row["description"],
            status=row["status"],
            created_at=datetime.fromisoformat(row["created_at"])
            if row["created_at"]
            else None,
            cwd=row["cwd"],
            reference_repo=row["reference_repo"],
            reference_repo_path=row["reference_repo_path"],
            reference_repo_branch=row["reference_repo_branch"],
            reference_repo_worktree=row["reference_repo_worktree"],
            current_commit=row["current_commit"],
            repo_dirty=bool(row["repo_dirty"]),
        )

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        if d["created_at"]:
            d["created_at"] = d["created_at"].isoformat()
        return d


TASK_STATUSES = ("todo", "in_progress", "done")


@dataclass
class Update:
    """A status update on a task."""

    id: int | None = None
    task_id: int | None = None
    status: str = "continuing"
    note: str | None = None
    created_at: datetime | None = None
    current_commit: str | None = None
    repo_dirty: bool = False

    @classmethod
    def from_row(cls, row: Row) -> "Update":
        return cls(
            id=row["id"],
            task_id=row["task_id"],
            status=row["status"],
            note=row["note"],
            created_at=datetime.fromisoformat(row["created_at"])
            if row["created_at"]
            else None,
            current_commit=row["current_commit"],
            repo_dirty=bool(row["repo_dirty"]),
        )

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        if d["created_at"]:
            d["created_at"] = d["created_at"].isoformat()
        return d


UPDATE_STATUSES = ("continuing", "blocked", "abandoned", "todo", "in_progress", "done")


@dataclass
class LinkedDoc:
    """A document linked to a plan or task with snapshot content."""

    id: int | None = None
    plan_id: int | None = None
    task_id: int | None = None
    path: str = ""
    relevance: str = ""
    content: str = ""
    linked_at: datetime | None = None

    @classmethod
    def from_row(cls, row: Row) -> "LinkedDoc":
        return cls(
            id=row["id"],
            plan_id=row["plan_id"],
            task_id=row["task_id"],
            path=row["path"],
            relevance=row["relevance"],
            content=row["content"],
            linked_at=datetime.fromisoformat(row["linked_at"])
            if row["linked_at"]
            else None,
        )

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        if d["linked_at"]:
            d["linked_at"] = d["linked_at"].isoformat()
        return d
