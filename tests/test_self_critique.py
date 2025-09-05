from unittest.mock import Mock
from ai_toolbox.commands.review import (
    self_consistency_review,
    run_review_pipeline,
)


def make_mock_response(text):
    mock_resp = Mock()
    mock_resp.choices = [Mock()]
    mock_resp.choices[0].message = Mock()
    mock_resp.choices[0].message.content = text
    return mock_resp


def test_self_consistency_review_and_pipeline_integration(
    mocker,
):
    draft = "Initial synthesis"

    mock_completion = mocker.patch(
        "ai_toolbox.commands.review.helpers.completion"
    )

    # self_consistency_review should be called once with the synthesis
    mock_completion.return_value = make_mock_response(
        "Polished final review"
    )

    polished = self_consistency_review(draft, model="fake-model")
    assert polished == "Polished final review"

    # Now ensure pipeline returns final_review when model is provided
    mocker.patch(
        "ai_toolbox.commands.review.cli.get_diff",
        return_value="x" * 300,
    )

    # Sequence of completions for analyze_syntax, analyze_logic, personas(3), synthesis, self-consistency
    mock_completion.side_effect = [
        make_mock_response(
            "[ANALYSIS]no issues[/ANALYSIS][SUGGESTIONS]none[/SUGGESTIONS]"
        ),
        make_mock_response(
            "[ANALYSIS]logic[/ANALYSIS][SUGGESTIONS]fix[/SUGGESTIONS]"
        ),
        make_mock_response("perf"),
        make_mock_response("maint"),
        make_mock_response("sec"),
        make_mock_response("synth"),
        make_mock_response("Polished final review"),
    ]

    result = run_review_pipeline(
        diff="x" * 300, model="fake-model"
    )
    assert "final_review" in result
    assert result["final_review"] == "Polished final review"
