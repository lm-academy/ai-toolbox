from dataclasses import dataclass, field
from typing import Any, Literal, Optional


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
    paths: Optional[list[str]] = field(default=None)

    def __post_init__(self) -> None:
        if self.mode not in ("staged", "uncommitted"):
            raise ValueError(f"Invalid mode: {self.mode}")


@dataclass
class ReviewIssue:
    """Represents a single issue discovered during review."""

    id: str
    severity: Literal["info", "minor", "major", "critical"]
    category: str
    description: str
    file: Optional[str] = None
    line: Optional[int] = None
    snippet: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "severity": self.severity,
            "category": self.category,
            "description": self.description,
            "file": self.file,
            "line": self.line,
            "snippet": self.snippet,
        }


@dataclass
class ReviewResult:
    """Aggregated result from running the review pipeline."""

    summary: str
    issues: list[ReviewIssue] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary,
            "issues": [i.to_dict() for i in self.issues],
            "suggestions": self.suggestions,
        }


def review_result_factory(
    result_type: Literal[
        "no-model", "auth-error", "generic-error"
    ],
    error_message: str = "",
):
    if result_type == "no-model":
        return ReviewResult(
            summary="No model provided - skipping review",
            issues=[],
            suggestions=[],
        )
    elif result_type == "auth-error":
        return ReviewResult(
            summary=f"Authentication error - skipping review: {error_message}",
            issues=[
                ReviewIssue(
                    id="",
                    severity="major",
                    category="authentication",
                    description=f"Authentication failed: {error_message}",
                    file=None,
                    line=None,
                    snippet=None,
                )
            ],
            suggestions=[],
        )
    elif result_type == "generic-error":
        return ReviewResult(
            summary=f"Generic error - skipping review: {error_message}",
            issues=[
                ReviewIssue(
                    id="",
                    severity="major",
                    category="unknown",
                    description=f"Unexpected error: {error_message}",
                    file=None,
                    line=None,
                    snippet=None,
                )
            ],
            suggestions=[],
        )
