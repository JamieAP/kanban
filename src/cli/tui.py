"""TUI subcommand for kanban."""

import click

from . import pass_context, Context
from ..tui.app import run


@click.command("tui")
@pass_context
def tui(ctx: Context) -> None:
    """Launch the TUI viewer."""
    run(db_path=ctx.db)
