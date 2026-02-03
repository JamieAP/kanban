"""Doc CLI subcommands."""

from pathlib import Path

import click

from .. import db
from ..models import LinkedDoc
from ..exceptions import (
    PlanNotFoundError,
    TaskNotFoundError,
    DocNotFoundError,
    FileNotFoundError as KanbanFileNotFoundError,
    FileUnreadableError,
    FileTooLargeError,
    DuplicateDocError,
)
from . import pass_context, Context


MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB hard limit
WARN_FILE_SIZE = 1 * 1024 * 1024  # 1MB warning threshold


def _read_file_content(path: Path, force: bool = False) -> str:
    """Read file content with validation.

    Args:
        path: Absolute path to file
        force: Allow files >1MB (up to 10MB)

    Returns:
        File content as string

    Raises:
        KanbanFileNotFoundError: File doesn't exist
        FileUnreadableError: Can't read file (binary, permission, etc.)
        FileTooLargeError: File exceeds size limit
    """
    if not path.exists():
        raise KanbanFileNotFoundError(str(path))

    # Resolve symlinks
    path = path.resolve()

    size = path.stat().st_size
    if size > MAX_FILE_SIZE:
        raise FileTooLargeError(str(path), size, MAX_FILE_SIZE)
    if size > WARN_FILE_SIZE and not force:
        raise FileTooLargeError(str(path), size, WARN_FILE_SIZE)

    # Try to read as text
    for encoding in ("utf-8", "latin-1"):
        try:
            content = path.read_text(encoding=encoding)
            # Check for binary content (null bytes)
            if "\x00" in content:
                raise FileUnreadableError(str(path), "Binary file")
            return content
        except UnicodeDecodeError:
            continue

    raise FileUnreadableError(str(path), "Unable to decode as text")


@click.group()
def doc() -> None:
    """Manage linked documents."""
    pass


@doc.command("link")
@click.option("--plan", "plan_id", type=int, help="Link to plan")
@click.option("--task", "task_id", type=int, help="Link to task")
@click.argument("path", type=click.Path())
@click.argument("relevance")
@click.option("--force", "-f", is_flag=True, help="Allow files >1MB")
@pass_context
def link(ctx: Context, plan_id: int | None, task_id: int | None, path: str, relevance: str, force: bool) -> None:
    """Link a document to a plan or task."""
    # Validate exactly one target
    if (plan_id is None) == (task_id is None):
        raise click.UsageError("Specify exactly one of --plan or --task")

    # Resolve to absolute path
    file_path = Path(path).resolve()
    content = _read_file_content(file_path, force=force)

    with db.get_connection(ctx.db) as conn:
        # Verify target exists
        if plan_id is not None:
            row = conn.execute("SELECT id FROM plan WHERE id = ? AND deleted_at IS NULL", (plan_id,)).fetchone()
            if not row:
                raise PlanNotFoundError(plan_id)
        else:
            row = conn.execute("SELECT id FROM task WHERE id = ? AND deleted_at IS NULL", (task_id,)).fetchone()
            if not row:
                raise TaskNotFoundError(task_id)

        # Check for duplicate (only among non-deleted docs)
        existing = conn.execute(
            "SELECT id FROM linked_doc WHERE path = ? AND (plan_id = ? OR task_id = ?) AND deleted_at IS NULL",
            (str(file_path), plan_id, task_id),
        ).fetchone()
        if existing:
            raise DuplicateDocError(str(file_path))

        cursor = conn.execute(
            "INSERT INTO linked_doc (plan_id, task_id, path, relevance, content) VALUES (?, ?, ?, ?, ?)",
            (plan_id, task_id, str(file_path), relevance, content),
        )
        conn.commit()
        doc_id = cursor.lastrowid

        if ctx.json:
            row = conn.execute("SELECT * FROM linked_doc WHERE id = ?", (doc_id,)).fetchone()
            doc_obj = LinkedDoc.from_row(row)
            # Don't include full content in JSON output by default
            d = doc_obj.to_dict()
            d["content_length"] = len(d.pop("content"))
            ctx.output(d)
        else:
            ctx.output(f"Linked doc {doc_id}", f"Linked doc {doc_id}")


@doc.command("list")
@click.option("--plan", "plan_id", type=int, help="List docs for plan")
@click.option("--task", "task_id", type=int, help="List docs for task")
@pass_context
def list_docs(ctx: Context, plan_id: int | None, task_id: int | None) -> None:
    """List linked documents."""
    if (plan_id is None) == (task_id is None):
        raise click.UsageError("Specify exactly one of --plan or --task")

    with db.get_connection(ctx.db) as conn:
        if plan_id is not None:
            rows = conn.execute(
                "SELECT * FROM linked_doc WHERE plan_id = ? AND deleted_at IS NULL ORDER BY linked_at DESC",
                (plan_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM linked_doc WHERE task_id = ? AND deleted_at IS NULL ORDER BY linked_at DESC",
                (task_id,),
            ).fetchall()

        docs = [LinkedDoc.from_row(row) for row in rows]

        if ctx.json:
            output = []
            for d in docs:
                dd = d.to_dict()
                dd["content_length"] = len(dd.pop("content"))
                output.append(dd)
            ctx.output(output)
        else:
            if not docs:
                ctx.output("No docs found", "No docs found")
            else:
                for d in docs:
                    ctx.output("", f"{d.id}\t{d.path}\t{d.relevance[:40]}")


@doc.command("show")
@click.argument("doc_id", type=int)
@click.option("--content", "-c", is_flag=True, help="Show full content")
@pass_context
def show(ctx: Context, doc_id: int, content: bool) -> None:
    """Show document details."""
    with db.get_connection(ctx.db) as conn:
        row = conn.execute("SELECT * FROM linked_doc WHERE id = ? AND deleted_at IS NULL", (doc_id,)).fetchone()
        if not row:
            raise DocNotFoundError(doc_id)

        doc_obj = LinkedDoc.from_row(row)

        if ctx.json:
            d = doc_obj.to_dict()
            if not content:
                d["content_length"] = len(d.pop("content"))
            ctx.output(d)
        else:
            ctx.output("", f"ID: {doc_obj.id}")
            ctx.output("", f"Path: {doc_obj.path}")
            ctx.output("", f"Relevance: {doc_obj.relevance}")
            ctx.output("", f"Linked: {doc_obj.linked_at}")
            ctx.output("", f"Content length: {len(doc_obj.content)} bytes")
            if content:
                ctx.output("", "--- Content ---")
                ctx.output("", doc_obj.content)


@doc.command("unlink")
@click.argument("doc_id", type=int)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
@pass_context
def unlink(ctx: Context, doc_id: int, yes: bool) -> None:
    """Remove a linked document (soft delete)."""
    with db.get_connection(ctx.db) as conn:
        row = conn.execute("SELECT * FROM linked_doc WHERE id = ? AND deleted_at IS NULL", (doc_id,)).fetchone()
        if not row:
            raise DocNotFoundError(doc_id)

        doc_obj = LinkedDoc.from_row(row)

        if not yes and not ctx.json:
            click.confirm(f"Unlink '{doc_obj.path}'?", abort=True)

        conn.execute("UPDATE linked_doc SET deleted_at = datetime('now') WHERE id = ?", (doc_id,))
        conn.commit()

        if ctx.json:
            ctx.output({"unlinked": doc_id})
        else:
            ctx.output(f"Unlinked doc {doc_id}", f"Unlinked doc {doc_id}")
