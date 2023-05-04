import asyncio
import logging
from unittest.mock import ANY, AsyncMock, Mock, sentinel

import pytest

from maxbot.bot import MaxBot
from maxbot.errors import BotError

ORIGINAL_RESOURCES = """
    dialog:
      - condition: true
        response: foo bar
"""

CHANGED_RESOURCES = """
    dialog:
      - condition: true
        response: bar baz
"""

INVALID_RESOURCES = "[]"


@pytest.fixture
def botfile(tmp_path, mtime_workaround_func):
    botfile = tmp_path / "bot.yaml"
    botfile.write_text(ORIGINAL_RESOURCES)
    mtime_workaround_func()
    return botfile


@pytest.fixture
def bot(botfile):
    # only  file based resources support autoreload
    return MaxBot.from_file(botfile)


async def _run_autoreloader(bot):
    task = asyncio.create_task(bot.autoreloader())
    # allow the task to run for a moment
    await asyncio.sleep(0)
    task.cancel()


async def test_autoreload(bot, botfile, dialog_stub, state_stub, caplog):
    botfile.write_text(CHANGED_RESOURCES)
    with caplog.at_level(logging.INFO):
        await _run_autoreloader(bot)
    assert "The bot reloaded successfully!" in caplog.text

    (command,) = await bot.dialog_manager.process_message("hey bot", dialog_stub, state_stub)
    assert {"text": "bar baz"} == command


async def test_bot_error(bot, botfile, dialog_stub, state_stub, caplog):
    # write invalid resources
    botfile.write_text(INVALID_RESOURCES)
    with caplog.at_level(logging.WARNING):
        await _run_autoreloader(bot)
    assert "An error occured while reloading the bot" in caplog.text

    (command,) = await bot.dialog_manager.process_message("hey bot", dialog_stub, state_stub)
    assert {"text": "foo bar"} == command


async def test_unhandled_error(bot, caplog, monkeypatch):
    monkeypatch.setattr(bot.resources, "poll", Mock(side_effect=RuntimeError("bar baz")))

    with caplog.at_level(logging.ERROR):
        await _run_autoreloader(bot)
    assert "Unhandled exception in autoreloader" in caplog.text
    assert "bar baz" in caplog.text


async def test_skipped(caplog, monkeypatch):
    bot = MaxBot.inline(ORIGINAL_RESOURCES)

    with caplog.at_level(logging.WARNING):
        await _run_autoreloader(bot)
    assert "Autoreload is not supported and therefore skipped." in caplog.text


async def test_unsupported_changes(bot, botfile, caplog):
    botfile.write_text("extensions: {}")
    with caplog.at_level(logging.WARNING):
        await _run_autoreloader(bot)
    assert (
        "The following resources could not be changed after the bot is started: extensions.\n"
        "These changes will be ignored until you restart the bot."
    ) in caplog.text


async def test_rpc_added(bot, botfile, caplog):
    botfile.write_text("rpc: []")
    with caplog.at_level(logging.WARNING):
        await _run_autoreloader(bot)
    assert (
        "Could not add RPC endpoint while the bot is running. "
        "These changes will be ignored until you restart the bot."
    ) in caplog.text
