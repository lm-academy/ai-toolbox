import click
import logging
import textwrap
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Literal
from ai_toolbox import git_utils
from litellm import completion
from litellm.exceptions import AuthenticationError

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


# Persona-based prompt templates
# Each persona should follow the same exact output formatting requirement as
# other review templates: the assistant must return exactly `[ANALYSIS]...[/ANALYSIS][SUGGESTIONS]...[/SUGGESTIONS]`.

PERFORMANCE_REVIEW_TEMPLATE = textwrap.dedent(
    """
    You are a performance specialist. Review the provided code or diff with a focus
    on algorithmic complexity, memory usage, potential bottlenecks, and opportunities
    for optimization.

    Follow this concise analysis process:
    1) First, summarize the code's intended behavior and hotspots that may impact performance.
    2) Second, analyze algorithmic complexity (time/space), data structures, and hotspots line-by-line.
    3) Third, propose concrete optimizations, trade-offs, and benchmarking suggestions.

    IMPORTANT: Format your entire reply using EXACTLY the following template and
    nothing else. Do not include additional commentary outside the tags.

    [ANALYSIS]
    <Provide measurable findings: complexity (Big-O), memory concerns, cache/micro-optimizations, and specific code locations.>
    [/ANALYSIS]
    [SUGGESTIONS]
    <Provide prioritized, actionable performance improvements, example code changes, and guidance on how to measure impact.>
    [/SUGGESTIONS]
    """
)


MAINTAINABILITY_REVIEW_TEMPLATE = textwrap.dedent(
    """
    You are a maintainability expert. Review the provided code or diff with a focus
    on clarity, readability, naming, documentation, tests, and how easy the code
    is to modify and extend in the future.

    Follow this concise analysis process:
    1) First, describe the module's public surface and the intent of the changes.
    2) Second, analyze code structure, naming, documentation, tests, and coupling/cohesion.
    3) Third, recommend refactors, documentation improvements, and testing gaps.

    IMPORTANT: Format your entire reply using EXACTLY the following template and
    nothing else. Do not include additional commentary outside the tags.

    [ANALYSIS]
    <Provide specific maintainability observations: unclear names, missing docstrings, high cyclomatic complexity, tight coupling, or fragile tests.>
    [/ANALYSIS]
    [SUGGESTIONS]
    <Provide concrete refactor steps, naming suggestions, docstring examples, and testing recommendations prioritized by effort and benefit.>
    [/SUGGESTIONS]
    """
)


SECURITY_REVIEW_TEMPLATE = textwrap.dedent(
    """
    You are a skeptical security analyst. Review the provided code or diff with a focus
    on vulnerabilities, unsafe patterns, input validation, secrets management, and
    potential attack vectors.

    Follow this concise analysis process:
    1) First, outline the trust boundaries and any external inputs the code depends on.
    2) Second, analyze for common security issues (injection, insecure defaults, improper auth/authorization, unsafe deserialization, secrets in code, etc.).
    3) Third, provide prioritized remediation steps and quick mitigations.

    IMPORTANT: Format your entire reply using EXACTLY the following template and
    nothing else. Do not include additional commentary outside the tags.

    [ANALYSIS]
    <List security findings with evidence (location, line, short reasoning). Emphasize exploitable patterns and attack surface.>
    [/ANALYSIS]
    [SUGGESTIONS]
    <Provide concrete fixes, configuration changes, and defensive coding patterns. Prioritize by severity and ease of mitigation.>
    [/SUGGESTIONS]
    """
)


# Synthesis template: lead software architect persona to combine multiple reviews
SYNTHESIS_TEMPLATE = textwrap.dedent(
    """
    You are a lead software architect tasked with synthesizing multiple specialist
    reviews into a single, comprehensive, and de-duplicated report. You will be
    provided with reviews from PERFORMANCE, MAINTAINABILITY, and SECURITY
    specialists. Your job is to merge them, remove duplicates, prioritize
    issues by severity/impact, and produce a clear action plan.

    IMPORTANT: Format your entire reply using EXACTLY the following template and
    nothing else. The output should be in Markdown and follow the tags.

    [ANALYSIS]
    <Summarize combined findings, grouped by area (performance, maintainability, security) and deduplicated.>
    [/ANALYSIS]
    [SUGGESTIONS]
    <Provide a prioritized, actionable plan (short-term quick fixes and longer-term refactors), and list who should own each item.>
    [/SUGGESTIONS]
    """
)


