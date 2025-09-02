"""Small git utilities using GitPython.

This module provides a minimal adapter used by the CLI commands. It
keeps error shapes similar to the previous subprocess-based code so
tests and callers can remain simple.
"""

from typing import Optional
import subprocess
from git import (
    Repo,
    InvalidGitRepositoryError,
    NoSuchPathError,
    GitCommandError,
)


def get_staged_diff(path: Optional[str] = None) -> str:
    """Return the staged git diff as a string.

    Raises:
        subprocess.CalledProcessError: If the current directory is not a git repo
        FileNotFoundError: If the underlying git binary cannot be found
    """
    repo_path = path or "."
    try:
        repo = Repo(repo_path)
        # Use the git command interface to get the same textual diff
        diff_text = repo.git.diff("--staged")
        return diff_text

    # TODO: Don't mirror that, instead update the tests
    #   for the new exceptions raised. Leverage the exceptions
    #   from GitPython where appropriate.
    except (InvalidGitRepositoryError, NoSuchPathError):
        # Let the original GitPython exception surface. Tests should be
        # updated to expect these exceptions rather than a subprocess
        # CalledProcessError.
        raise
    except GitCommandError:
        # Surface GitCommandError to callers for more specific handling.
        raise
    except FileNotFoundError:
        # Git binary not found
        raise


def run_commit(message: str, path: Optional[str] = None) -> None:
    """Run a git commit with the provided message.

    Raises subprocess.CalledProcessError on failure to keep compatibility
    with the previous implementation that used subprocess.run(..., check=True).
    """
    repo_path = path or "."
    try:
        repo = Repo(repo_path)
        repo.git.commit(m=message)
    # Let GitPython exceptions surface to callers. Tests and callers
    # should handle InvalidGitRepositoryError, NoSuchPathError and
    # GitCommandError explicitly when needed.
    except (InvalidGitRepositoryError, NoSuchPathError):
        raise
    except GitCommandError:
        raise
    except FileNotFoundError:
        raise
