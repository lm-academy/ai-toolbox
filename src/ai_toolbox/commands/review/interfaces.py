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
    message: str
    file: Optional[str] = None
    line: Optional[int] = None
    snippet: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
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
    issues: list[ReviewIssue] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary,
            "issues": [i.to_dict() for i in self.issues],
            "suggestions": self.suggestions,
            "metadata": self.metadata,
        }
