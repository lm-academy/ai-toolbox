# Contributing & Development

Development notes for working on AI Toolbox.

## Setup

1. Create a virtual environment and activate it.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .[dev]
```

2. Provide LLM credentials in a `.env` file or in your environment. The code expects `litellm` to read credentials from the environment.

## Tests

Run the test suite with pytest:

```bash
pytest -q
```

The project includes a small set of unit tests in the `tests/` folder. When changing behavior, add tests to cover the new code paths.

## Packaging

This project uses `pyproject.toml`. Build a wheel with:

```bash
python -m build
```

Then publish with your preferred method (Twine, etc.).

## Code style

Follow PEP8 and prefer small, well-tested changes. Keep click command functions focused and testable.
