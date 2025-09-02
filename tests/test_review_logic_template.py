import importlib


review = importlib.import_module("ai_toolbox.commands.review")


def test_logic_template_exists_and_structure():
    tpl = review.LOGIC_REVIEW_TEMPLATE
    assert isinstance(tpl, str)
    # Must contain the exact wrapper sequence in order
    assert "[ANALYSIS]" in tpl
    assert "[/ANALYSIS]" in tpl
    assert "[SUGGESTIONS]" in tpl
    assert "[/SUGGESTIONS]" in tpl
    # Must instruct chain-of-thought steps
    assert (
        "First, understand the overall goal" in tpl
        or "First, understand the overall goal of the code"
        in tpl
    )
    assert "Second, analyze its logic" in tpl
    assert "Third, also consider" in tpl
    assert "Fourth, formulate" in tpl
    # Must focus on correctness/bugs/edge cases
    assert (
        "bugs" in tpl
        or "edge cases" in tpl
        or "correctness" in tpl
    )
