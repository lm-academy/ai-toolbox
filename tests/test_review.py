import click
from click.testing import CliRunner

from ai_toolbox.commands import review
from ai_toolbox.commands.review import run_review_pipeline


def test_review_command_exists():
    assert isinstance(review, click.Command)


def test_run_review_pipeline_truncates_diff():
    long_diff = "a" * 500
    result = run_review_pipeline(diff=long_diff)
    assert "preview" in result
    assert len(result["preview"]) == 200


def test_review_command_calls_git_and_outputs_preview(mocker):
    # Arrange
    sample_diff = "x" * 300
    mocker.patch(
        "ai_toolbox.commands.review.cli.get_diff",
        return_value=sample_diff,
    )
    # Mock the LLM completion to avoid real network calls
    mock_completion = mocker.patch(
        "ai_toolbox.commands.review.helpers.completion"
    )
    from unittest.mock import Mock

    mock_resp = Mock()
    mock_resp.choices = [Mock()]
    mock_resp.choices[0].message = Mock()
    mock_resp.choices[0].message.content = (
        "[ANALYSIS]No issues[/ANALYSIS][SUGGESTIONS]None[/SUGGESTIONS]"
    )
    mock_completion.return_value = mock_resp

    runner = CliRunner()

    # Act
    result = runner.invoke(review, obj={})

    # Assert
    assert result.exit_code == 0
    # preview is first 200 chars
    assert "Review preview (first 200 chars):" in result.output
    assert sample_diff[:200] in result.output
