"""Textual TUI application for kanban viewer."""

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import DataTable, Footer, Header, ListItem, ListView, Static

from ..db import get_connection
from ..models import Plan, Task


class DetailPanel(Static):
    """Panel showing task details."""

    DEFAULT_CSS = """
    DetailPanel {
        width: 35%;
        height: 100%;
        border: solid $primary;
        padding: 1;
    }
    """

    def update_task(self, task: Task | None) -> None:
        if task is None:
            self.update("No task selected")
            return

        lines = [
            f"[bold]Title:[/bold] {task.title}",
            f"[bold]Status:[/bold] {task.status}",
            f"[bold]Plan ID:[/bold] {task.plan_id}",
            f"[bold]Created:[/bold] {task.created_at}",
            "",
        ]

        if task.description:
            lines.append(f"[bold]Description:[/bold]\n{task.description}")
            lines.append("")

        if task.reference_repo:
            lines.append("[bold]Git Context:[/bold]")
            lines.append(f"  Repo: {task.reference_repo}")
            if task.reference_repo_branch:
                lines.append(f"  Branch: {task.reference_repo_branch}")
            if task.current_commit:
                lines.append(f"  Commit: {task.current_commit[:8]}")
            lines.append(f"  Dirty: {'Yes' if task.repo_dirty else 'No'}")
            if task.reference_repo_worktree:
                lines.append(f"  Worktree: {task.reference_repo_worktree}")

        self.update("\n".join(lines))


class PlanListItem(ListItem):
    """List item for a plan."""

    def __init__(self, plan: Plan) -> None:
        super().__init__()
        self.plan = plan

    def compose(self) -> ComposeResult:
        yield Static(f"{self.plan.name}")


class KanbanApp(App):
    """Kanban TUI viewer."""

    CSS = """
    #main {
        height: 1fr;
    }
    #plan-list {
        width: 20%;
        border: solid $primary;
    }
    #task-table {
        width: 45%;
        border: solid $primary;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("tab", "focus_next", "Next Pane"),
        Binding("shift+tab", "focus_previous", "Prev Pane"),
    ]

    def __init__(self, db_path: str | None = None) -> None:
        super().__init__()
        self.db_path = db_path
        self.plans: list[Plan] = []
        self.tasks: list[Task] = []
        self.selected_plan_id: int | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="main"):
            yield ListView(id="plan-list")
            yield DataTable(id="task-table")
            yield DetailPanel("No task selected")
        yield Footer()

    def on_mount(self) -> None:
        self.title = "Kanban TUI"
        self.load_plans()

        table = self.query_one("#task-table", DataTable)
        table.add_columns("ID", "Status", "Title")
        table.cursor_type = "row"

    def load_plans(self) -> None:
        with get_connection(self.db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM plan ORDER BY created_at DESC"
            ).fetchall()
            self.plans = [Plan.from_row(row) for row in rows]

        plan_list = self.query_one("#plan-list", ListView)
        plan_list.clear()
        for plan in self.plans:
            plan_list.append(PlanListItem(plan))

    def load_tasks(self, plan_id: int) -> None:
        with get_connection(self.db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM task WHERE plan_id = ? ORDER BY created_at DESC",
                (plan_id,),
            ).fetchall()
            self.tasks = [Task.from_row(row) for row in rows]

        table = self.query_one("#task-table", DataTable)
        table.clear()
        for task in self.tasks:
            table.add_row(str(task.id), task.status, task.title, key=str(task.id))

        # Clear detail panel when switching plans
        detail = self.query_one(DetailPanel)
        detail.update_task(None)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if isinstance(event.item, PlanListItem):
            self.selected_plan_id = event.item.plan.id
            self.load_tasks(event.item.plan.id)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.row_key and event.row_key.value:
            task_id = int(event.row_key.value)
            task = next((t for t in self.tasks if t.id == task_id), None)
            detail = self.query_one(DetailPanel)
            detail.update_task(task)

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.row_key and event.row_key.value:
            task_id = int(event.row_key.value)
            task = next((t for t in self.tasks if t.id == task_id), None)
            detail = self.query_one(DetailPanel)
            detail.update_task(task)


def run(db_path: str | None = None) -> None:
    """Run the TUI application."""
    app = KanbanApp(db_path=db_path)
    app.run()