def run_persona_review(
    diff: str,
    persona_template: str,
    persona_name: str,
    model: Optional[str] = None,
) -> str:
    """Run a single persona review using the provided template.

    Returns the raw assistant content (string). If model is None, returns a skip placeholder.
    """
    logger.debug(
        f"run_persona_review called for persona {persona_name}"
    )
    messages = [
        {
            "role": "system",
            "content": persona_template,
        },
        {
            "role": "user",
            "content": f"<diff>\n{diff}\n</diff>",
        },
    ]

    if not model:
        logger.debug(
            "No model provided for persona review - skipping LLM call"
        )
        return "<skipped: no model provided>"

    try:
        resp: Any = completion(model=model, messages=messages)
        content = resp.choices[0].message.content or ""
        return content.strip()
    except AuthenticationError as e:
        logger.error(
            f"LLM authentication failed in run_persona_review: {e}"
        )
        return f"<error: authentication failed: {e}>"
    except Exception as e:
        logger.exception(
            "Unexpected error calling LLM in run_persona_review"
        )
        return f"<error: {e}>"


def run_reviews_with_personas(
    diff: str,
    personas_dict: Dict[str, str],
    model: Optional[str] = None,
) -> Dict[str, str]:
    """Run the performance, maintainability and security persona reviews.

    Returns a dict mapping persona name to the raw review string.
    """
    reviews: Dict[str, str] = {}
    for persona_name, persona_template in personas_dict.items():
        click.echo(
            f"👥 Running persona {persona_name} review..."
        )
        reviews[persona_name] = run_persona_review(
            diff,
            persona_template,
            persona_name=persona_name,
            model=model,
        )
    return reviews


def synthesize_perspectives(
    reviews: Dict[str, str], model: Optional[str] = None
) -> str:
    """Synthesize multiple persona reviews into a single report using the lead architect persona.

    If model is None, returns a skip placeholder.
    """
    logger.debug("synthesize_perspectives called")
    # Build a single prompt that inserts each persona's review into placeholders
    combined = textwrap.dedent(
        f"""
        PERFORMANCE_REVIEW:
        {reviews.get("performance", "")}

        MAINTAINABILITY_REVIEW:
        {reviews.get("maintainability", "")}

        SECURITY_REVIEW:
        {reviews.get("security", "")}
        """
    )

    messages = [
        {
            "role": "system",
            "content": SYNTHESIS_TEMPLATE,
        },
        {
            "role": "user",
            "content": f"<reviews>\n{combined}\n</reviews>",
        },
    ]

    if not model:
        logger.debug(
            "No model provided for synthesis - skipping LLM call"
        )
        return "<skipped: no model provided>"

    try:
        resp: Any = completion(model=model, messages=messages)
        content = resp.choices[0].message.content or ""
        return content.strip()
    except AuthenticationError as e:
        logger.error(
            f"LLM authentication failed in synthesize_perspectives: {e}"
        )
        return f"<error: authentication failed: {e}>"
    except Exception as e:
        logger.exception(
            "Unexpected error calling LLM in synthesize_perspectives"
        )
        return f"<error: {e}>"


def self_consistency_review(
    synthesis: str, model: Optional[str] = None
) -> str:
    """Run a simple self-consistency check on the synthesized report.

    This asks the model to look for contradictions or missed items and improve the report.
    """
    logger.debug("self_consistency_review called")
    prompt = textwrap.dedent(
        """
        You are an expert software architect. Review the synthesized report provided below for internal
        consistency, contradictions, missing high-severity issues, and clarity. Produce an improved
        version of the synthesis that resolves contradictions and fills obvious gaps.

        IMPORTANT: Format your entire reply using EXACTLY the following template and
        nothing else. The output should be in Markdown and follow the tags.

        [ANALYSIS]
        <Summarize combined findings, grouped by area (performance, maintainability, security) and deduplicated.>
        [/ANALYSIS]
        [SUGGESTIONS]
        <Provide the synthesized plan.>
        [/SUGGESTIONS]
        """
    )

    messages = [
        {"role": "system", "content": prompt},
        {
            "role": "user",
            "content": f"<synthesis>{synthesis}</synthesis>",
        },
    ]

    if not model:
        logger.debug(
            "No model provided for self_consistency_review - skipping LLM call"
        )
        return "<skipped: no model provided>"

    try:
        resp: Any = completion(model=model, messages=messages)
        content = resp.choices[0].message.content or ""
        return content.strip()
    except AuthenticationError as e:
        logger.error(
            f"LLM authentication failed in self_consistency_review: {e}"
        )
        return f"<error: authentication failed: {e}>"
    except Exception as e:
        logger.exception(
            "Unexpected error calling LLM in self_consistency_review"
        )
        return f"<error: {e}>"


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
    click.echo("🔎 Retrieving git diff...")
    diff = git_utils.get_diff(staged=staged)

    # Get model from context (mirror commit.py behavior)
    model = ctx.obj.get("model", "openai/gpt-4o-mini")
    logger.debug(f"Using model for review command: {model}")
    click.echo(f"🤖 Using model: {model}")

    click.echo(
        "🚦 Starting review pipeline (this may take a while)..."
    )
    result = run_review_pipeline(diff=diff, model=model)

    preview = result.get("preview", "")
    click.echo(f"Review preview (first 200 chars):\n{preview}")


