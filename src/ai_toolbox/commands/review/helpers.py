import click
import logging
import json
from typing import Optional, Any, Union
from litellm import completion
from ai_toolbox.tool_utils import TOOL_REGISTRY
from litellm.exceptions import AuthenticationError
from .interfaces import (
    ReviewResult,
    ReviewIssue,
    review_result_factory,
)
from .prompts import (
    SYNTAX_REVIEW_TEMPLATE,
    LOGIC_REVIEW_TEMPLATE,
    PERFORMANCE_REVIEW_TEMPLATE,
    MAINTAINABILITY_REVIEW_TEMPLATE,
    SECURITY_REVIEW_TEMPLATE,
    SYNTHESIS_TEMPLATE,
    SELF_CRITIQUE_TEMPLATE,
)

logger = logging.getLogger(__name__)


def _parse_review_response(
    response_content: str, review_name: str = "unknown"
) -> ReviewResult:
    try:
        data = json.loads(response_content)

        issues = []

        for issue_data in data.get("issues", []):
            issue = ReviewIssue(
                id=issue_data.get("id", ""),
                severity=issue_data.get("severity", "info"),
                category=issue_data.get("category", ""),
                description=issue_data.get("description", ""),
                file=issue_data.get("file"),
                line=issue_data.get("line"),
                snippet=issue_data.get("snippet"),
            )
            issues.append(issue)

        result = ReviewResult(
            summary=data.get("summary", ""),
            issues=issues,
            suggestions=data.get("suggestions", []),
        )

        return result
    except json.JSONDecodeError as e:
        logger.error(
            f"Failed to parse JSON for {review_name}: {e}"
        )
        return ReviewResult(
            summary=f"Failed to parse JSON for {review_name}: {e}",
            issues=[
                ReviewIssue(
                    id="",
                    severity="major",
                    category="parsing",
                    description=f"Failed to parse JSON: {e}",
                    file=None,
                    line=None,
                    snippet=None,
                )
            ],
            suggestions=[],
        )
    except Exception as e:
        logger.exception(
            f"Unexpected error parsing review response for {review_name}: {e}"
        )
        return ReviewResult(
            summary=f"Unexpected error parsing review response for {review_name}: {e}",
            issues=[
                ReviewIssue(
                    id="",
                    severity="major",
                    category="parsing",
                    description=f"Unexpected error: {e}",
                    file=None,
                    line=None,
                    snippet=None,
                )
            ],
            suggestions=[],
        )


def _execute_llm_call(
    messages: list[dict],
    model: str,
    review_name: str,
    max_tool_iterations: int = 5,
    tool_schemas: list[dict] | None = None,
):
    iteration = 0
    last_message = ""

    try:
        while iteration < max_tool_iterations:
            iteration += 1

            model_response: Any = completion(
                model=model,
                messages=messages,
                tools=tool_schemas,
                response_format={"type": "json_object"},
            )

            model_message = model_response.choices[0].message
            last_message = model_message.content or ""

            # If there are no tool_calls, it means that the
            # model answer is final and we can exit the loop
            if not model_message.tool_calls:
                break

            messages.append(model_message)
            tool_calls = model_message.tool_calls

            for tool_call in tool_calls:
                tool_id = tool_call.id
                tool_name = tool_call.function.name
                raw_tool_args = tool_call.function.arguments

                try:
                    args = (
                        json.loads(raw_tool_args)
                        if raw_tool_args
                        else {}
                    )
                except json.JSONDecodeError:
                    args = {}

                try:
                    tool_result = TOOL_REGISTRY.call_tool(
                        tool_name, **args
                    )
                except KeyError:
                    tool_result = (
                        f"<error: tool not found: {tool_name}>"
                    )
                except Exception as e:
                    tool_result = (
                        f"<error: tool execution failed: {e}>"
                    )

                # Append the tool result to messages so the LLM can consume it
                messages.append(
                    {
                        "role": "tool",
                        "name": tool_name,
                        "content": str(tool_result),
                        "tool_call_id": tool_id,
                    }
                )

        return _parse_review_response(last_message, review_name)
    except AuthenticationError as e:
        logger.error(f"LLM authentication failed in: {e}")
        return review_result_factory(
            "auth-error", error_message=str(e)
        )
    except Exception as e:
        logger.exception(f"Unexpected error calling LLM: {e}")
        return review_result_factory(
            "generic-error", error_message=str(e)
        )


def _print_review_overview(review: ReviewResult) -> None:
    click.echo(f"Summary: {review.summary}")
    click.echo(f"Issues found: {len(review.issues)}")
    click.echo(f"Suggestions: {len(review.suggestions)}")


def run_persona_review(
    diff: str,
    persona_template: str,
    persona_name: str,
    model: Optional[str] = None,
) -> ReviewResult:
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
        return review_result_factory("no-model")

    return _execute_llm_call(messages, model, persona_name)


