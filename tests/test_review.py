import click
from click.testing import CliRunner

from ai_toolbox.commands import review
import importlib

# Import module object explicitly to avoid package attribute shadowing
review_mod = importlib.import_module(
    "ai_toolbox.commands.review"
)
from ai_toolbox import git_utils


def test_review_command_exists():
    assert isinstance(review, click.Command)


def test_run_review_pipeline_truncates_diff():
    long_diff = "a" * 500
    result = review_mod.run_review_pipeline(diff=long_diff)
    assert "preview" in result
    assert len(result["preview"]) == 200


def test_review_command_calls_git_and_outputs_preview(mocker):
    # Arrange
    sample_diff = "x" * 300
    mocker.patch(
        "ai_toolbox.commands.review.git_utils.get_diff",
        return_value=sample_diff,
    )

    runner = CliRunner()

    # Act
    result = runner.invoke(review, obj={})

    # Assert
    assert result.exit_code == 0
    # preview is first 200 chars
    assert "Review preview (first 200 chars):" in result.output
    assert sample_diff[:200] in result.output
