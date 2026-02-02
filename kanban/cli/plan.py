"""Plan CLI subcommands."""

import click

from .. import db
from ..models import Plan
from ..exceptions import PlanNotFoundError
from . import pass_context, Context


@click.group()
def plan() -> None:
    """Manage plans."""
    pass


@plan.command("create")
@click.argument("name")
@click.option("--description", "-d", help="Plan description")
@pass_context
def create(ctx: Context, name: str, description: str | None) -> None:
    """Create a new plan."""
    with db.get_connection(ctx.db) as conn:
        cursor = conn.execute(
            "INSERT INTO plan (name, description) VALUES (?, ?)",
            (name, description),
        )
        conn.commit()
        plan_id = cursor.lastrowid

        if ctx.json:
            row = conn.execute("SELECT * FROM plan WHERE id = ?", (plan_id,)).fetchone()
            ctx.output(Plan.from_row(row).to_dict())
        else:
            ctx.output(f"Created plan {plan_id}", f"Created plan {plan_id}")


@plan.command("list")
@pass_context
def list_plans(ctx: Context) -> None:
    """List all plans."""
    with db.get_connection(ctx.db) as conn:
        rows = conn.execute("SELECT * FROM plan ORDER BY created_at DESC").fetchall()
        plans = [Plan.from_row(row) for row in rows]

        if ctx.json:
            ctx.output([p.to_dict() for p in plans])
        else:
            if not plans:
                ctx.output("No plans found", "No plans found")
            else:
                for p in plans:
                    ctx.output("", f"{p.id}\t{p.name}")


@plan.command("show")
@click.argument("plan_id", type=int)
@pass_context
def show(ctx: Context, plan_id: int) -> None:
    """Show plan details."""
    with db.get_connection(ctx.db) as conn:
        row = conn.execute("SELECT * FROM plan WHERE id = ?", (plan_id,)).fetchone()
        if not row:
            raise PlanNotFoundError(plan_id)

        plan_obj = Plan.from_row(row)

        if ctx.json:
            ctx.output(plan_obj.to_dict())
        else:
            ctx.output("", f"ID: {plan_obj.id}")
            ctx.output("", f"Name: {plan_obj.name}")
            if plan_obj.description:
                ctx.output("", f"Description: {plan_obj.description}")
            ctx.output("", f"Created: {plan_obj.created_at}")


@plan.command("update")
@click.argument("plan_id", type=int)
@click.option("--name", "-n", help="New name")
@click.option("--description", "-d", help="New description")
@pass_context
def update_plan(ctx: Context, plan_id: int, name: str | None, description: str | None) -> None:
    """Update a plan."""
    with db.get_connection(ctx.db) as conn:
        row = conn.execute("SELECT * FROM plan WHERE id = ?", (plan_id,)).fetchone()
        if not row:
            raise PlanNotFoundError(plan_id)

        updates = []
        params = []
        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if description is not None:
            updates.append("description = ?")
            params.append(description)

        if updates:
            params.append(plan_id)
            conn.execute(f"UPDATE plan SET {', '.join(updates)} WHERE id = ?", params)
            conn.commit()

        row = conn.execute("SELECT * FROM plan WHERE id = ?", (plan_id,)).fetchone()
        plan_obj = Plan.from_row(row)

        if ctx.json:
            ctx.output(plan_obj.to_dict())
        else:
            ctx.output(f"Updated plan {plan_id}", f"Updated plan {plan_id}")


@plan.command("delete")
@click.argument("plan_id", type=int)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
@pass_context
def delete(ctx: Context, plan_id: int, yes: bool) -> None:
    """Delete a plan and all its tasks."""
    with db.get_connection(ctx.db) as conn:
        row = conn.execute("SELECT * FROM plan WHERE id = ?", (plan_id,)).fetchone()
        if not row:
            raise PlanNotFoundError(plan_id)

        plan_obj = Plan.from_row(row)

        if not yes and not ctx.json:
            click.confirm(f"Delete plan '{plan_obj.name}' and all its tasks?", abort=True)

        conn.execute("DELETE FROM plan WHERE id = ?", (plan_id,))
        conn.commit()

        if ctx.json:
            ctx.output({"deleted": plan_id})
        else:
            ctx.output(f"Deleted plan {plan_id}", f"Deleted plan {plan_id}")
