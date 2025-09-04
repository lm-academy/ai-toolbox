import importlib

review = importlib.import_module("ai_toolbox.commands.review")


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
        "[ANALYSIS]ok[/ANALYSIS][SUGGESTIONS]fix[/SUGGESTIONS]"
    )

    m = mocker.patch(
        "ai_toolbox.commands.review.completion",
        return_value=mock_resp,
    )

    result = review.analyze_syntax(
        sample_diff, model="fake-model"
    )

    assert "[ANALYSIS]" in result
    assert "[SUGGESTIONS]" in result
    m.assert_called_once()


def test_analyze_logic_calls_llm_and_returns_content(mocker):
    sample_diff = "+ def bar():\n+    return x"
    mock_resp = DummyResponse(
        "[ANALYSIS]logic[/ANALYSIS][SUGGESTIONS]improve[/SUGGESTIONS]"
    )

    m = mocker.patch(
        "ai_toolbox.commands.review.completion",
        return_value=mock_resp,
    )

    result = review.analyze_logic(
        sample_diff, model="fake-model"
    )

    assert "[ANALYSIS]" in result
    assert "[SUGGESTIONS]" in result
    m.assert_called_once()


def test_analyze_helpers_skip_when_no_model():
    sample_diff = "+ def ok():\n+    pass"
    assert (
        review.analyze_syntax(sample_diff)
        == "<skipped: no model provided>"
    )
    assert (
        review.analyze_logic(sample_diff)
        == "<skipped: no model provided>"
    )