def run_reviews_with_personas(
    diff: str,
    personas_dict: dict[str, str],
    model: Optional[str] = None,
) -> dict[str, ReviewResult]:
    """Run the performance, maintainability and security persona reviews.

    Returns a dict mapping persona name to the raw review string.
    """
    reviews: dict[str, ReviewResult] = {}
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
    reviews: dict[str, ReviewResult],
    model: Optional[str] = None,
) -> ReviewResult:
    """Synthesize multiple persona reviews into a single report using the lead architect persona.

    If model is None, returns a skip placeholder.
    """
    logger.debug("synthesize_perspectives called")

    if not model:
        logger.debug(
            "No model provided for synthesis - skipping LLM call"
        )
        return review_result_factory("no-model")

    combined = []

    for persona, review in reviews.items():
        combined.append(f"\n{persona.upper()} REVIEW:")
        combined.append(json.dumps(review.to_dict()))

    combined_text = "\n".join(combined)

    messages = [
        {
            "role": "system",
            "content": SYNTHESIS_TEMPLATE,
        },
        {
            "role": "user",
            "content": f"<reviews>\n{combined_text}\n</reviews>",
        },
    ]

    return _execute_llm_call(messages, model, "synthesis")


def run_review_pipeline(
    diff: Optional[str] = None, model: Optional[str] = None
) -> ReviewResult:
    """Lightweight review pipeline that returns a 200-char preview.

    For now this integrates git diff retrieval via the calling command
    and returns a minimal dictionary with a `preview` field.
    """
    logger.debug("run_review_pipeline called")
    if not diff:
        return ReviewResult(
            summary="No diff provided - skipping review",
            issues=[],
            suggestions=[],
        )

    # Call analysis helpers if model provided (skipped during tests by default)
    final_review = ""
    try:
        # Syntax analysis phase
        click.echo("🔧 Starting syntax analysis...")
        syntax_result = analyze_syntax(diff, model=model)
        click.echo("✅ Syntax analysis completed\n")
        _print_review_overview(syntax_result)
        click.echo("\n-----\n")

        # Logic analysis phase
        click.echo("🧠 Starting logic analysis...")
        logic_result = analyze_logic(diff, model=model)
        click.echo("✅ Logic analysis completed\n")
        _print_review_overview(logic_result)
        click.echo("\n-----\n")

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
        for persona, review in persona_reviews.items():
            click.echo(
                f"--- {persona.capitalize()} Review ---\n"
            )
            _print_review_overview(review)
            click.echo("\n-----\n")

        # Synthesize perspectives
        click.echo(
            "🧩 Synthesizing perspectives into a single report..."
        )
        synthesis = synthesize_perspectives(
            {
                **persona_reviews,
                "syntax": syntax_result,
                "logic": logic_result,
            },
            model=model,
        )
        click.echo("✅ Synthesis completed")
        click.echo("--- Synthesized Report ---")
        click.echo(synthesis)
        click.echo("\n-----\n")

        # Self-consistency check
        click.echo(
            "🔁 Running self-consistency review on the synthesized report..."
        )
        refined = self_consistency_review(synthesis, model=model)
        click.echo("✅ Self-consistency pass completed")
        click.echo("--- Refined Synthesized Report ---")
        click.echo(refined)
        click.echo("\n-----\n")
        # Include final polished review in the result

        return refined
    except Exception as e:
        logger.exception(
            "Error while running analysis functions"
        )

        return review_result_factory(
            "generic-error", error_message=str(e)
        )


def analyze_syntax(
    diff: str, model: Optional[str] = None
) -> ReviewResult:
    """Analyze the provided diff for syntax/PEP8 issues using LLM.

    If `model` is None the call is skipped and a placeholder string is returned.

    Returns the assistant's text content (string).
    """
    logger.debug("analyze_syntax called")

    # Prepare messages: put the diff in the user message so the LLM can analyze it
    messages = [
        {
            "role": "system",
            "content": SYNTAX_REVIEW_TEMPLATE,
        },
        {
            "role": "user",
            "content": f"<diff>\n{diff}\n</diff>",
        },
    ]

    if not model:
        logger.debug(
            "No model provided for analyze_syntax - skipping LLM call"
        )
        return review_result_factory("no-model")

    return _execute_llm_call(messages, model, "syntax")


def self_consistency_review(
    synthesis: ReviewResult,
    model: Optional[str] = None,
) -> ReviewResult:
    """Critique and refine the synthesized report using the principal-architect persona.

    If model is None, returns a skip placeholder.
    The output is a single polished final review (plain text).
    """
    logger.debug("self_consistency_review called")

    messages = [
        {
            "role": "system",
            "content": SELF_CRITIQUE_TEMPLATE,
        },
        {
            "role": "user",
            "content": f"<draft_review>\n{synthesis.to_dict()}\n</draft_review>",
        },
    ]

    if not model:
        logger.debug(
            "No model provided for self_consistency_review - skipping LLM call"
        )
        return review_result_factory("no-model")

    return _execute_llm_call(messages, model, "self-consistency")


def analyze_logic(
    diff: str,
    model: Optional[str] = None,
    max_tool_iterations: int = 5,
) -> ReviewResult:
    """Analyze the provided diff for logical issues using LLM.

    If `model` is None the call is skipped and a placeholder string is returned.

    Returns the assistant's text content (string).
    """
    logger.debug("analyze_logic called")

    # Prepare initial messages
    messages = [
        {"role": "system", "content": LOGIC_REVIEW_TEMPLATE},
        {
            "role": "user",
            "content": f"<diff>\n{diff}\n</diff>",
        },
    ]

    if not model:
        logger.debug(
            "No model provided for analyze_logic - skipping LLM call"
        )
        return review_result_factory("no-model")

    # Provide tool schemas to the LLM so it can request tool calls
    tool_schemas = TOOL_REGISTRY.generate_all_tool_schemas()

    return _execute_llm_call(
        messages, model, "logic", tool_schemas=tool_schemas
    )
