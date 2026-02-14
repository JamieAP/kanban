"""Note CLI subcommands."""

import os
from pathlib import Path

import click

from .. import db, git
from ..models import Note
from ..exceptions import TaskNotFoundError, NoteNotFoundError
from . import pass_context, Context


@click.group()
def note() -> None:
    """Manage task notes."""
    pass


@note.command("add")
@click.argument("task_id", type=int)
@click.argument("text")
@click.option("--repo", type=click.Path(exists=True), help="Repository path for git context")
@pass_context
def add(ctx: Context, task_id: int, text: str, repo: str | None) -> None:
    """Add a note to a task."""
    with db.get_connection(ctx.db) as conn:
        # Verify task exists
        task_row = conn.execute("SELECT id, reference_repo_path FROM task WHERE id = ? AND deleted_at IS NULL", (task_id,)).fetchone()
        if not task_row:
            raise TaskNotFoundError(task_id)

        # Capture git context from repo path or task's original repo
        repo_path = repo or task_row["reference_repo_path"] or os.getcwd()
        git_ctx = git.capture_context(Path(repo_path))

        cursor = conn.execute(
            """INSERT INTO note (task_id, text, current_commit, repo_dirty)
            VALUES (?, ?, ?, ?)""",
            (
                task_id,
                text,
                git_ctx.commit if git_ctx else None,
                git_ctx.dirty if git_ctx else False,
            ),
        )
        conn.commit()
        note_id = cursor.lastrowid

        if ctx.json:
            row = conn.execute("SELECT * FROM note WHERE id = ?", (note_id,)).fetchone()
            ctx.output(Note.from_row(row).to_dict())
        else:
            ctx.output(f"Added note {note_id}", f"Added note {note_id}")


@note.command("list")
@click.argument("task_id", type=int)
@pass_context
def list_notes(ctx: Context, task_id: int) -> None:
    """List notes for a task."""
    with db.get_connection(ctx.db) as conn:
        # Verify task exists
        task_row = conn.execute("SELECT id FROM task WHERE id = ? AND deleted_at IS NULL", (task_id,)).fetchone()
        if not task_row:
            raise TaskNotFoundError(task_id)

        rows = conn.execute(
            "SELECT * FROM note WHERE task_id = ? AND deleted_at IS NULL ORDER BY created_at DESC",
            (task_id,),
        ).fetchall()
        notes = [Note.from_row(row) for row in rows]

        if ctx.json:
            ctx.output([n.to_dict() for n in notes])
        else:
            if not notes:
                ctx.output("No notes found", "No notes found")
            else:
                for n in notes:
                    text_preview = (n.text[:60] + "...") if len(n.text) > 60 else n.text
                    ctx.output("", f"{n.id}\t{n.created_at}\t{text_preview}")


@note.command("delete")
@click.argument("note_id", type=int)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
@pass_context
def delete(ctx: Context, note_id: int, yes: bool) -> None:
    """Delete a note (soft delete)."""
    with db.get_connection(ctx.db) as conn:
        row = conn.execute("SELECT * FROM note WHERE id = ? AND deleted_at IS NULL", (note_id,)).fetchone()
        if not row:
            raise NoteNotFoundError(note_id)

        if not yes and not ctx.json:
            click.confirm(f"Delete note {note_id}?", abort=True)

        conn.execute("UPDATE note SET deleted_at = datetime('now') WHERE id = ?", (note_id,))
        conn.commit()

        if ctx.json:
            ctx.output({"deleted": note_id})
        else:
            ctx.output(f"Deleted note {note_id}", f"Deleted note {note_id}")
