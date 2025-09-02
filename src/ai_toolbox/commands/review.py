import click
import logging
from typing import Optional

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
    click.echo(f"Review command called (mode={mode})")


def run_review_pipeline(diff: Optional[str] = None) -> dict:
    """Placeholder function for the review pipeline.

    Returns a minimal dict to be expanded later.
    """
    logger.debug("run_review_pipeline called")
    return {"status": "not_implemented", "diff": diff}
