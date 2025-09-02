import importlib


review = importlib.import_module("ai_toolbox.commands.review")


def test_syntax_template_exists_and_structure():
    tpl = review.SYNTAX_REVIEW_TEMPLATE
    assert isinstance(tpl, str)
    # Must contain the exact wrapper sequence in order
    assert "[ANALYSIS]" in tpl
    assert "[/ANALYSIS]" in tpl
    assert "[SUGGESTIONS]" in tpl
    assert "[/SUGGESTIONS]" in tpl
    # Must mention out-of-scope items
    assert (
        "ignore logical" in tpl
        or "Do NOT comment on program correctness" in tpl
    )
    # Must mention PEP 8 or style
    assert "PEP 8" in tpl or "style" in tpl
