import asyncio
import logging
import os
import pickle
from unittest.mock import ANY, AsyncMock, Mock

import pytest
import sanic
from sanic import Sanic

from maxbot.bot import MaxBot
from maxbot.channels import ChannelsCollection
from maxbot.errors import BotError
from maxbot.rpc import RpcManager
from maxbot.webapp import Factory, run_webapp


@pytest.fixture(autouse=True)
def mock_sanic_run(monkeypatch):
    monkeypatch.setattr(Sanic, "run", Mock())
    monkeypatch.setattr(Sanic, "serve", Mock())


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
    return _create_listener_execute("after_server_start")


@pytest.fixture
def before_server_stop(monkeypatch):
    monkeypatch.setattr(Sanic, "before_server_stop", Mock())
    return _create_listener_execute("before_server_stop")


@pytest.fixture
def main_process_start(monkeypatch):
    monkeypatch.setattr(Sanic, "main_process_start", Mock())
    return _create_listener_execute("main_process_start")


@pytest.fixture
def main_process_ready(monkeypatch):
    monkeypatch.setattr(Sanic, "main_process_ready", Mock())
    return _create_listener_execute("main_process_ready")


@pytest.fixture
def main_process_stop(monkeypatch):
    monkeypatch.setattr(Sanic, "main_process_stop", Mock())
    return _create_listener_execute("main_process_stop")


def test_run_webapp(bot):
    run_webapp(bot, None, "localhost", 8080, single_process=True)

    assert Sanic.run.call_args.args == ("localhost", 8080)

    ch = bot.channels.my_channel
    assert ch.blueprint.called


async def test_report_started(bot, after_server_start, caplog):
    run_webapp(bot, None, "localhost", 8080, single_process=True)

    with caplog.at_level(logging.INFO):
        await after_server_start()
    assert (
        "Started webhooks updater on http://localhost:8080. Press 'Ctrl-C' to exit."
    ) in caplog.text


async def test_report_started_mp(bot, after_server_start, caplog):
    run_webapp(bot, None, "localhost", 8080, single_process=False, fast=True)

    with caplog.at_level(logging.INFO):
        app = Mock()
        app.m = Mock()
        app.m.name = "SanicServer-0-0"
        app.m.state = {"starts": 1}
        await after_server_start(app)
    assert (
        "Started webhooks updater on http://localhost:8080. Press 'Ctrl-C' to exit."
    ) in caplog.text


def test_no_channels():
    bot = MaxBot()
    with pytest.raises(BotError) as excinfo:
        run_webapp(bot, None, "localhost", 8080, single_process=True)
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
    run_webapp(bot, None, "localhost", 8080, single_process=True)

    assert bot.rpc.blueprint.called


def test_rpc_disabled(bot, monkeypatch):
    monkeypatch.setattr(RpcManager, "blueprint", Mock())

    run_webapp(bot, None, "localhost", 8080, single_process=True)

    assert not bot.rpc.blueprint.called


async def test_autoreload(bot, after_server_start, before_server_stop):
    run_webapp(bot, None, "localhost", 8080, autoreload=True, single_process=True)

    app = Mock()
    await after_server_start(app)
    app.add_task.assert_called_with(bot.autoreloader, name="autoreloader")

    app = AsyncMock()
    await before_server_stop(app)
    app.cancel_task.assert_called_with("autoreloader")


async def test_public_url_missing(bot, after_server_start, caplog):
    bot.channels.my_channel.configure_mock(name="my_channel")

    with caplog.at_level(logging.WARNING):
        run_webapp(bot, None, "localhost", 8080, single_process=True)
        await after_server_start()

    assert (
        "Make sure you have a public URL that is forwarded to -> "
        "http://localhost:8080/my_channel and register webhook for it."
    ) in caplog.text


def test_public_url_present(bot):
    run_webapp(bot, None, "localhost", 8080, public_url="https://example.com", single_process=True)

    ch = bot.channels.my_channel
    kw = ch.blueprint.call_args.kwargs
    assert kw["public_url"] == "https://example.com"


def test_base_file_name(bot):
    fname = Factory(bot, None, "localhost", 8080, None, None, None, None).base_file_name
    with open(fname, "w") as f:
        pass
    os.unlink(fname)


def _create_mock():
    return Mock()


def test_pickle_bot():
    bot = _create_mock()
    factory1 = Factory(bot, _create_mock, "localhost", 8080, None, None, None, None)
    factory2 = pickle.loads(pickle.dumps(factory1))
    assert factory1.bot is not None
    assert factory2.bot is not None
    assert id(factory1.bot) != id(factory2.bot)


_LOG_INITED = False


def _init_logging():
    global _LOG_INITED
    _LOG_INITED = True


def test_pickle_init_logging():
    global _LOG_INITED
    _LOG_INITED = False
    factory1 = Factory(None, _create_mock, "localhost", 8080, _init_logging, None, None, None)
    factory2 = pickle.loads(pickle.dumps(factory1))
    assert _LOG_INITED


def test_sanic_21_force_single_process(bot, monkeypatch):
    monkeypatch.setattr(sanic, "__version__", "21.0.0")
    run_webapp(bot, None, "localhost", 8080, fast=True, single_process=False)
    assert Sanic.run.call_args.kwargs == {"motd": False, "workers": 1}


def test_single_process(bot):
    run_webapp(bot, None, "localhost", 8080, single_process=True)
    assert Sanic.run.call_args.kwargs == {"motd": False, "single_process": True}


def test_multi_processes_fast(bot):
    run_webapp(bot, None, "localhost", 8080, fast=True, single_process=False)
    Sanic.serve.assert_called_once()


def test_multi_processes_workers(bot):
    run_webapp(bot, None, "localhost", 8080, workers=16, single_process=False)
    Sanic.serve.assert_called_once()


async def test_main_process(
    bot, main_process_start, main_process_ready, main_process_stop, caplog
):
    run_webapp(bot, None, "localhost", 8080, init_logging=_init_logging, single_process=False)
    with caplog.at_level(logging.INFO):
        await main_process_start()
        await main_process_ready()
        await main_process_stop()

    assert "Sanic multi-process server starting..." in caplog.text
    assert "Sanic multi-process server stopping..." in caplog.text


def _create_listener_execute(listener_name):
    async def execute(app=None):
        for call in getattr(Sanic, listener_name).call_args_list:
            (coro,) = call.args
            await coro(app or Mock(), loop=Mock())

    return execute
