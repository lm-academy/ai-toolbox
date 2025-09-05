import click
import logging
from ...git_utils import get_diff
from .helpers import run_review_pipeline

logger = logging.getLogger(__name__)


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
    diff = get_diff(staged=staged)

    # Get model from context (mirror commit.py behavior)
    model = ctx.obj.get("model", "openai/gpt-4o-mini")
    logger.debug(f"Using model for review command: {model}")
    click.echo(f"🤖 Using model: {model}")

    click.echo(
        "🚦 Starting review pipeline (this may take a while)..."
    )
    result = run_review_pipeline(diff=diff, model=model)

    click.echo(result.to_dict())
