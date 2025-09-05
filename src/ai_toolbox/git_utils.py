"""Small git utilities using GitPython.

This module provides a minimal adapter used by the CLI commands. It
keeps error shapes similar to the previous subprocess-based code so
tests and callers can remain simple.
"""

from typing import Optional
from git import Repo


def _get_staged_diff(path: Optional[str] = None) -> str:
    """Return the staged git diff as a string.

    Raises:
        subprocess.CalledProcessError: If the current directory is not a git repo
        FileNotFoundError: If the underlying git binary cannot be found
    """
    repo_path = path or "."

    repo = Repo(repo_path)
    # Use the git command interface to get the same textual diff
    diff_text = repo.git.diff("--staged")
    return diff_text


def _get_uncommitted_diff(path: Optional[str] = None) -> str:
    """Return the working-tree (uncommitted) diff as a string.

    This mirrors the previous behavior of `git diff` without --staged.
    """
    repo_path = path or "."

    repo = Repo(repo_path)
    diff_text = repo.git.diff()
    return diff_text


def get_diff(
    staged: bool = True, path: Optional[str] = None
) -> str:
    """Convenience helper returning either staged or uncommitted diff.

    Args:
        staged: if True return staged diff, otherwise uncommitted diff.
    """
    if staged:
        return _get_staged_diff(path=path)
    return _get_uncommitted_diff(path=path)


def run_commit(message: str, path: Optional[str] = None) -> None:
    """Run a git commit with the provided message.

    Raises subprocess.CalledProcessError on failure to keep compatibility
    with the previous implementation that used subprocess.run(..., check=True).
    """
    repo_path = path or "."

    repo = Repo(repo_path)
    repo.git.commit(m=message)
