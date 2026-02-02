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
from . import plan, task, update, doc

main.add_command(plan.plan)
main.add_command(task.task)
main.add_command(update.update)
main.add_command(doc.doc)
