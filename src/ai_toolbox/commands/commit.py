"""Commit command for the AI toolbox CLI.

This module provides a `commit` click command which (eventually)
generates a commit message based on staged changes.
"""

import subprocess
import click


def get_staged_diff() -> str:
    """Get the staged git diff.

    Returns:
        str: The output of 'git diff --staged' command.

    Raises:
        subprocess.CalledProcessError: If the git command fails.
        FileNotFoundError: If git is not found in the system PATH.
    """
    try:
        result = subprocess.run(
            ["git", "diff", "--staged"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        raise subprocess.CalledProcessError(
            e.returncode,
            e.cmd,
            f"Git command failed: {e.stderr}",
        )
    except FileNotFoundError:
        raise FileNotFoundError(
            "Git command not found. Please ensure git is installed and in your PATH."
        )


@click.command()
def commit() -> None:
    """Generate a commit message based on staged changes.

    This is a lightweight boilerplate. The real implementation should
    inspect staged git changes (e.g. via `git diff --staged`) and then
    call an LLM to produce a concise commit message.
    """
    try:
        staged_diff = get_staged_diff()

        if not staged_diff.strip():
            click.echo(
                "No staged changes found. Please stage some changes before generating a commit message."
            )
            return

        # For now, just display the diff (will be replaced with LLM integration later)
        click.echo("[commit] Retrieved staged changes:")
        click.echo(staged_diff)

    except subprocess.CalledProcessError as e:
        click.echo(f"Error running git command: {e}", err=True)
    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
