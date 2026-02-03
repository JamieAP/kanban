"""TUI subcommand for kanban."""

import click

from . import pass_context, Context


@click.command("tui")
@pass_context
def tui(ctx: Context) -> None:
    """Launch the TUI viewer."""
    try:
        from ..tui.app import run
    except ImportError:
        raise click.ClickException(
            "TUI requires 'textual'. Install with: pip install kanban[tui]"
        )

    run(db_path=ctx.db)
