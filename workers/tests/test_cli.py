from typer.testing import CliRunner

from halflife.cli import app


def test_help_lists_commands():
    out = CliRunner().invoke(app, ["--help"]).output
    for cmd in ["ingest", "clean", "features", "train", "score", "onboard"]:
        assert cmd in out
