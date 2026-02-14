"""CLI entry point for kanban tracker."""

import sys
import json as json_module
import click

from ..exceptions import KanbanError


class Context:
    """CLI context holding global options."""

    def __init__(self, db: str | None = None, json: bool = False, quiet: bool = False):
        self.db = db
        self.json = json
        self.quiet = quiet

    def output(self, data: dict | list | str, message: str | None = None) -> None:
        """Output data in appropriate format."""
        if self.json:
            if isinstance(data, str):
                click.echo(json_module.dumps({"message": data}))
            else:
                click.echo(json_module.dumps(data, indent=2, default=str))
        elif not self.quiet:
            if message:
                click.echo(message)
            elif isinstance(data, str):
                click.echo(data)

    def error(self, message: str) -> None:
        """Output error message."""
        if self.json:
            click.echo(json_module.dumps({"error": message}), err=True)
        else:
            click.echo(f"Error: {message}", err=True)


pass_context = click.make_pass_decorator(Context, ensure=True)


class KanbanGroup(click.Group):
    """Click group with exception handling."""

    def invoke(self, ctx: click.Context) -> None:
        try:
            return super().invoke(ctx)
        except KanbanError as e:
            if ctx.obj:
                ctx.obj.error(str(e))
            else:
                click.echo(f"Error: {e}", err=True)
            ctx.exit(1)


@click.group(cls=KanbanGroup)
@click.option("--db", envvar="KANBAN_DB", help="Database path (default: ~/.kanban/kanban.db)")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
@click.option("--quiet", "-q", is_flag=True, help="Suppress non-essential output")
@click.pass_context
def main(ctx: click.Context, db: str | None, json_output: bool, quiet: bool) -> None:
    """Kanban task tracker with git context capture."""
    ctx.obj = Context(db=db, json=json_output, quiet=quiet)


def handle_errors(func):
    """Decorator to handle KanbanError exceptions."""
    @click.pass_context
    def wrapper(ctx: click.Context, *args, **kwargs):
        try:
            return ctx.invoke(func, *args, **kwargs)
        except KanbanError as e:
            ctx.obj.error(str(e))
            sys.exit(1)
    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper


# Import and register subcommands
from . import plan, task, note, doc
from .tui import tui
from .. import db
from ..models import Plan, Task, Note

main.add_command(plan.plan)
main.add_command(task.task)
main.add_command(note.note)
main.add_command(doc.doc)
main.add_command(tui)


@main.command("tree")
@click.option("--plan", "plan_id", type=int, help="Show only a specific plan")
@click.option("--all", "-a", "show_done", is_flag=True, help="Include done tasks")
@pass_context
def tree_view(ctx: Context, plan_id: int | None, show_done: bool) -> None:
    """Show plans, tasks, and notes as a tree.

    Tasks grouped by status (in_progress, blocked, todo, done) and sorted by last note within each group.
    Done tasks are hidden by default; use -a to show them.
    """
    with db.get_connection(ctx.db) as conn:
        # Get plans
        if plan_id:
            plan_rows = conn.execute(
                "SELECT * FROM plan WHERE id = ? AND deleted_at IS NULL", (plan_id,)
            ).fetchall()
        else:
            plan_rows = conn.execute(
                "SELECT * FROM plan WHERE deleted_at IS NULL ORDER BY created_at DESC"
            ).fetchall()

        if not plan_rows:
            ctx.output("No plans found", "No plans found")
            return

        plans = [Plan.from_row(row) for row in plan_rows]

        # Status display order
        status_order = ["in_progress", "blocked", "todo", "done"] if show_done else ["in_progress", "blocked", "todo"]

        def get_tasks_grouped(plan_id: int) -> list[Task]:
            """Get tasks grouped by status, sorted by last note within each group."""
            # Query with last activity time
            task_rows = conn.execute(
                """SELECT t.*,
                          COALESCE(
                              (SELECT MAX(created_at) FROM note WHERE task_id = t.id AND deleted_at IS NULL),
                              t.created_at
                          ) as last_activity
                   FROM task t
                   WHERE t.plan_id = ? AND t.deleted_at IS NULL
                   ORDER BY last_activity DESC""",
                (plan_id,),
            ).fetchall()

            tasks_by_status: dict[str, list[Task]] = {s: [] for s in status_order}
            for row in task_rows:
                task = Task.from_row(row)
                if task.status in tasks_by_status:
                    tasks_by_status[task.status].append(task)

            # Flatten in status order
            result = []
            for s in status_order:
                result.extend(tasks_by_status[s])
            return result

        # Build output
        if ctx.json:
            output = []
            for p in plans:
                plan_dict = p.to_dict()
                tasks = get_tasks_grouped(p.id)
                plan_dict["tasks"] = []
                for t in tasks:
                    task_dict = t.to_dict()
                    note_rows = conn.execute(
                        "SELECT * FROM note WHERE task_id = ? AND deleted_at IS NULL ORDER BY created_at DESC",
                        (t.id,),
                    ).fetchall()
                    task_dict["notes"] = [Note.from_row(row).to_dict() for row in note_rows]
                    plan_dict["tasks"].append(task_dict)
                output.append(plan_dict)
            ctx.output(output)
        else:
            # Status symbols for visual clarity
            status_sym = {"todo": "○", "in_progress": "◐", "blocked": "✗", "done": "●"}

            for i, p in enumerate(plans):
                is_last_plan = i == len(plans) - 1
                plan_prefix = "└─" if is_last_plan else "├─"
                ctx.output("", f"{plan_prefix} 📋 {p.name} (plan {p.id})")

                tasks = get_tasks_grouped(p.id)
                plan_indent = "   " if is_last_plan else "│  "

                for j, t in enumerate(tasks):
                    is_last_task = j == len(tasks) - 1
                    task_prefix = "└─" if is_last_task else "├─"
                    sym = status_sym.get(t.status, "?")
                    ctx.output("", f"{plan_indent}{task_prefix} {sym} [{t.status}] {t.title} (#{t.id})")

                    # Get notes for this task
                    note_rows = conn.execute(
                        "SELECT * FROM note WHERE task_id = ? AND deleted_at IS NULL ORDER BY created_at DESC",
                        (t.id,),
                    ).fetchall()
                    notes = [Note.from_row(row) for row in note_rows]

                    task_indent = plan_indent + ("   " if is_last_task else "│  ")

                    for k, n in enumerate(notes):
                        is_last_note = k == len(notes) - 1
                        note_prefix = "└─" if is_last_note else "├─"
                        text_preview = (n.text[:50] + "...") if len(n.text) > 50 else n.text
                        ctx.output("", f"{task_indent}{note_prefix} 📝 {text_preview}")
