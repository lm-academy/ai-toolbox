"""Commit command for the AI toolbox CLI.

This module provides a `commit` click command which (eventually)
generates a commit message based on staged changes.
"""

import subprocess
import click
import logging
import sys
from typing import Any
from litellm import completion
from litellm.exceptions import AuthenticationError

# Set up module logger
logger = logging.getLogger(__name__)

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
    logger.debug("Starting to retrieve staged git diff")

    try:
        logger.debug("Executing git diff --staged command")
        result = subprocess.run(
            ["git", "diff", "--staged"],
            capture_output=True,
            text=True,
            check=True,
        )

        diff_length = len(result.stdout)
        logger.debug(
            f"Successfully retrieved git diff, length: {diff_length} characters"
        )

        if diff_length == 0:
            logger.info("No staged changes found in git diff")
        else:
            logger.info(
                f"Retrieved staged diff with {diff_length} characters"
            )

        return result.stdout

    except subprocess.CalledProcessError as e:
        logger.error(
            f"Git diff command failed with return code {e.returncode}: {e.stderr}"
        )
        raise subprocess.CalledProcessError(
            e.returncode,
            e.cmd,
            f"Git command failed: {e.stderr}",
        )
    except FileNotFoundError as e:
        logger.error(f"Git command not found: {e}")
        raise FileNotFoundError(
            "Git command not found. Please ensure git is installed and in your PATH."
        )


@click.command()
@click.pass_context
def commit(ctx: click.Context) -> None:
    """Generate a commit message based on staged changes.

    This is a lightweight boilerplate. The real implementation should
    inspect staged git changes (e.g. via `git diff --staged`) and then
    call an LLM to produce a concise commit message.
    """
    logger.info("Starting commit command")

    # Get model from context
    model = ctx.obj.get("model", "openai/gpt-4o-mini")
    logger.debug(f"Using model for commit command: {model}")

    try:
        logger.debug("Retrieving staged changes from git")
        staged_diff = get_staged_diff()

        if not staged_diff.strip():
            logger.warning(
                "No staged changes found - aborting commit generation"
            )
            click.echo(
                "No staged changes found. Please stage some changes before generating a commit message."
            )
            return

        logger.info(
            "Staged changes found, preparing commit message generation"
        )
        logger.debug(
            "Formatting commit prompt template with diff"
        )
        commit_prompt = COMMIT_MESSAGE_PROMPT_TEMPLATE.format(
            diff=staged_diff
        )

        # Log prompt length for debugging
        prompt_length = len(commit_prompt)
        logger.debug(
            f"Generated commit prompt with {prompt_length} characters"
        )

        # Prepare the LLM messages history; we'll append assistant/user turns on adjust
        messages = [{"role": "user", "content": commit_prompt}]
        logger.debug(
            f"Initialized conversation with {len(messages)} message(s)"
        )

        # Inform the user we're generating the commit message
        click.echo(
            "🤖 Generating commit message, please hold..."
        )

        try:
            iteration_count = 0
            while True:
                iteration_count += 1
                logger.debug(
                    f"Starting commit generation iteration {iteration_count}"
                )

                # Call the LLM to generate the commit message
                logger.debug(
                    f"Calling LLM completion with {len(messages)} messages using model {model}"
                )
                response: Any = completion(
                    model=model,
                    messages=messages,
                )
                logger.debug(
                    "Successfully received LLM response"
                )

                # Extract generated content (assumes non-streaming response)
                generated_message = (
                    response.choices[0].message.content or ""
                ).strip()

                logger.info(
                    f"Generated commit message: {repr(generated_message)}"
                )
                logger.debug(
                    f"Message length: {len(generated_message)} characters"
                )

                # Display generated message inside a clear formatted block
                click.echo(
                    "\n----- Generated commit message -----"
                )
                click.echo(generated_message)
                click.echo("----- End commit message -----\n")

                # Offer numeric choices to the user (default: Approve)
                click.echo(
                    "Choose one of the following actions:\n"
                )
                click.echo("1) Approve (default)")
                click.echo("2) Adjust")
                click.echo("3) Abort")

                logger.debug(
                    "Prompting user for action selection"
                )
                selection = click.prompt(
                    "Choose an action",
                    type=click.IntRange(1, 3),
                    default=1,
                    show_default=True,
                )
                choice = {1: "approve", 2: "adjust", 3: "abort"}[
                    selection
                ]
                logger.info(f"User selected action: {choice}")

                if choice.lower() == "approve":
                    logger.info(
                        "User approved commit message, proceeding with git commit"
                    )
                    try:
                        logger.debug(
                            f"Executing git commit with message: {repr(generated_message)}"
                        )
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
                        logger.info(
                            "Git commit executed successfully"
                        )
                        click.echo(
                            "✅ Commit created successfully."
                        )
                    except subprocess.CalledProcessError as e:
                        logger.error(
                            f"Git commit failed with return code {e.returncode}: {e.stderr}"
                        )
                        click.echo(
                            f"Error committing changes: {e.stderr}",
                            err=True,
                        )
                    return

                if choice.lower() == "abort":
                    logger.info("User aborted commit generation")
                    click.echo("Aborted...")
                    return

                # If user chose Adjust, collect feedback and loop
                if choice.lower() == "adjust":
                    logger.info(
                        "User requested adjustment to commit message"
                    )
                    # Save the assistant's last message and ask the user for adjustment
                    messages.append(
                        {
                            "role": "assistant",
                            "content": generated_message,
                        }
                    )
                    logger.debug(
                        "Added assistant message to conversation history"
                    )

                    adjustment = click.prompt(
                        "Describe the changes you'd like to make to the commit message",
                    )
                    logger.info(
                        f"User provided adjustment feedback: {repr(adjustment)}"
                    )

                    # Append the user's adjustment request to the conversation
                    messages.append(
                        {"role": "user", "content": adjustment}
                    )
                    logger.debug(
                        f"Added user adjustment to conversation history. Total messages: {len(messages)}"
                    )

                    # Inform about generation and continue loop to regenerate
                    click.echo(
                        "🤖 Regenerating commit message with your feedback..."
                    )
                    continue

        except AuthenticationError as e:
            logger.error(f"LLM authentication failed: {e}")
            click.echo(
                "Authentication failed. Please check your API key.",
                err=True,
            )
        except Exception as e:
            logger.error(
                f"Error during LLM interaction: {e}",
                exc_info=True,
            )
            click.echo(
                f"Error generating commit message: {e}", err=True
            )

    except subprocess.CalledProcessError as e:
        logger.error(f"Git command error: {e}")
        click.echo(f"Error running git command: {e}", err=True)
    except FileNotFoundError as e:
        logger.error(f"Git not found error: {e}")
        click.echo(f"Error: {e}", err=True)
