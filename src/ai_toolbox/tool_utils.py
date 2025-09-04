"""Utility wrappers around external developer tools (pylint, bandit).

These wrappers intentionally return the raw stdout/stderr as a string so the
calling code or AI can decide how to interpret the output.
"""

import subprocess
from .tool_registry import ToolRegistry


TOOL_REGISTRY = ToolRegistry()


def _sanitize_path(path: str) -> str:
    if not isinstance(path, str) or not path.strip():
        raise ValueError("path must be a non-empty string")

    if path.strip() in [".", "/", "~"]:
        path = "src"

    return path.strip()


@TOOL_REGISTRY.register_tool()
def run_pylint(path: str) -> str:
    """Run pylint on the provided path and return raw output as a string.

    Returns combined stdout+stderr. If pylint is not installed, returns a
    descriptive error string instead of raising.
    """
    sanitized_path = _sanitize_path(path)

    cmd = ["pylint", sanitized_path]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        return out
    except FileNotFoundError:
        return "<error: pylint not installed>"
    except Exception as e:  # pragma: no cover - defensive
        return f"<error: {e}>"


@TOOL_REGISTRY.register_tool()
def run_security_scan(path: str) -> str:
    """Run bandit (security scanner) recursively on the provided path.

    Returns raw output (we use JSON format by default). If bandit is not
    installed, returns a descriptive error string.
    """
    sanitized_path = _sanitize_path(path)

    cmd = ["bandit", "-r", sanitized_path, "-f", "json"]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        return out
    except FileNotFoundError:
        return "<error: bandit not installed>"
    except Exception as e:  # pragma: no cover - defensive
        return f"<error: {e}>"
