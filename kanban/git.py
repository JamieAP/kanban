"""Git context capture utilities."""

import subprocess
from pathlib import Path

from .models import GitContext


def _run_git(args: list[str], cwd: Path) -> str | None:
    """Run a git command and return stdout, or None on failure."""
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None


def _is_git_repo(path: Path) -> bool:
    """Check if path is inside a git repository."""
    return _run_git(["rev-parse", "--git-dir"], path) is not None


def _get_branch(path: Path) -> str | None:
    """Get current branch name, or None if detached/bare."""
    return _run_git(["symbolic-ref", "--short", "HEAD"], path)


def _get_commit(path: Path) -> str | None:
    """Get current commit SHA."""
    return _run_git(["rev-parse", "HEAD"], path)


def _is_dirty(path: Path) -> bool:
    """Check if repo has uncommitted changes."""
    status = _run_git(["status", "--porcelain"], path)
    return status is not None and len(status) > 0


def _get_worktree(path: Path) -> str | None:
    """Get worktree path if in a worktree (not main working tree)."""
    # Get the git common dir (shared .git for worktrees)
    common_dir = _run_git(["rev-parse", "--git-common-dir"], path)
    git_dir = _run_git(["rev-parse", "--git-dir"], path)

    if common_dir and git_dir and common_dir != git_dir:
        # We're in a worktree - return the worktree root
        toplevel = _run_git(["rev-parse", "--show-toplevel"], path)
        return toplevel

    return None


def _get_repo_root(path: Path) -> str | None:
    """Get repository root path."""
    return _run_git(["rev-parse", "--show-toplevel"], path)


def capture_context(path: Path | str | None = None) -> GitContext | None:
    """Capture git context from a directory.

    Args:
        path: Directory to capture from. Uses cwd if None.

    Returns:
        GitContext with captured info, or None if not a git repo.
    """
    if path is None:
        path = Path.cwd()
    else:
        path = Path(path)

    if not path.exists():
        return None

    if not _is_git_repo(path):
        return None

    return GitContext(
        branch=_get_branch(path),
        commit=_get_commit(path),
        dirty=_is_dirty(path),
        worktree=_get_worktree(path),
    )


def get_repo_info(path: Path | str | None = None) -> tuple[str | None, str | None]:
    """Get repo name and root path.

    Returns:
        Tuple of (repo_name, repo_path) or (None, None) if not a repo.
    """
    if path is None:
        path = Path.cwd()
    else:
        path = Path(path)

    if not _is_git_repo(path):
        return None, None

    root = _get_repo_root(path)
    if root:
        return Path(root).name, root

    return None, None
