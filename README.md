# AI Toolbox

This repository contains the code for the AI Toolbox Project from my Prompt Engineering course. The entire code for the course lectures can be found here: https://github.com/lm-academy/prompt-engineering-developers

### ➡️ Course link (with a big discount 🙂): [https://www.lauromueller.com/courses/prompt-engineering](https://www.lauromueller.com/courses/prompt-engineering)

**Check my other courses:**

- 👉 [Python for DevOps: Mastering Real-World Automation](https://www.lauromueller.com/courses/python-devops)
- 👉 [The Complete Docker and Kubernetes Course: From Zero to Hero](https://www.lauromueller.com/courses/docker-kubernetes)
- 👉 [Mastering Terraform: From Beginner to Expert](https://www.lauromueller.com/courses/mastering-terraform)
- 👉 [The Definitive Helm Course: From Beginner to Master](https://www.lauromueller.com/courses/definitive-helm-course)
- 👉 [Mastering GitHub Actions: From Beginner to Expert](https://www.lauromueller.com/courses/mastering-github-actions)
- 👉 [Write better code: 20 code smells and how to get rid of them](https://www.lauromueller.com/courses/writing-clean-code)

## Description

AI Toolbox is a lightweight, CLI-first Python utility for using LLMs to help with developer workflows. It provides small, focused commands and a minimal tool registry so LLMs can call local developer tools.

## Highlights

- Click-based CLI with top-level commands: `hello`, `commit`, and `review`.
- Commit message generation: analyzes staged diffs and produces Conventional Commits-compliant messages (interactive approval / adjust flow).
- Review pipeline: syntax, logic, persona-based reviews (performance, maintainability, security) and a synthesis/refinement stage.
- Tool Registry + Tool wrappers: `tool_registry` and `tool_utils` expose tools such as `run_pylint` and `run_security_scan` that the review pipeline can use.
- Git helpers: `git_utils` provides `get_diff` and `run_commit` using GitPython.
- Pluggable LLM backend via `litellm` and configurable model with `--model`.

## Quick install (development)

Clone and install in editable mode with dev dependencies:

```bash
git clone <repo-url>
cd ai-toolbox
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .[dev]
```

## Environment

- The project uses `litellm` for LLM access. Provide LLM credentials via environment variables or a `.env` file at the project root. The code calls `dotenv.load_dotenv()` in the CLI bootstrap.
- Ensure `git` is installed and available on PATH when running git-related commands.
- Optional tools used by `tool_utils`: `pylint` and `bandit` (installable via dev extras).

## Usage examples

Run the CLI module directly:

```bash
# Show help
python -m ai_toolbox.main --help

# Generate a greeting
python -m ai_toolbox.main hello

# Generate a commit message (requires staged changes)
python -m ai_toolbox.main commit

# Run a lightweight review of staged changes
python -m ai_toolbox.main review
```

## Console script

When installed (`pip install .` or via the editable dev install above) a console script named `ai-toolbox` is exposed and maps to the same Click entry point.

## Development notes

- Tests: run `pytest -q` to execute the unit test suite in `tests/`.
- Lint & security: `pylint` and `bandit` wrappers are available via `ai_toolbox.tool_utils.TOOL_REGISTRY` and can be executed by the review pipeline.
- Packaging: `pyproject.toml` defines the package metadata and dependencies.

## Documentation

See the `docs/` folder for CLI details, per-command docs and development instructions. Start with `docs/index.md`.

## License

MIT — see `LICENSE`.