def run_review_pipeline(
    diff: Optional[str] = None, model: Optional[str] = None
) -> dict:
    """Lightweight review pipeline that returns a 200-char preview.

    For now this integrates git diff retrieval via the calling command
    and returns a minimal dictionary with a `preview` field.
    """
    logger.debug("run_review_pipeline called")
    if not diff:
        return {"preview": ""}

    # For backward compatibility keep preview behavior
    preview = diff[:200]

    # Call analysis helpers if model provided (skipped during tests by default)
    try:
        # Syntax analysis phase
        click.echo("🔧 Starting syntax analysis...")
        if not model:
            click.echo(
                "(skipped) No model provided for syntax analysis"
            )
            syntax_result = analyze_syntax(diff, model=model)
        else:
            syntax_result = analyze_syntax(diff, model=model)
            click.echo("✅ Syntax analysis completed")

        # Logic analysis phase
        click.echo("🧠 Starting logic analysis...")
        if not model:
            click.echo(
                "(skipped) No model provided for logic analysis"
            )
            logic_result = analyze_logic(diff, model=model)
        else:
            logic_result = analyze_logic(diff, model=model)
            click.echo("✅ Logic analysis completed")

        # Print results for now as requested
        click.echo("--- Syntax Analysis Result ---")
        click.echo(syntax_result)
        click.echo("--- Logic Analysis Result ---")
        click.echo(logic_result)

        # Run persona-based reviews
        click.echo(
            "👥 Running persona-based reviews (performance, maintainability, security)..."
        )
        persona_reviews = run_reviews_with_personas(
            diff,
            model=model,
            personas_dict={
                "performance": PERFORMANCE_REVIEW_TEMPLATE,
                "maintainability": MAINTAINABILITY_REVIEW_TEMPLATE,
                "security": SECURITY_REVIEW_TEMPLATE,
            },
        )
        click.echo("✅ Persona reviews completed")

        # Synthesize perspectives
        click.echo(
            "🧩 Synthesizing perspectives into a single report..."
        )
        synthesis = synthesize_perspectives(
            persona_reviews, model=model
        )
        click.echo("✅ Synthesis completed")
        click.echo("--- Synthesized Report ---")
        click.echo(synthesis)

        # Self-consistency check
        click.echo(
            "🔁 Running self-consistency review on the synthesized report..."
        )
        refined = self_consistency_review(synthesis, model=model)
        click.echo("✅ Self-consistency pass completed")
        click.echo("--- Refined Synthesized Report ---")
        click.echo(refined)
    except Exception:
        logger.exception(
            "Error while running analysis functions"
        )

    return {"preview": preview}


def analyze_syntax(
    diff: str, model: Optional[str] = None
) -> str:
    """Analyze the provided diff for syntax/PEP8 issues using LLM.

    If `model` is None the call is skipped and a placeholder string is returned.

    Returns the assistant's text content (string).
    """
    logger.debug("analyze_syntax called")
    prompt = SYNTAX_REVIEW_TEMPLATE

    # Prepare messages: put the diff in the user message so the LLM can analyze it
    messages = [
        {
            "role": "user",
            "content": f"<diff>\n{diff}\n</diff>\n\n{prompt}",
        },
    ]

    if not model:
        logger.debug(
            "No model provided for analyze_syntax - skipping LLM call"
        )
        return "<skipped: no model provided>"

    try:
        resp: Any = completion(model=model, messages=messages)
        content = resp.choices[0].message.content or ""
        return content.strip()
    except AuthenticationError as e:
        logger.error(
            f"LLM authentication failed in analyze_syntax: {e}"
        )
        return f"<error: authentication failed: {e}>"
    except Exception as e:
        logger.exception(
            "Unexpected error calling LLM in analyze_syntax"
        )
        return f"<error: {e}>"


def analyze_logic(diff: str, model: Optional[str] = None) -> str:
    """Analyze the provided diff for logical issues using LLM.

    If `model` is None the call is skipped and a placeholder string is returned.

    Returns the assistant's text content (string).
    """
    logger.debug("analyze_logic called")
    prompt = LOGIC_REVIEW_TEMPLATE

    messages = [
        {
            "role": "user",
            "content": f"<diff>\n{diff}\n</diff>\n\n{prompt}",
        },
    ]

    if not model:
        logger.debug(
            "No model provided for analyze_logic - skipping LLM call"
        )
        return "<skipped: no model provided>"

    try:
        resp: Any = completion(model=model, messages=messages)
        content = resp.choices[0].message.content or ""
        return content.strip()
    except AuthenticationError as e:
        logger.error(
            f"LLM authentication failed in analyze_logic: {e}"
        )
        return f"<error: authentication failed: {e}>"
    except Exception as e:
        logger.exception(
            "Unexpected error calling LLM in analyze_logic"
        )
        return f"<error: {e}>"
