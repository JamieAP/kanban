"""Tests for CLI commands."""

import json

import pytest
from click.testing import CliRunner

from src.cli import main


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def cli_db(tmp_path):
    """Return path to temp database for CLI tests."""
    return str(tmp_path / "cli_test.db")


class TestPlanCLI:
    def test_create_plan(self, runner, cli_db):
        result = runner.invoke(main, ["--db", cli_db, "plan", "create", "My Plan"])
        assert result.exit_code == 0
        assert "Created plan 1" in result.output

    def test_create_plan_with_description(self, runner, cli_db):
        result = runner.invoke(
            main, ["--db", cli_db, "plan", "create", "My Plan", "-d", "A description"]
        )
        assert result.exit_code == 0

    def test_list_plans(self, runner, cli_db):
        runner.invoke(main, ["--db", cli_db, "plan", "create", "Plan 1"])
        runner.invoke(main, ["--db", cli_db, "plan", "create", "Plan 2"])

        result = runner.invoke(main, ["--db", cli_db, "plan", "list"])
        assert result.exit_code == 0
        assert "Plan 1" in result.output
        assert "Plan 2" in result.output

    def test_show_plan(self, runner, cli_db):
        runner.invoke(main, ["--db", cli_db, "plan", "create", "My Plan", "-d", "Desc"])

        result = runner.invoke(main, ["--db", cli_db, "plan", "show", "1"])
        assert result.exit_code == 0
        assert "My Plan" in result.output
        assert "Desc" in result.output

    def test_show_plan_not_found(self, runner, cli_db):
        result = runner.invoke(main, ["--db", cli_db, "plan", "show", "999"])
        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    def test_update_plan(self, runner, cli_db):
        runner.invoke(main, ["--db", cli_db, "plan", "create", "Old Name"])

        result = runner.invoke(
            main, ["--db", cli_db, "plan", "update", "1", "--name", "New Name"]
        )
        assert result.exit_code == 0

        result = runner.invoke(main, ["--db", cli_db, "plan", "show", "1"])
        assert "New Name" in result.output

    def test_delete_plan(self, runner, cli_db):
        runner.invoke(main, ["--db", cli_db, "plan", "create", "To Delete"])

        result = runner.invoke(main, ["--db", cli_db, "plan", "delete", "1", "-y"])
        assert result.exit_code == 0
        assert "Deleted" in result.output

    def test_json_output(self, runner, cli_db):
        runner.invoke(main, ["--db", cli_db, "plan", "create", "JSON Plan"])

        result = runner.invoke(main, ["--db", cli_db, "--json", "plan", "show", "1"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["name"] == "JSON Plan"


class TestTaskCLI:
    def test_create_task(self, runner, cli_db):
        runner.invoke(main, ["--db", cli_db, "plan", "create", "Plan"])

        result = runner.invoke(
            main, ["--db", cli_db, "task", "create", "1", "My Task"]
        )
        assert result.exit_code == 0
        assert "Created task 1" in result.output

    def test_create_task_captures_cwd(self, runner, cli_db):
        runner.invoke(main, ["--db", cli_db, "plan", "create", "Plan"])
        runner.invoke(main, ["--db", cli_db, "task", "create", "1", "Task"])

        result = runner.invoke(main, ["--db", cli_db, "--json", "task", "show", "1"])
        data = json.loads(result.output)
        assert data["cwd"] is not None

    def test_list_tasks_by_plan(self, runner, cli_db):
        runner.invoke(main, ["--db", cli_db, "plan", "create", "Plan 1"])
        runner.invoke(main, ["--db", cli_db, "plan", "create", "Plan 2"])
        runner.invoke(main, ["--db", cli_db, "task", "create", "1", "Task A"])
        runner.invoke(main, ["--db", cli_db, "task", "create", "2", "Task B"])

        result = runner.invoke(main, ["--db", cli_db, "task", "list", "1"])
        assert "Task A" in result.output
        assert "Task B" not in result.output

    def test_list_tasks_by_status(self, runner, cli_db):
        runner.invoke(main, ["--db", cli_db, "plan", "create", "Plan"])
        runner.invoke(main, ["--db", cli_db, "task", "create", "1", "Task 1"])
        runner.invoke(main, ["--db", cli_db, "task", "create", "1", "Task 2"])
        runner.invoke(
            main, ["--db", cli_db, "task", "set", "1", "--status", "done"]
        )

        result = runner.invoke(
            main, ["--db", cli_db, "task", "list", "--status", "todo"]
        )
        assert "Task 2" in result.output
        assert "Task 1" not in result.output

    def test_set_task_status(self, runner, cli_db):
        runner.invoke(main, ["--db", cli_db, "plan", "create", "Plan"])
        runner.invoke(main, ["--db", cli_db, "task", "create", "1", "Task"])

        result = runner.invoke(
            main, ["--db", cli_db, "task", "set", "1", "-s", "in_progress"]
        )
        assert result.exit_code == 0

        result = runner.invoke(main, ["--db", cli_db, "task", "show", "1"])
        assert "in_progress" in result.output

    def test_task_status_shortcuts(self, runner, cli_db):
        runner.invoke(main, ["--db", cli_db, "plan", "create", "Plan"])
        runner.invoke(main, ["--db", cli_db, "task", "create", "1", "Task"])

        result = runner.invoke(main, ["--db", cli_db, "task", "start", "1"])
        assert result.exit_code == 0

        result = runner.invoke(main, ["--db", cli_db, "task", "done", "1"])
        assert result.exit_code == 0

        result = runner.invoke(main, ["--db", cli_db, "task", "todo", "1"])
        assert result.exit_code == 0

        result = runner.invoke(main, ["--db", cli_db, "task", "block", "1", "waiting on API"])
        assert result.exit_code == 0


class TestNoteCLI:
    def test_add_note(self, runner, cli_db):
        runner.invoke(main, ["--db", cli_db, "plan", "create", "Plan"])
        runner.invoke(main, ["--db", cli_db, "task", "create", "1", "Task"])

        result = runner.invoke(
            main,
            ["--db", cli_db, "note", "add", "1", "Progress note"],
        )
        assert result.exit_code == 0
        assert "Added note 1" in result.output

    def test_list_notes(self, runner, cli_db):
        runner.invoke(main, ["--db", cli_db, "plan", "create", "Plan"])
        runner.invoke(main, ["--db", cli_db, "task", "create", "1", "Task"])
        runner.invoke(main, ["--db", cli_db, "note", "add", "1", "First note"])
        runner.invoke(main, ["--db", cli_db, "note", "add", "1", "Second note"])

        result = runner.invoke(main, ["--db", cli_db, "note", "list", "1"])
        assert result.exit_code == 0
        assert "First note" in result.output
        assert "Second note" in result.output


class TestDocCLI:
    def test_link_doc_to_plan(self, runner, cli_db, tmp_path):
        runner.invoke(main, ["--db", cli_db, "plan", "create", "Plan"])

        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello world")

        result = runner.invoke(
            main,
            ["--db", cli_db, "doc", "link", "--plan", "1", str(test_file), "Test doc"],
        )
        assert result.exit_code == 0
        assert "Linked doc 1" in result.output

    def test_link_doc_to_task(self, runner, cli_db, tmp_path):
        runner.invoke(main, ["--db", cli_db, "plan", "create", "Plan"])
        runner.invoke(main, ["--db", cli_db, "task", "create", "1", "Task"])

        test_file = tmp_path / "test.txt"
        test_file.write_text("Content")

        result = runner.invoke(
            main,
            ["--db", cli_db, "doc", "link", "--task", "1", str(test_file), "Relevance"],
        )
        assert result.exit_code == 0

    def test_link_requires_plan_or_task(self, runner, cli_db, tmp_path):
        test_file = tmp_path / "test.txt"
        test_file.write_text("Content")

        result = runner.invoke(
            main, ["--db", cli_db, "doc", "link", str(test_file), "Relevance"]
        )
        assert result.exit_code != 0
        assert "exactly one" in result.output.lower()

    def test_link_nonexistent_file(self, runner, cli_db):
        runner.invoke(main, ["--db", cli_db, "plan", "create", "Plan"])

        result = runner.invoke(
            main,
            ["--db", cli_db, "doc", "link", "--plan", "1", "/nonexistent", "Test"],
        )
        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    def test_show_doc_content(self, runner, cli_db, tmp_path):
        runner.invoke(main, ["--db", cli_db, "plan", "create", "Plan"])

        test_file = tmp_path / "test.txt"
        test_file.write_text("File content here")

        runner.invoke(
            main,
            ["--db", cli_db, "doc", "link", "--plan", "1", str(test_file), "Relevance"],
        )

        result = runner.invoke(
            main, ["--db", cli_db, "doc", "show", "1", "--content"]
        )
        assert result.exit_code == 0
        assert "File content here" in result.output

    def test_unlink_doc(self, runner, cli_db, tmp_path):
        runner.invoke(main, ["--db", cli_db, "plan", "create", "Plan"])

        test_file = tmp_path / "test.txt"
        test_file.write_text("Content")

        runner.invoke(
            main,
            ["--db", cli_db, "doc", "link", "--plan", "1", str(test_file), "Test"],
        )

        result = runner.invoke(main, ["--db", cli_db, "doc", "unlink", "1", "-y"])
        assert result.exit_code == 0
        assert "Unlinked" in result.output
