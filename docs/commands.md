# Commands

This document describes the two example commands included in the project.

## hello

- Purpose: Ask an LLM to generate a short, friendly greeting for the CLI user.
- Location: `src/ai_toolbox/main.py` (function: `hello`)
- Behavior: Builds a small prompt and calls `litellm.completion(..., stream=True)` to stream output and print it to stdout.
- Error handling: logs authentication or general errors and prints a friendly error message.

## commit

- Purpose: Generate a Conventional Commits-compliant commit message from the output of `git diff --staged`.
- Location: `src/ai_toolbox/commands/commit.py` (function: `commit`)
- Behavior summary:
  - Reads staged diff via `git diff --staged` (helper: `get_staged_diff`).
  - If no changes are staged, the command exits with a message.
  - Formats a prompt with a template that explains Conventional Commits rules.
  - Calls `litellm.completion` to generate a commit message, prints it to the user, and offers actions: Approve / Adjust / Abort.
  - If approved, runs `git commit -m "<message>"` to create the commit.
- Important notes & safety:
  - The command runs `git` to commit; review the generated message before approval.
  - Ensure `git` is installed and the repository is in a consistent state.
