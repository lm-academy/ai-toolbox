from click.testing import CliRunner
from ai_toolbox.main import cli


def test_hello():
    runner = CliRunner()
    result = runner.invoke(cli, ["hello"])
    assert result.exit_code == 0
    assert "Hello from the AI toolbox!" in result.output
