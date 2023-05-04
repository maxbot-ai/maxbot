import logging
from pathlib import Path
from unittest.mock import Mock

import pytest
from click.testing import CliRunner
from sanic import Sanic

import maxbot.cli


@pytest.fixture
def pkgdir(botfile, monkeypatch):
    pkgdir = botfile.parent
    monkeypatch.syspath_prepend(pkgdir.parent)
    (pkgdir / "__init__.py").write_text(
        "from maxbot import MaxBot\n"
        "builder = MaxBot.builder()\n"
        "builder.use_package_resources(__name__)\n"
        "bot = builder.build()"
    )
    return pkgdir


def test_from_file(runner, botfile, monkeypatch):
    monkeypatch.setattr(Sanic, "run", Mock())

    result = runner.invoke(maxbot.cli.main, ["run", "--bot", botfile], catch_exceptions=False)
    assert result.exit_code == 0, result.output
    assert Sanic.run.call_count == 1


def test_custom_filename(runner, botfile, monkeypatch):
    customfile = botfile.parent / "custom.yaml"
    botfile.rename(customfile)
    monkeypatch.setattr(Sanic, "run", Mock())

    result = runner.invoke(maxbot.cli.main, ["run", "--bot", customfile], catch_exceptions=False)
    assert result.exit_code == 0, result.output
    assert Sanic.run.call_count == 1


def test_from_file_bot_error(runner, botfile, monkeypatch, caplog):
    monkeypatch.setattr(Sanic, "run", Mock())

    botfile.write_text(
        f"""
        dialog: XXX
    """
    )

    with caplog.at_level(logging.CRITICAL):
        result = runner.invoke(maxbot.cli.main, ["run", "--bot", botfile], catch_exceptions=False)
    assert result.exit_code == 1, result.output
    assert "Invalid input type" in caplog.text
    assert "    dialog: XXX" in caplog.text


def test_from_directory(runner, botfile, monkeypatch):
    monkeypatch.setattr(Sanic, "run", Mock())

    result = runner.invoke(
        maxbot.cli.main, ["run", "--bot", botfile.parent], catch_exceptions=False
    )
    assert result.exit_code == 0, result.output
    assert Sanic.run.call_count == 1


def test_package(runner, pkgdir, monkeypatch):
    monkeypatch.setattr(Sanic, "run", Mock())

    result = runner.invoke(maxbot.cli.main, ["run", "--bot", pkgdir.name], catch_exceptions=False)
    assert result.exit_code == 0, result.output
    assert Sanic.run.call_count == 1


def test_package_custom_bot_name(runner, pkgdir, monkeypatch):
    monkeypatch.setattr(Sanic, "run", Mock())

    (pkgdir / "__init__.py").write_text(
        "from maxbot import MaxBot\n"
        "builder = MaxBot.builder()\n"
        "builder.use_package_resources(__name__)\n"
        "custom_bot = builder.build()"
    )

    result = runner.invoke(
        maxbot.cli.main,
        ["run", "--bot", f"{pkgdir.name}:custom_bot"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output
    assert Sanic.run.call_count == 1


def test_package_import_error(runner):
    result = runner.invoke(maxbot.cli.main, ["run", "--bot", "foobar"], catch_exceptions=False)
    assert (
        "file or directory not found, import causes error \"No module named 'foobar'\"."
    ) in result.output


def test_package_invalid_bot_name(runner, pkgdir, caplog):
    with caplog.at_level(logging.ERROR):
        result = runner.invoke(
            maxbot.cli.main, ["run", "--bot", f"{pkgdir.name}:xxx"], catch_exceptions=False
        )
    assert f"While loading '{pkgdir.name}:xxx', an exception was raised" in caplog.text
    assert f"AttributeError: module '{pkgdir.name}' has no attribute 'xxx'" in caplog.text


def test_package_not_a_bot(runner, pkgdir):
    (pkgdir / "__init__.py").write_text("bot = None")

    result = runner.invoke(
        maxbot.cli.main, ["run", "--bot", f"{pkgdir.name}"], catch_exceptions=False
    )
    assert f"a valid MaxBot instance was not obtained from '{pkgdir.name}'." in result.output


def test_package_bot_error(runner, pkgdir, caplog):
    (pkgdir / "__init__.py").write_text(
        "from maxbot.errors import BotError\n" "raise BotError('error message')"
    )
    with caplog.at_level(logging.ERROR):
        runner.invoke(maxbot.cli.main, ["run", "--bot", pkgdir.name], catch_exceptions=False)
    assert "error message" in caplog.text
