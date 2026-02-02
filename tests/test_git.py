"""Tests for git context capture."""

import subprocess
from pathlib import Path

import pytest

from kanban.git import capture_context, get_repo_info


def test_capture_context_in_repo(tmp_path):
    """Should capture context in a git repo."""
    # Initialize a git repo
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, capture_output=True)

    # Create a file and commit
    (tmp_path / "test.txt").write_text("hello")
    subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=tmp_path, capture_output=True)

    ctx = capture_context(tmp_path)

    assert ctx is not None
    assert ctx.branch in ("main", "master")  # depends on git config
    assert ctx.commit is not None
    assert len(ctx.commit) == 40  # full SHA
    assert ctx.dirty is False


def test_capture_context_dirty_repo(tmp_path):
    """Should detect dirty repo."""
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, capture_output=True)

    (tmp_path / "test.txt").write_text("hello")
    subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=tmp_path, capture_output=True)

    # Make dirty
    (tmp_path / "test.txt").write_text("changed")

    ctx = capture_context(tmp_path)

    assert ctx is not None
    assert ctx.dirty is True


def test_capture_context_not_a_repo(tmp_path):
    """Should return None if not a git repo."""
    ctx = capture_context(tmp_path)
    assert ctx is None


def test_capture_context_nonexistent_path():
    """Should return None for nonexistent path."""
    ctx = capture_context(Path("/nonexistent/path/12345"))
    assert ctx is None


def test_get_repo_info_in_repo(tmp_path):
    """Should return repo name and path."""
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)

    name, path = get_repo_info(tmp_path)

    assert name == tmp_path.name
    assert path == str(tmp_path)


def test_get_repo_info_not_a_repo(tmp_path):
    """Should return None, None if not a repo."""
    name, path = get_repo_info(tmp_path)

    assert name is None
    assert path is None


def test_capture_context_uncommitted_repo(tmp_path):
    """Should handle repo with no commits."""
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)

    ctx = capture_context(tmp_path)

    assert ctx is not None
    assert ctx.commit is None  # No commits yet
    assert ctx.branch in ("main", "master", None)
