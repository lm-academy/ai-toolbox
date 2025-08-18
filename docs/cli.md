# AI Toolbox CLI

The AI Toolbox is driven by a Click-based CLI defined in `src/ai_toolbox/main.py`.

Global options (available on the top-level command group):

- `--verbose`, `-v`: enable verbose (DEBUG) logging
- `--model`, `-m`: LLM model to use (default: `openai/gpt-4o-mini`)

Top-level commands:

- `hello` — ask the configured LLM for a short, friendly greeting.
- `commit` — generate a conventional commit message from staged changes (interactive).

Examples:

```bash
# Show help
python -m ai_toolbox.main --help

# Generate a greeting
python -m ai_toolbox.main hello

# Generate a commit message (requires git + staged changes)
python -m ai_toolbox.main commit
```

Notes:

- LLM calls use the `litellm` library. Ensure the environment is configured with appropriate credentials (for example via a `.env` file).
- The `commit` command executes `git` commands; make sure `git` is installed and the working directory is a git repository with staged changes.

Console script after installation

When the package is installed (for example via `pip install ai_toolbox` or `pip install -e .`), a console script named `ai-toolbox` will be available. It maps to the same `Click` entry point as the `python -m ai_toolbox.main` command, so the following are equivalent:

```bash
# module form
python -m ai_toolbox.main hello

# installed console script (after pip install)
ai-toolbox hello
```
