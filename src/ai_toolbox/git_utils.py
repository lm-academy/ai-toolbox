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
    #   for the new exceptions raised.
    except (InvalidGitRepositoryError, NoSuchPathError):
        # Mirror the old subprocess error shape for compatibility with tests
        raise subprocess.CalledProcessError(
            returncode=128,
            cmd=["git", "diff", "--staged"],
            stderr="fatal: not a git repository",
        )
    except GitCommandError as e:
        # Git command failed for some other reason
        raise subprocess.CalledProcessError(
            returncode=e.status if hasattr(e, "status") else 1,
            cmd=(
                e.command
                if hasattr(e, "command")
                else ["git", "diff", "--staged"]
            ),
            stderr=str(e),
        )
    except FileNotFoundError as e:
        # Git binary not found
        raise FileNotFoundError(str(e))


def run_commit(message: str, path: Optional[str] = None) -> None:
    """Run a git commit with the provided message.

    Raises subprocess.CalledProcessError on failure to keep compatibility
    with the previous implementation that used subprocess.run(..., check=True).
    """
    repo_path = path or "."
    try:
        repo = Repo(repo_path)
        repo.git.commit(m=message)
    except (InvalidGitRepositoryError, NoSuchPathError):
        raise subprocess.CalledProcessError(
            returncode=128,
            cmd=["git", "commit", "-m", message],
            stderr="fatal: not a git repository",
        )
    except GitCommandError as e:
        raise subprocess.CalledProcessError(
            returncode=e.status if hasattr(e, "status") else 1,
            cmd=(
                e.command
                if hasattr(e, "command")
                else ["git", "commit", "-m", message]
            ),
            stderr=str(e),
        )
    except FileNotFoundError as e:
        raise FileNotFoundError(str(e))
