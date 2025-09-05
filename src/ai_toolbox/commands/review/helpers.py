import click
import logging
import textwrap
from typing import Optional, Any, Union
from litellm import completion
import json
from ai_toolbox.tool_utils import TOOL_REGISTRY
from litellm.exceptions import AuthenticationError
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


def run_persona_review(
    diff: str,
    persona_template: str,
    persona_name: str,
    model: Optional[str] = None,
) -> Union[str, dict[str, Any]]:
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

    # Helper: parse JSON from model content robustly (not used for persona reviews,
    # but kept for future JSON-enabled prompts)
    def _parse_model_json(raw: str) -> Any:
        try:
            return json.loads(raw)
        except Exception:
            # Attempt to extract first {...} block
            start = raw.find("{")
            end = raw.rfind("}")
            if start != -1 and end != -1 and end > start:
                try:
                    return json.loads(raw[start : end + 1])
                except Exception:
                    return raw
            return raw

    if not model:
        logger.debug(
            "No model provided for persona review - skipping LLM call"
        )
        return "<skipped: no model provided>"

    try:
        # For persona reviews we expect plain text in the tests, so do a simple completion
        resp: Any = completion(model=model, messages=messages)
        content = resp.choices[0].message.content or ""
        return content
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
    personas_dict: dict[str, str],
    model: Optional[str] = None,
) -> dict[str, Union[str, dict[str, Any]]]:
    """Run the performance, maintainability and security persona reviews.

    Returns a dict mapping persona name to the raw review string.
    """
    reviews: dict[str, Any] = {}
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
    reviews: dict[str, Union[str, dict[str, Any]]],
    model: Optional[str] = None,
) -> Union[str, dict[str, Any]]:
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
        # Keep backward compatibility: return raw content if it's not JSON
        try:
            return json.loads(content)
        except Exception:
            return content
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
    final_review = ""
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
        # Include final polished review in the result
        final_review = refined
    except Exception:
        logger.exception(
            "Error while running analysis functions"
        )

    return {"preview": preview, "final_review": final_review}


def analyze_syntax(
    diff: str, model: Optional[str] = None
) -> Union[str, dict[str, Any]]:
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
        return {"error": "<skipped: no model provided>"}

    try:
        resp: Any = completion(
            model=model,
            messages=messages,
            response_format={"type": "json_object"},
        )
        content = resp.choices[0].message.content or ""
        try:
            return json.loads(content)
        except Exception:
            return {"error": "invalid_json", "raw": content}
    except AuthenticationError as e:
        logger.error(
            f"LLM authentication failed in analyze_syntax: {e}"
        )
        return {"error": f"authentication failed: {e}"}
    except Exception as e:
        logger.exception(
            "Unexpected error calling LLM in analyze_syntax"
        )
        return {"error": str(e)}


def self_consistency_review(
    synthesis: Union[str, dict[str, Any]],
    model: Optional[str] = None,
) -> str:
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
            "content": f"<draft_review>\n{synthesis}\n</draft_review>",
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


def analyze_logic(
    diff: str,
    model: Optional[str] = None,
    max_tool_iterations: int = 5,
) -> dict[str, Any]:
    """Analyze the provided diff for logical issues using LLM.

    If `model` is None the call is skipped and a placeholder string is returned.

    Returns the assistant's text content (string).
    """
    logger.debug("analyze_logic called")
    prompt = LOGIC_REVIEW_TEMPLATE

    # Prepare initial messages
    messages = [
        {"role": "system", "content": prompt},
        {
            "role": "user",
            "content": f"<diff>\n{diff}\n</diff>",
        },
    ]

    if not model:
        logger.debug(
            "No model provided for analyze_logic - skipping LLM call"
        )
        return {"error": "<skipped: no model provided>"}

    # Provide tool schemas to the LLM so it can request tool calls
    tool_schemas = TOOL_REGISTRY.generate_all_tool_schemas()

    iteration = 0
    last_message = ""

    try:
        while iteration < max_tool_iterations:
            iteration += 1

            model_response: Any = completion(
                model=model,
                messages=messages,
                tools=tool_schemas,
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

        return {"content": last_message.strip()}
    except AuthenticationError as e:
        logger.error(
            f"LLM authentication failed in analyze_logic: {e}"
        )
        return {"error": f"authentication failed: {e}"}
    except Exception as e:
        logger.exception(
            "Unexpected error calling LLM in analyze_logic"
        )
        return {"error": str(e)}
