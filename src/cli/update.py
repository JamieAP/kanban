"""Update CLI subcommands."""

import os
from pathlib import Path

import click

from .. import db, git
from ..models import Update, UPDATE_STATUSES
from ..exceptions import TaskNotFoundError
from . import pass_context, Context


@click.group()
def update() -> None:
    """Manage task updates."""
    pass


@update.command("create")
@click.argument("task_id", type=int)
@click.argument("status", type=click.Choice(UPDATE_STATUSES))
@click.option("--note", "-n", help="Update note")
@click.option("--repo", type=click.Path(exists=True), help="Repository path for git context")
@pass_context
def create(ctx: Context, task_id: int, status: str, note: str | None, repo: str | None) -> None:
    """Create a status update on a task."""
    with db.get_connection(ctx.db) as conn:
        # Verify task exists
        task_row = conn.execute("SELECT id, reference_repo_path FROM task WHERE id = ? AND deleted_at IS NULL", (task_id,)).fetchone()
        if not task_row:
            raise TaskNotFoundError(task_id)

        # Capture git context from repo path or task's original repo
        repo_path = repo or task_row["reference_repo_path"] or os.getcwd()
        git_ctx = git.capture_context(Path(repo_path))

        cursor = conn.execute(
            """INSERT INTO task_update (task_id, status, note, current_commit, repo_dirty)
            VALUES (?, ?, ?, ?, ?)""",
            (
                task_id,
                status,
                note,
                git_ctx.commit if git_ctx else None,
                git_ctx.dirty if git_ctx else False,
            ),
        )
        conn.commit()
        update_id = cursor.lastrowid

        if ctx.json:
            row = conn.execute("SELECT * FROM task_update WHERE id = ?", (update_id,)).fetchone()
            ctx.output(Update.from_row(row).to_dict())
        else:
            ctx.output(f"Created update {update_id}", f"Created update {update_id}")


@update.command("list")
@click.argument("task_id", type=int)
@pass_context
def list_updates(ctx: Context, task_id: int) -> None:
    """List updates for a task."""
    with db.get_connection(ctx.db) as conn:
        # Verify task exists
        task_row = conn.execute("SELECT id FROM task WHERE id = ? AND deleted_at IS NULL", (task_id,)).fetchone()
        if not task_row:
            raise TaskNotFoundError(task_id)

        rows = conn.execute(
            "SELECT * FROM task_update WHERE task_id = ? AND deleted_at IS NULL ORDER BY created_at DESC",
            (task_id,),
        ).fetchall()
        updates = [Update.from_row(row) for row in rows]

        if ctx.json:
            ctx.output([u.to_dict() for u in updates])
        else:
            if not updates:
                ctx.output("No updates found", "No updates found")
            else:
                for u in updates:
                    note_preview = (u.note[:40] + "...") if u.note and len(u.note) > 40 else (u.note or "")
                    ctx.output("", f"{u.id}\t[{u.status}]\t{u.created_at}\t{note_preview}")
