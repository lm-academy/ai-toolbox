import json

from ai_toolbox.commands.review import (
    analyze_syntax,
    analyze_logic,
)


class DummyMessage:
    def __init__(self, content, tool_calls=[]):
        self.content = content
        self.tool_calls = tool_calls


class DummyChoice:
    def __init__(self, message):
        self.message = message


class DummyResponse:
    def __init__(self, text):
        self.choices = [DummyChoice(DummyMessage(text))]


def test_analyze_syntax_calls_llm_and_returns_content(mocker):
    sample_diff = "+ def foo():\n+    return 1"
    mock_resp = DummyResponse(
        json.dumps(
            {
                "analysis": "[ANALYSIS]syntax[/ANALYSIS]",
                "suggestions": "[SUGGESTIONS]none[/SUGGESTIONS]",
            }
        )
    )

    m = mocker.patch(
        "ai_toolbox.commands.review.helpers.completion",
        return_value=mock_resp,
    )

    result = analyze_syntax(sample_diff, model="fake-model")

    assert "analysis" in result
    assert "suggestions" in result
    m.assert_called_once()


def test_analyze_logic_calls_llm_and_returns_content(mocker):
    sample_diff = "+ def bar():\n+    return x"
    mock_resp = DummyResponse(
        json.dumps(
            {
                "analysis": "[ANALYSIS]logic[/ANALYSIS]",
                "suggestions": "[SUGGESTIONS]none[/SUGGESTIONS]",
            }
        )
    )

    m = mocker.patch(
        "ai_toolbox.commands.review.helpers.completion",
        return_value=mock_resp,
    )

    result = analyze_logic(sample_diff, model="fake-model")

    assert "analysis" in result["content"]
    assert "suggestions" in result["content"]
    m.assert_called_once()


def test_analyze_helpers_skip_when_no_model():
    sample_diff = "+ def ok():\n+    pass"
    assert analyze_syntax(sample_diff) == {
        "error": "<skipped: no model provided>"
    }
    assert analyze_logic(sample_diff) == {
        "error": "<skipped: no model provided>"
    }
