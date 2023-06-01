import logging
from pathlib import Path
from unittest.mock import AsyncMock, Mock, sentinel

import pytest
from sanic import Sanic
from telegram.ext import Application

import maxbot.cli
from maxbot import MaxBot
from maxbot.cli._journal import Dumper, FileJournal
from maxbot.cli._rich import PrettyJournal
from maxbot.dialog_manager import DialogManager


def test_updater_webhooks(runner, botfile, monkeypatch):
    monkeypatch.setattr(Sanic, "run", Mock())

    result = runner.invoke(
        maxbot.cli.main, ["run", "--bot", botfile, "--updater", "webhooks"], catch_exceptions=False
    )
    assert result.exit_code == 0, result.output
    assert Sanic.run.call_count == 1


def test_updater_polling(runner, telegram_botfile, monkeypatch):
    monkeypatch.setattr(Application, "run_polling", Mock())

    result = runner.invoke(
        maxbot.cli.main,
        ["run", "--bot", telegram_botfile, "--updater", "polling"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output
    assert Application.run_polling.call_count == 1


def test_updater_for_telegram(runner, telegram_botfile, monkeypatch):
    monkeypatch.setattr(Application, "run_polling", Mock())

    result = runner.invoke(
        maxbot.cli.main, ["run", "--bot", telegram_botfile], catch_exceptions=False
    )
    assert result.exit_code == 0, result.output
    assert Application.run_polling.call_count == 1


def test_updater_polling_conflicts(runner, telegram_botfile, monkeypatch):
    monkeypatch.setattr(Application, "run_polling", Mock())

    result = runner.invoke(
        maxbot.cli.main,
        ["run", "--bot", telegram_botfile, "--updater", "polling", "--host", "localhost"],
        catch_exceptions=False,
    )
    assert result.exit_code == 2, result.output
    assert "Option '--updater=polling' conflicts with '--host'." in result.output


def test_updater_for_host(runner, botfile, monkeypatch):
    monkeypatch.setattr(Sanic, "run", Mock())

    result = runner.invoke(
        maxbot.cli.main, ["run", "--bot", botfile, "--host", "localhost"], catch_exceptions=False
    )
    assert result.exit_code == 0, result.output
    assert Sanic.run.call_count == 1


def test_updater_for_port(runner, botfile, monkeypatch):
    monkeypatch.setattr(MaxBot, "run_webapp", Mock())

    result = runner.invoke(
        maxbot.cli.main,
        ["run", "--bot", botfile, "--host", "myhost", "--port", "123"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output
    assert MaxBot.run_webapp.call_args.args == ("myhost", 123)


def test_public_url(runner, botfile, monkeypatch):
    monkeypatch.setattr(MaxBot, "run_webapp", Mock())

    result = runner.invoke(
        maxbot.cli.main,
        [
            "run",
            "--bot",
            botfile,
            "--public-url",
            "http://example.com",
        ],
        catch_exceptions=False,
    )
    assert MaxBot.run_webapp.call_args.kwargs["public_url"] == "http://example.com"


def test_journal_file(runner, botfile, tmp_path, monkeypatch):
    monkeypatch.setattr(MaxBot, "run_webapp", Mock())
    monkeypatch.setattr(DialogManager, "journal", Mock())

    journal_file = tmp_path / "maxbot.jsonl"

    result = runner.invoke(
        maxbot.cli.main,
        [
            "run",
            "--bot",
            botfile,
            "--journal-file",
            f"{journal_file}",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output

    (journal,) = DialogManager.journal.call_args.args
    assert journal.chain[-1].f.name == str(journal_file)


def test_journal_bad_file(runner, botfile, tmp_path):
    badfile = tmp_path / "maxbot.log"
    badfile.mkdir()

    result = runner.invoke(
        maxbot.cli.main,
        [
            "run",
            "--bot",
            botfile,
            "--journal-file",
            f"{badfile}",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 2, result.output
    assert f"Invalid value for '--journal-file': {str(badfile)!r}: Is a directory" in result.output


@pytest.mark.parametrize(
    "output, dumps", (("json", Dumper.json_line), ("yaml", Dumper.yaml_triple_dash))
)
def test_journal_output(runner, botfile, tmp_path, monkeypatch, output, dumps):
    monkeypatch.setattr(MaxBot, "run_webapp", Mock())
    monkeypatch.setattr(DialogManager, "journal", Mock())

    journal_file = tmp_path / "maxbot.jsonl"

    result = runner.invoke(
        maxbot.cli.main,
        ["run", "--bot", botfile, "--journal-file", f"{journal_file}", "--journal-output", output],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output

    (journal,) = DialogManager.journal.call_args.args
    assert journal.chain[-1].dumps == dumps


def test_no_journal(runner, botfile, monkeypatch):
    monkeypatch.setattr(MaxBot, "run_webapp", Mock())
    monkeypatch.setattr(DialogManager, "journal", Mock())

    result = runner.invoke(
        maxbot.cli.main,
        [
            "run",
            "--bot",
            botfile,
            "-q",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output

    (journal,) = DialogManager.journal.call_args.args
    assert not journal.chain


def test_console_journal_only(runner, botfile, monkeypatch):
    monkeypatch.setattr(MaxBot, "run_webapp", Mock())
    monkeypatch.setattr(DialogManager, "journal", Mock())

    result = runner.invoke(
        maxbot.cli.main,
        [
            "run",
            "--bot",
            botfile,
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output

    (journal,) = DialogManager.journal.call_args.args
    (console_journal,) = journal.chain
    assert isinstance(console_journal, PrettyJournal)


def test_file_journal_only(runner, botfile, tmp_path, monkeypatch):
    monkeypatch.setattr(MaxBot, "run_webapp", Mock())
    monkeypatch.setattr(DialogManager, "journal", Mock())

    journal_file = tmp_path / "maxbot.jsonl"

    result = runner.invoke(
        maxbot.cli.main,
        [
            "run",
            "--bot",
            botfile,
            "-q",
            "--journal-file",
            f"{journal_file}",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output

    (journal,) = DialogManager.journal.call_args.args
    (file_journal,) = journal.chain
    assert isinstance(file_journal, FileJournal)


def test_console_and_file_journal(runner, botfile, tmp_path, monkeypatch):
    monkeypatch.setattr(MaxBot, "run_webapp", Mock())
    monkeypatch.setattr(DialogManager, "journal", Mock())

    journal_file = tmp_path / "maxbot.jsonl"

    result = runner.invoke(
        maxbot.cli.main,
        [
            "run",
            "--bot",
            botfile,
            "--journal-file",
            f"{journal_file}",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output

    (journal,) = DialogManager.journal.call_args.args
    assert len(journal.chain) == 2
