import logging
from pathlib import Path
from unittest.mock import AsyncMock, Mock, sentinel

import pytest
from sanic import Sanic
from telegram.ext import Application

import maxbot.cli
from maxbot import MaxBot
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
            "--journal",
            f"file:{journal_file}",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output

    (journal,) = DialogManager.journal.call_args.args
    assert journal.f.name == str(journal_file)
    journal.f.close()


def test_journal_bad_file(runner, botfile, tmp_path):
    badfile = tmp_path / "maxbot.log"
    badfile.mkdir()

    result = runner.invoke(
        maxbot.cli.main,
        [
            "run",
            "--bot",
            botfile,
            "--journal",
            f"file:{badfile}",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 2, result.output
    assert f"could not open '{badfile}'" in result.output


def test_journal_unknown(runner, botfile):
    result = runner.invoke(
        maxbot.cli.main,
        ["run", "--bot", botfile, "--no-reload", "--journal", "unknown"],
        catch_exceptions=False,
    )
    assert result.exit_code == 2, result.output
    assert "unknown journal 'unknown'" in result.output
