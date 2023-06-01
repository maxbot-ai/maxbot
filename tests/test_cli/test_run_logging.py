import logging
from unittest.mock import Mock

import pytest
from click.testing import CliRunner
from sanic import Sanic

import maxbot.cli
from maxbot import MaxBot
from maxbot.errors import BotError, YamlSnippet
from maxbot.maxml import fields
from maxbot.schemas import ResourceSchema


def test_logger_file(runner, botfile, tmp_path, monkeypatch):
    monkeypatch.setattr(MaxBot, "run_webapp", Mock())
    monkeypatch.setattr(logging, "basicConfig", Mock())

    logfile = tmp_path / "maxbot.log"

    result = runner.invoke(
        maxbot.cli.main,
        [
            "run",
            "--bot",
            botfile,
            "--logger",
            f"file:{logfile}",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output
    (log_handler,) = logging.basicConfig.call_args.kwargs["handlers"]
    assert log_handler.baseFilename == str(logfile)


@pytest.fixture
def console_handler(runner, botfile, monkeypatch):
    monkeypatch.setattr(MaxBot, "run_webapp", Mock())
    monkeypatch.setattr(logging, "basicConfig", Mock())

    result = runner.invoke(
        maxbot.cli.main,
        [
            "run",
            "--bot",
            botfile,
            "--logger",
            "console",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output
    (log_handler,) = logging.basicConfig.call_args.kwargs["handlers"]
    return log_handler


def _make_log_record(log_level, message, args=tuple()):
    return logging.LogRecord("maxbot", log_level, __file__, 1, message, args, None)


def test_logger_console(console_handler, capsys):
    console_handler.emit(_make_log_record(logging.INFO, "foo bar"))
    _, err = capsys.readouterr()
    assert "✓ foo bar" in err


def test_logger_console_bot_error(console_handler, capsys):
    class C(ResourceSchema):
        s = fields.String()

    source = C().loads("s: hello world")
    err = BotError("something failed", YamlSnippet.from_data(source))

    console_handler.emit(_make_log_record(logging.ERROR, "Got bot error: %s", (err,)))
    _, err = capsys.readouterr()
    assert "✗ Got bot error: something failed" in err
    assert '  in "<unicode string>", line 1, column 1' in err
    assert "  ❱ 1 s: hello world" in err


def test_logger_bad_file(runner, tmp_path):
    badfile = tmp_path / "maxbot.log"
    badfile.mkdir()

    result = runner.invoke(
        maxbot.cli.main,
        [
            "run",
            "--bot",
            "bot.yaml",
            "--logger",
            f"file:{badfile}",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 2, result.output
    assert f"could not log to the '{badfile}'" in result.output


def test_logger_unknown(runner):
    result = runner.invoke(
        maxbot.cli.main,
        ["run", "--bot", "bot.yaml", "--logger", "unknown"],
        catch_exceptions=False,
    )
    assert result.exit_code == 2, result.output
    assert "unknown logger 'unknown'" in result.output
