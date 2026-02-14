"""Task CLI subcommands."""

import os
from pathlib import Path

import click

from .. import db, git
from ..models import Task, Note, TASK_STATUSES
from ..exceptions import PlanNotFoundError, TaskNotFoundError
from . import pass_context, Context


@click.group()
def task() -> None:
    """Manage tasks."""
    pass


@task.command("create")
@click.argument("plan_id", type=int)
@click.argument("title")
@click.option("--description", "-d", help="Task description")
@click.option("--repo", type=click.Path(exists=True), help="Repository path for git context")
@pass_context
def create(ctx: Context, plan_id: int, title: str, description: str | None, repo: str | None) -> None:
    """Create a new task with git context capture."""
    with db.get_connection(ctx.db) as conn:
        # Verify plan exists
        plan_row = conn.execute("SELECT id FROM plan WHERE id = ? AND deleted_at IS NULL", (plan_id,)).fetchone()
        if not plan_row:
            raise PlanNotFoundError(plan_id)

        # Capture context
        cwd = os.getcwd()
        repo_path = Path(repo) if repo else Path(cwd)
        git_ctx = git.capture_context(repo_path)
        repo_name, repo_root = git.get_repo_info(repo_path)

        cursor = conn.execute(
            """INSERT INTO task (
                plan_id, title, description, cwd,
                reference_repo, reference_repo_path, reference_repo_branch,
                reference_repo_worktree, current_commit, repo_dirty
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                plan_id,
                title,
                description,
                cwd,
                repo_name,
                repo_root,
                git_ctx.branch if git_ctx else None,
                git_ctx.worktree if git_ctx else None,
                git_ctx.commit if git_ctx else None,
                git_ctx.dirty if git_ctx else False,
            ),
        )
        conn.commit()
        task_id = cursor.lastrowid

        if ctx.json:
            row = conn.execute("SELECT * FROM task WHERE id = ?", (task_id,)).fetchone()
            ctx.output(Task.from_row(row).to_dict())
        else:
            ctx.output(f"Created task {task_id}", f"Created task {task_id}")


@task.command("list")
@click.option("--plan", "plan_id", type=int, help="Filter by plan ID")
@click.option("--status", type=click.Choice(TASK_STATUSES), help="Filter by status")
@click.option("--notes", "-n", is_flag=True, help="Include notes for each task")
@pass_context
def list_tasks(ctx: Context, plan_id: int | None, status: str | None, notes: bool) -> None:
    """List tasks."""
    with db.get_connection(ctx.db) as conn:
        query = "SELECT * FROM task WHERE deleted_at IS NULL"
        params: list = []

        if plan_id is not None:
            query += " AND plan_id = ?"
            params.append(plan_id)
        if status is not None:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY created_at DESC"
        rows = conn.execute(query, params).fetchall()
        tasks = [Task.from_row(row) for row in rows]

        # Fetch notes for each task if requested
        task_notes: dict[int, list[Note]] = {}
        if notes:
            for t in tasks:
                if t.id is not None:
                    note_rows = conn.execute(
                        "SELECT * FROM note WHERE task_id = ? AND deleted_at IS NULL ORDER BY created_at DESC",
                        (t.id,),
                    ).fetchall()
                    task_notes[t.id] = [Note.from_row(row) for row in note_rows]

        if ctx.json:
            if notes:
                output = []
                for t in tasks:
                    task_dict = t.to_dict()
                    task_dict["notes"] = [n.to_dict() for n in task_notes.get(t.id or 0, [])]
                    output.append(task_dict)
                ctx.output(output)
            else:
                ctx.output([t.to_dict() for t in tasks])
        else:
            if not tasks:
                ctx.output("No tasks found", "No tasks found")
            else:
                for t in tasks:
                    ctx.output("", f"{t.id}\t[{t.status}]\t{t.title}")
                    if notes and t.id is not None:
                        for n in task_notes.get(t.id, []):
                            text_preview = (n.text[:50] + "...") if len(n.text) > 50 else n.text
                            ctx.output("", f"  └─ {n.id}\t{n.created_at}\t{text_preview}")


@task.command("show")
@click.argument("task_id", type=int)
@pass_context
def show(ctx: Context, task_id: int) -> None:
    """Show task details."""
    with db.get_connection(ctx.db) as conn:
        row = conn.execute("SELECT * FROM task WHERE id = ? AND deleted_at IS NULL", (task_id,)).fetchone()
        if not row:
            raise TaskNotFoundError(task_id)

        task_obj = Task.from_row(row)

        if ctx.json:
            ctx.output(task_obj.to_dict())
        else:
            ctx.output("", f"ID: {task_obj.id}")
            ctx.output("", f"Plan: {task_obj.plan_id}")
            ctx.output("", f"Title: {task_obj.title}")
            ctx.output("", f"Status: {task_obj.status}")
            if task_obj.description:
                ctx.output("", f"Description: {task_obj.description}")
            ctx.output("", f"Created: {task_obj.created_at}")
            if task_obj.reference_repo:
                ctx.output("", f"Repo: {task_obj.reference_repo}")
                ctx.output("", f"  Path: {task_obj.reference_repo_path}")
                ctx.output("", f"  Branch: {task_obj.reference_repo_branch}")
                ctx.output("", f"  Commit: {task_obj.current_commit}")
                ctx.output("", f"  Dirty: {task_obj.repo_dirty}")
                if task_obj.reference_repo_worktree:
                    ctx.output("", f"  Worktree: {task_obj.reference_repo_worktree}")


@task.command("set")
@click.argument("task_id", type=int)
@click.option("--title", "-t", help="New title")
@click.option("--description", "-d", help="New description")
@click.option("--status", "-s", type=click.Choice(TASK_STATUSES), help="New status")
@pass_context
def set_task(ctx: Context, task_id: int, title: str | None, description: str | None, status: str | None) -> None:
    """Set task fields."""
    with db.get_connection(ctx.db) as conn:
        row = conn.execute("SELECT * FROM task WHERE id = ? AND deleted_at IS NULL", (task_id,)).fetchone()
        if not row:
            raise TaskNotFoundError(task_id)

        updates = []
        params = []
        if title is not None:
            updates.append("title = ?")
            params.append(title)
        if description is not None:
            updates.append("description = ?")
            params.append(description)
        if status is not None:
            updates.append("status = ?")
            params.append(status)

        if updates:
            params.append(task_id)
            conn.execute(f"UPDATE task SET {', '.join(updates)} WHERE id = ?", params)

        conn.commit()

        row = conn.execute("SELECT * FROM task WHERE id = ?", (task_id,)).fetchone()
        task_obj = Task.from_row(row)

        if ctx.json:
            ctx.output(task_obj.to_dict())
        else:
            ctx.output(f"Updated task {task_id}", f"Updated task {task_id}")


# --- Status shortcuts ---


@task.command("start")
@click.argument("task_id", type=int)
@pass_context
def start(ctx: Context, task_id: int) -> None:
    """Set task status to in_progress."""
    _set_status(ctx, task_id, "in_progress")


@task.command("done")
@click.argument("task_id", type=int)
@pass_context
def done(ctx: Context, task_id: int) -> None:
    """Set task status to done."""
    _set_status(ctx, task_id, "done")


@task.command("block")
@click.argument("task_id", type=int)
@click.argument("reason", required=False)
@pass_context
def block(ctx: Context, task_id: int, reason: str | None) -> None:
    """Set task status to blocked, optionally with a note."""
    with db.get_connection(ctx.db) as conn:
        row = conn.execute("SELECT * FROM task WHERE id = ? AND deleted_at IS NULL", (task_id,)).fetchone()
        if not row:
            raise TaskNotFoundError(task_id)

        conn.execute("UPDATE task SET status = 'blocked' WHERE id = ?", (task_id,))

        # Add note if reason provided
        if reason:
            repo_path = row["reference_repo_path"] or os.getcwd()
            git_ctx = git.capture_context(Path(repo_path))
            conn.execute(
                "INSERT INTO note (task_id, text, current_commit, repo_dirty) VALUES (?, ?, ?, ?)",
                (task_id, reason, git_ctx.commit if git_ctx else None, git_ctx.dirty if git_ctx else False),
            )

        conn.commit()

        if ctx.json:
            row = conn.execute("SELECT * FROM task WHERE id = ?", (task_id,)).fetchone()
            ctx.output(Task.from_row(row).to_dict())
        else:
            ctx.output(f"Blocked task {task_id}", f"Blocked task {task_id}")


@task.command("todo")
@click.argument("task_id", type=int)
@pass_context
def todo(ctx: Context, task_id: int) -> None:
    """Set task status to todo."""
    _set_status(ctx, task_id, "todo")


def _set_status(ctx: Context, task_id: int, status: str) -> None:
    """Helper to set task status."""
    with db.get_connection(ctx.db) as conn:
        row = conn.execute("SELECT * FROM task WHERE id = ? AND deleted_at IS NULL", (task_id,)).fetchone()
        if not row:
            raise TaskNotFoundError(task_id)

        conn.execute("UPDATE task SET status = ? WHERE id = ?", (status, task_id))
        conn.commit()

        if ctx.json:
            row = conn.execute("SELECT * FROM task WHERE id = ?", (task_id,)).fetchone()
            ctx.output(Task.from_row(row).to_dict())
        else:
            ctx.output(f"Task {task_id} → {status}", f"Task {task_id} → {status}")


@task.command("delete")
@click.argument("task_id", type=int)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
@pass_context
def delete(ctx: Context, task_id: int, yes: bool) -> None:
    """Delete a task and all its notes (soft delete)."""
    with db.get_connection(ctx.db) as conn:
        row = conn.execute("SELECT * FROM task WHERE id = ? AND deleted_at IS NULL", (task_id,)).fetchone()
        if not row:
            raise TaskNotFoundError(task_id)

        task_obj = Task.from_row(row)

        if not yes and not ctx.json:
            click.confirm(f"Delete task '{task_obj.title}' and all its notes?", abort=True)

        # Soft delete task and cascade to children
        conn.execute("UPDATE task SET deleted_at = datetime('now') WHERE id = ?", (task_id,))
        conn.execute("UPDATE note SET deleted_at = datetime('now') WHERE task_id = ? AND deleted_at IS NULL", (task_id,))
        conn.execute("UPDATE linked_doc SET deleted_at = datetime('now') WHERE task_id = ? AND deleted_at IS NULL", (task_id,))
        conn.commit()

        if ctx.json:
            ctx.output({"deleted": task_id})
        else:
            ctx.output(f"Deleted task {task_id}", f"Deleted task {task_id}")
