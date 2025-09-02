import click
import logging
import textwrap
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Literal
from ai_toolbox import git_utils

logger = logging.getLogger(__name__)


# Prompt template for syntax-focused reviews.
# The assistant must act as an automated linter: check only for syntax errors,
# PEP 8 violations, and common code smells. It MUST ignore logical or algorithmic
# issues. The assistant's entire response must be formatted using the exact
# wrapper tags shown below and nothing else: [ANALYSIS]...[/ANALYSIS][SUGGESTIONS]...[/SUGGESTIONS]
SYNTAX_REVIEW_TEMPLATE = textwrap.dedent(
    """
     You are an automated code linter. Your only responsibilities are:

     1. Detect syntax errors (invalid Python syntax) in the provided code or diff.
     2. Detect PEP 8 style violations (naming, line length, indentation, imports,
         whitespace, etc.).
     3. Identify common code smells that indicate readability or maintainability
         problems (e.g., deeply nested blocks, very long functions, duplicated
         code, magic literals, missing docstrings for public functions/classes).

     Do NOT comment on program correctness, algorithmic complexity, or logical
     behavior — those are out of scope for this prompt.

     IMPORTANT: Format your entire reply using EXACTLY the following template and
     nothing else. Do not add preambles, footers, or any text outside the tags.

     [ANALYSIS]
     <Provide a concise analysis of issues found. For each issue include the file
     path (if available), line number (if available), a short description, and
     an optional short code snippet or pointer. Keep this factual and brief.
     [/ANALYSIS]
     [SUGGESTIONS]
     <Provide actionable suggestions for fixing the issues. Each suggestion must
     map to one or more analysis items above. Be concrete (code examples or
     quick fixes are preferred) and prioritize fixes that remove syntax errors
     first, then style improvements, then code-smell remediation.>
     [/SUGGESTIONS]
     """
)


# Prompt template for logic-focused reviews.
# The assistant must act as a senior software architect and follow a simple
# chain-of-thought process: understand goal, analyze logic line-by-line,
# then formulate suggestions. The response MUST be formatted exactly using the
# wrapper tags: [ANALYSIS]...[/ANALYSIS][SUGGESTIONS]...[/SUGGESTIONS]
LOGIC_REVIEW_TEMPLATE = textwrap.dedent(
    """
     You are a senior software architect. Review the provided code or diff with
     a focus on logical correctness, potential bugs, missed edge cases, and
     adherence to software design and Python best practices.

     Follow this Chain-of-Thought process in your analysis (you may keep it
     concise):
     1) First, understand the overall goal of the code.
     2) Second, analyze its logic line-by-line and identify any potential
         correctness problems, suspicious assumptions, or edge cases.
     3) Third, also consider the overall code structure from a holistic
         perspective. In other words, not line-by-line, but from a more
         architectural viewpoint.
     4) Fourth, formulate concrete suggestions to improve correctness,
         robustness, and design.

     IMPORTANT: Format your entire reply using EXACTLY the following template and
     nothing else. Do not include additional commentary outside the tags.

     [ANALYSIS]
     <Present your analysis following the three-step structure. For each finding
     include location (file/line) when possible and a short reasoning snippet.>
     [/ANALYSIS]
     [SUGGESTIONS]
     <Provide prioritized, actionable suggestions and example fixes where
     appropriate. Map each suggestion to analysis items above.>
     [/SUGGESTIONS]
     """
)


@dataclass
class ReviewRequest:
    """Represents a request to run a review pipeline.

    Attributes:
        diff: The unified diff text to review.
        mode: Either 'staged' or 'uncommitted'.
        paths: Optional list of file paths to focus the review on.
    """

    diff: str
    mode: Literal["staged", "uncommitted"] = "staged"
    paths: Optional[List[str]] = field(default=None)

    def __post_init__(self) -> None:
        if self.mode not in ("staged", "uncommitted"):
            raise ValueError(f"Invalid mode: {self.mode}")


@dataclass
class ReviewIssue:
    """Represents a single issue discovered during review."""

    id: str
    severity: Literal["info", "minor", "major", "critical"]
    category: str
    message: str
    file: Optional[str] = None
    line: Optional[int] = None
    snippet: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "severity": self.severity,
            "category": self.category,
            "message": self.message,
            "file": self.file,
            "line": self.line,
            "snippet": self.snippet,
        }


@dataclass
class ReviewResult:
    """Aggregated result from running the review pipeline."""

    summary: str
    issues: List[ReviewIssue] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary": self.summary,
            "issues": [i.to_dict() for i in self.issues],
            "suggestions": self.suggestions,
            "metadata": self.metadata,
        }


@click.command()
@click.option(
    "--staged/--uncommitted",
    default=True,
    help="Choose to review staged changes (default) or uncommitted changes.",
)
@click.pass_context
def review(ctx: click.Context, staged: bool) -> None:
    """Scaffold for the review command.

    The command is intentionally lightweight for now. The real review
    pipeline will be implemented later.
    """
    mode = "staged" if staged else "uncommitted"
    logger.info(f"Running review command in mode: {mode}")

    # Retrieve diff from git and run the lightweight pipeline
    diff = git_utils.get_diff(staged=staged)
    result = run_review_pipeline(diff=diff)

    preview = result.get("preview", "")
    click.echo(f"Review preview (first 200 chars):\n{preview}")


def run_review_pipeline(diff: Optional[str] = None) -> dict:
    """Lightweight review pipeline that returns a 200-char preview.

    For now this integrates git diff retrieval via the calling command
    and returns a minimal dictionary with a `preview` field.
    """
    logger.debug("run_review_pipeline called")
    if not diff:
        return {"preview": ""}

    preview = diff[:200]
    return {"preview": preview}
