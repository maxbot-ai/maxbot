import asyncio
import logging
from unittest.mock import ANY, AsyncMock, Mock

import pytest
from sanic import Sanic

from maxbot.bot import MaxBot
from maxbot.channels import ChannelsCollection
from maxbot.errors import BotError
from maxbot.rpc import RpcManager


@pytest.fixture(autouse=True)
def mock_sanic_run(monkeypatch):
    monkeypatch.setattr(Sanic, "run", Mock())


@pytest.fixture
def bot():
    # we need at least one channel to run the bot
    channel = Mock()
    channel.configure_mock(name="my_channel")
    bot = MaxBot(channels=ChannelsCollection([channel]))
    return bot


@pytest.fixture
def after_server_start(monkeypatch):
    monkeypatch.setattr(Sanic, "after_server_start", Mock())

    async def execute(app=None):
        for call in Sanic.after_server_start.call_args_list:
            (coro,) = call.args
            await coro(app or Mock(), loop=Mock())

    return execute


@pytest.fixture
def before_server_stop(monkeypatch):
    monkeypatch.setattr(Sanic, "before_server_stop", Mock())

    async def execute(app=None):
        for call in Sanic.before_server_stop.call_args_list:
            (coro,) = call.args
            await coro(app or Mock(), loop=Mock())

    return execute


def test_run_webapp(bot):
    bot.run_webapp("localhost", 8080)

    assert Sanic.run.call_args.args == ("localhost", 8080)

    ch = bot.channels.my_channel
    assert ch.blueprint.called


async def test_report_started(bot, after_server_start, caplog):
    bot.run_webapp("localhost", 8080)

    with caplog.at_level(logging.INFO):
        await after_server_start()
    assert (
        "Started webhooks updater on http://localhost:8080. Press 'Ctrl-C' to exit."
    ) in caplog.text


def test_no_channels():
    bot = MaxBot()
    with pytest.raises(BotError) as excinfo:
        bot.run_webapp("localhost", 8080)
    assert excinfo.value.message == (
        "At least one channel is required to run a bot. "
        "Please, fill the 'channels' section of your bot.yaml."
    )


def test_rpc_enabled(bot, monkeypatch):
    monkeypatch.setattr(RpcManager, "blueprint", Mock())

    bot.dialog_manager.load_inline_resources(
        """
        rpc:
          - method: say_hello
    """
    )
    bot.run_webapp("localhost", 8080)

    assert bot.rpc.blueprint.called


def test_rpc_disabled(bot, monkeypatch):
    monkeypatch.setattr(RpcManager, "blueprint", Mock())

    bot.run_webapp("localhost", 8080)

    assert not bot.rpc.blueprint.called


async def test_autoreload(bot, after_server_start, before_server_stop):
    bot.run_webapp("localhost", 8080, autoreload=True)

    app = Mock()
    await after_server_start(app)
    app.add_task.assert_called_with(bot.autoreloader, name="autoreloader")

    app = AsyncMock()
    await before_server_stop(app)
    app.cancel_task.assert_called_with("autoreloader")


def test_public_url_missing(bot, caplog):
    bot.channels.my_channel.configure_mock(name="my_channel")

    with caplog.at_level(logging.WARNING):
        bot.run_webapp("localhost", 8080)
    assert (
        "Make sure you have a public URL that is forwarded to -> "
        "http://localhost:8080/my_channel and register webhook for it."
    ) in caplog.text


def test_public_url_present(bot):
    bot.run_webapp("localhost", 8080, public_url="https://example.com")

    ch = bot.channels.my_channel
    kw = ch.blueprint.call_args.kwargs
    assert kw["public_url"] == "https://example.com"
