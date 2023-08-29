import logging
import sys
from pathlib import Path
from unittest.mock import AsyncMock, Mock, sentinel

import pytest
from sanic import Sanic
from telegram.ext import Application

import maxbot.cli
from maxbot import MaxBot
from maxbot.cli._journal import Dumper, FileJournal, FileQuietJournal, no_journal
from maxbot.cli._rich import PrettyJournal
from maxbot.dialog_manager import DialogManager


def test_updater_webhooks_default(runner, botfile, monkeypatch):
    monkeypatch.setattr(Sanic, "serve", Mock())

    result = runner.invoke(
        maxbot.cli.main,
        ["run", "--bot", botfile],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output
    assert Sanic.serve.call_count == 1


def test_updater_webhooks(runner, botfile, monkeypatch):
    monkeypatch.setattr(Sanic, "run", Mock())

    result = runner.invoke(
        maxbot.cli.main,
        ["run", "--bot", botfile, "--updater", "webhooks", "--single-process"],
        catch_exceptions=False,
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
        maxbot.cli.main,
        ["run", "--bot", botfile, "--host", "localhost", "--single-process"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output
    assert Sanic.run.call_count == 1


def test_updater_for_port(runner, botfile, monkeypatch):
    monkeypatch.setattr(maxbot.cli.run, "run_webapp", Mock())

    result = runner.invoke(
        maxbot.cli.main,
        ["run", "--bot", botfile, "--host", "myhost", "--port", "123", "--single-process"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output
    assert maxbot.cli.run.run_webapp.call_args.args[2:] == ("myhost", 123)


def test_public_url(runner, botfile, monkeypatch):
    monkeypatch.setattr(maxbot.cli.run, "run_webapp", Mock())

    result = runner.invoke(
        maxbot.cli.main,
        [
            "run",
            "--bot",
            botfile,
            "--public-url",
            "http://example.com",
            "--single-process",
        ],
        catch_exceptions=False,
    )
    assert maxbot.cli.run.run_webapp.call_args.kwargs["public_url"] == "http://example.com"


def test_journal_file(runner, botfile, tmp_path, monkeypatch):
    monkeypatch.setattr(maxbot.cli.run, "run_webapp", Mock())
    monkeypatch.setattr(DialogManager, "journal", Mock())

    journal_file = tmp_path / "maxbot.jsonl"

    result = runner.invoke(
        maxbot.cli.main,
        ["run", "--bot", botfile, "--journal-file", f"{journal_file}", "--single-process"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output

    (journal,) = DialogManager.journal.call_args.args
    assert journal.f.name == str(journal_file)


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
    monkeypatch.setattr(maxbot.cli.run, "run_webapp", Mock())
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
            "--journal-output",
            output,
            "--single-process",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output

    (journal,) = DialogManager.journal.call_args.args
    assert journal.dumps == dumps


def test_no_journal(runner, botfile, monkeypatch):
    monkeypatch.setattr(maxbot.cli.run, "run_webapp", Mock())
    monkeypatch.setattr(DialogManager, "journal", Mock())

    try:
        result = runner.invoke(
            maxbot.cli.main,
            ["run", "--bot", botfile, "-qq", "--single-process"],
            catch_exceptions=False,
        )
    finally:
        logging.disable(logging.NOTSET)
    assert result.exit_code == 0, result.output

    (journal,) = DialogManager.journal.call_args.args
    assert journal == no_journal


def test_console_journal(runner, botfile, monkeypatch):
    monkeypatch.setattr(maxbot.cli.run, "run_webapp", Mock())
    monkeypatch.setattr(DialogManager, "journal", Mock())
    monkeypatch.setattr(maxbot.cli._journal, "_stdout_is_non_interactive", lambda: False)

    result = runner.invoke(
        maxbot.cli.main,
        ["run", "--bot", botfile, "--single-process"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output

    (journal,) = DialogManager.journal.call_args.args
    assert isinstance(journal, PrettyJournal)


def test_non_interactive_journal(runner, botfile, monkeypatch):
    monkeypatch.setattr(maxbot.cli.run, "run_webapp", Mock())
    monkeypatch.setattr(DialogManager, "journal", Mock())
    monkeypatch.setattr(maxbot.cli._journal, "_stdout_is_non_interactive", lambda: True)

    result = runner.invoke(
        maxbot.cli.main,
        [
            "run",
            "--bot",
            botfile,
            "--single-process",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output

    (journal,) = DialogManager.journal.call_args.args
    assert isinstance(journal, FileJournal)


def test_file_journal(runner, botfile, tmp_path, monkeypatch):
    monkeypatch.setattr(maxbot.cli.run, "run_webapp", Mock())
    monkeypatch.setattr(DialogManager, "journal", Mock())

    journal_file = tmp_path / "maxbot.jsonl"

    result = runner.invoke(
        maxbot.cli.main,
        ["run", "--bot", botfile, "--journal-file", f"{journal_file}", "--single-process"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output

    (journal,) = DialogManager.journal.call_args.args
    assert isinstance(journal, FileJournal)


def test_quiet_file_journal(runner, botfile, tmp_path, monkeypatch):
    monkeypatch.setattr(maxbot.cli.run, "run_webapp", Mock())
    monkeypatch.setattr(DialogManager, "journal", Mock())

    journal_file = tmp_path / "maxbot.jsonl"

    result = runner.invoke(
        maxbot.cli.main,
        ["run", "--bot", botfile, "-q", "--journal-file", f"{journal_file}", "--single-process"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output

    (journal,) = DialogManager.journal.call_args.args
    assert isinstance(journal, FileQuietJournal)


def test_q_v_mutually_exclusive(runner, telegram_botfile):
    result = runner.invoke(
        maxbot.cli.main,
        ["run", "--bot", telegram_botfile, "-v", "-q"],
        catch_exceptions=False,
    )
    assert result.exit_code == 2, result.output
    assert "Options -q and -v are mutually exclusive." in result.output
