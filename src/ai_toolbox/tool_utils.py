"""Utility wrappers around external developer tools (pylint, bandit).

These wrappers intentionally return the raw stdout/stderr as a string so the
calling code or AI can decide how to interpret the output.
"""

import subprocess


def _validate_path(path: str) -> None:
    if not isinstance(path, str) or not path.strip():
        raise ValueError("path must be a non-empty string")


def run_pylint(path: str) -> str:
    """Run pylint on the provided path and return raw output as a string.

    Returns combined stdout+stderr. If pylint is not installed, returns a
    descriptive error string instead of raising.
    """
    _validate_path(path)

    cmd = ["pylint", path]
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


def run_security_scan(path: str) -> str:
    """Run bandit (security scanner) recursively on the provided path.

    Returns raw output (we use JSON format by default). If bandit is not
    installed, returns a descriptive error string.
    """
    _validate_path(path)

    cmd = ["bandit", "-r", path, "-f", "json"]
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
