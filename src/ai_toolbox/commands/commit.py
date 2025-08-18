"""Commit command for the AI toolbox CLI.

This module provides a `commit` click command which (eventually)
generates a commit message based on staged changes.
"""

import subprocess
import click
import sys
from typing import Any
from litellm import completion
from litellm.exceptions import AuthenticationError

COMMIT_MESSAGE_PROMPT_TEMPLATE = """You are an expert software developer tasked with generating a concise and informative commit message based on the provided git diff.

**Instructions:**
1. Follow the Conventional Commits specification (https://www.conventionalcommits.org/)
2. Use this format: `<type>[optional scope]: <description>`
3. Keep the first line (title) under 50 characters
4. Use imperative mood (e.g., "add", "fix", "update", not "added", "fixed", "updated")
5. Start with lowercase after the colon
6. Do not end the title with a period

**Common types:**
- feat: new feature
- fix: bug fix
- docs: documentation changes
- style: formatting, missing semicolons, etc.
- refactor: code change that neither fixes a bug nor adds a feature
- test: adding or modifying tests
- chore: maintenance tasks, dependencies, build process
- perf: performance improvements
- ci: continuous integration changes

**Output format:**
- First line: commit title following conventional commits
- Afterwards, a blank line followed by commit body with additional details
- Return only the commit message text, no extra formatting or explanations
- In case of a breaking change, please add BREAKING CHANGE: <description> in the commit body

**Git diff to analyze:**

<diff>
{diff}
</diff>

Generate an appropriate commit message based on the changes shown in the diff above."""


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

        commit_prompt = COMMIT_MESSAGE_PROMPT_TEMPLATE.format(
            diff=staged_diff
        )

        # Inform the user we're generating the commit message
        click.echo(
            "🤖 Generating commit message, please hold..."
        )

        try:
            response: Any = completion(
                model="openai/gpt-4o-mini",
                messages=[
                    {"role": "user", "content": commit_prompt}
                ],
            )

            generated_message = response.choices[
                0
            ].message.content

            # Display generated message inside a clear formatted block
            click.echo("\n----- Generated commit message -----")
            click.echo(generated_message)
            click.echo("----- End commit message -----\n")

            # If not running interactively (tests/non-tty), skip confirmation
            if not sys.stdin.isatty():
                click.echo(
                    "Non-interactive session detected; skipping commit prompt."
                )
                return

            if click.confirm("Accept and commit this message?"):
                try:
                    subprocess.run(
                        [
                            "git",
                            "commit",
                            "-m",
                            generated_message,
                        ],
                        capture_output=True,
                        text=True,
                        check=True,
                    )
                    click.echo("✅ Commit created successfully.")
                except subprocess.CalledProcessError as e:
                    click.echo(
                        f"Error committing changes: {e.stderr}",
                        err=True,
                    )
            else:
                click.echo("Aborted...")

        except AuthenticationError:
            click.echo(
                "Authentication failed. Please check your API key.",
                err=True,
            )
        except Exception as e:
            click.echo(
                f"Error generating commit message: {e}", err=True
            )

    except subprocess.CalledProcessError as e:
        click.echo(f"Error running git command: {e}", err=True)
    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
