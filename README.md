# AI Toolbox

AI Toolbox is a small CLI-first Python utility that helps generate developer-facing text using LLMs (for example: commit messages and brief greetings). It provides a Click-based command group with example commands and a simple integration with an LLM backend via `litellm`.

This repository is intended as both a learning example and a lightweight helper for everyday git workflows.

## Features

- Generate conventional commit messages from staged git diffs (`commit` command).
- Produce short, friendly greetings from an LLM (`hello` command).
- Pluggable LLM model via `--model` CLI option and environment variables.

## Installation

Install from PyPI (when published):

```bash
pip install ai_toolbox
```

Run from source (recommended during development):

```bash
git clone <repo>
cd ai-toolbox
python -m pip install -e .  # optional: installs package in editable mode
# then run the CLI via
python -m ai_toolbox.main --help
```

Run after installing the package (console script):

```bash
# If installed (pip install ai_toolbox), the package exposes a console script named `ai-toolbox`.
# You can run the same commands without the -m form:
ai-toolbox --help
ai-toolbox hello
ai-toolbox commit
```

## Quick usage

Run the CLI module directly:

```bash
# Show help
python -m ai_toolbox.main --help

# Generate a greeting (prints an LLM-generated one-liner)
python -m ai_toolbox.main hello

# Generate a commit message from staged changes (interactive)
python -m ai_toolbox.main commit
```

Notes:

- The project uses `litellm` for LLM access; ensure your LLM credentials/API keys are available in the environment (for example via a `.env` file) before running commands that call the LLM.
- The `commit` command relies on `git` being installed and some changes staged (`git add`) to generate a diff.

## Documentation

Detailed documentation is in the `docs/` directory. Start with `docs/index.md`.

## Contributing

See `docs/contributing.md` for guidelines on developing and testing locally.

## License

This project is provided under the terms of the repository `LICENSE` file.

# AI Toolbox

A brief description of your library.

## Installation

```bash
pip install ai_toolbox
```

## Usage

```python
import ai_toolbox
# Example usage
```
