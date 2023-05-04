import asyncio
import logging
from unittest.mock import ANY, AsyncMock, Mock, sentinel

import pytest
from telegram.ext import Application, ApplicationBuilder

from maxbot.bot import MaxBot
from maxbot.channels import ChannelsCollection
from maxbot.errors import BotError


@pytest.fixture(autouse=True)
def mock_telegram_polling(monkeypatch):
    monkeypatch.setattr(Application, "run_polling", Mock())


# currently only telegram channel supports polling
RESOURCES = """
    channels:
        telegram:
            api_token: 110201543:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw
"""


@pytest.fixture
def bot():
    return MaxBot.inline(RESOURCES)


@pytest.fixture
def post_init(monkeypatch):
    """Emulate ptb post_init hook."""
    monkeypatch.setattr(ApplicationBuilder, "post_init", Mock())

    async def execute():
        (coro,) = ApplicationBuilder.post_init.call_args.args
        await coro(app=Mock())

    return execute


@pytest.fixture
def post_stop(monkeypatch):
    """Emulate ptb post_stop hook."""
    monkeypatch.setattr(ApplicationBuilder, "post_stop", Mock())

    async def execute():
        (coro,) = ApplicationBuilder.post_stop.call_args.args
        await coro(app=Mock())

    return execute


async def test_run_polling(bot):
    bot.run_polling()
    assert Application.run_polling.called


async def test_token(bot, monkeypatch):
    app = None

    def run_polling(self):
        nonlocal app
        app = self

    monkeypatch.setattr(Application, "run_polling", run_polling)

    bot.run_polling()

    assert app.bot.token == "110201543:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw"


def test_unsupported_channel():
    channel = Mock()
    channel.configure_mock(name="my_channel")
    bot = MaxBot(channels=ChannelsCollection([channel]))

    with pytest.raises(BotError) as excinfo:
        bot.run_polling()
    assert (
        "The 'polling' updater does not support following channels: my_channel. "
        "Please, remove unsupported channels or use the 'webhooks' updater."
    ) == excinfo.value.message


def test_rpc_warning(bot, caplog):
    bot.dialog_manager.load_inline_resources(
        """
        rpc:
          - method: say_hello
    """
    )
    with caplog.at_level(logging.WARNING):
        bot.run_polling()
    assert (
        "Your bot requires RPC service. But you force the 'polling' updater which does not support it. "
        "So RPC requests will not be processed. Please use the 'webhooks' updater in order to use RPC."
    ) in caplog.text


async def test_report_started(bot, post_init, caplog):
    bot.run_polling()

    with caplog.at_level(logging.INFO):
        await post_init()
    assert ("Started polling updater... Press 'Ctrl-C' to exit.") in caplog.text


async def test_callback(bot, monkeypatch, caplog):
    monkeypatch.setattr(Application, "add_handler", Mock())
    monkeypatch.setattr(bot, "default_channel_adapter", AsyncMock())

    bot.run_polling()

    (handler,) = Application.add_handler.call_args.args
    await handler.callback(update=sentinel.update, context=Mock())
    bot.default_channel_adapter.assert_awaited_with(sentinel.update, bot.channels.telegram)


async def test_autoreload(tmp_path, post_init, post_stop):
    # only file based resources support autoreload
    botfile = tmp_path / "bot.yaml"
    botfile.write_text(RESOURCES)
    bot = MaxBot.from_file(botfile)

    bot.run_polling(autoreload=True)

    await post_init()
    task = next(task for task in asyncio.all_tasks() if task.get_name() == "autoreloader")
    assert not task.done()

    await post_stop()
    assert task.cancelled()
