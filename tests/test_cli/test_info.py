import importlib.metadata
import platform
from pathlib import Path

import maxbot.cli.info
from maxbot.cli import main


def test_basic(runner):
    result = runner.invoke(main, ["info"], catch_exceptions=False)
    assert result.exit_code == 0, result.output

    out = result.output

    assert "Maxbot version" in out
    assert importlib.metadata.version("maxbot") in out
    assert "Python version" in out
    assert platform.python_version() in out
    assert "Platform" in out
    assert platform.platform() in out

    _location_title = "Location"
    assert _location_title in out

    package_location = "".join(
        i.strip()
        for i in (out[out.index(_location_title) + len(_location_title) : :]).splitlines()
    )
    assert str(Path(__file__).parent.parent.parent) == package_location


def test_unknown_package_version(runner, monkeypatch):
    monkeypatch.setattr(maxbot.cli.info, "__package__", "unknown_maxbot_package")
    result = runner.invoke(main, ["info"], catch_exceptions=False)
    assert result.exit_code == 0, result.output

    out = result.output
    _version_title = "Maxbot version"
    _python_title = "Python version"

    version = (
        out[out.index(_version_title) + len(_version_title) : out.index(_python_title) :]
    ).strip()
    assert not version
