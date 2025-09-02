import click

from ai_toolbox.commands import review


def test_review_command_exists():
    assert isinstance(review, click.Command)
