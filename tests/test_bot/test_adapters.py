from unittest.mock import MagicMock, Mock

import pytest

from maxbot.bot import MaxBot
from maxbot.channels import Channel
from maxbot.context import RpcRequest


class TextChannel(Channel):
    def __init__(self, name, config):
        super().__init__(name, config)
        self.sent = []

    async def create_dialog(self, platform_data):
        return {"channel_name": self.name, "user_id": "23"}

    async def receive_text(self, platform_data):
        if isinstance(platform_data, str):
            return platform_data
        return None

    async def send_text(self, command: dict, dialog: dict):
        self.sent.append(command["text"].render())


@pytest.fixture
def bot():
    return MaxBot()


@pytest.fixture
def channel():
    return TextChannel("text_channel", config={})


async def test_default_channel_adapter(bot, channel):
    bot.dialog_manager.load_inline_resources(
        """
        dialog:
          - condition: message.text == "hey bot"
            response: hello world
    """
    )
    await bot.default_channel_adapter("hey bot", channel)
    assert channel.sent == ["hello world"]


async def test_unknown_request(bot, channel):
    bot.dialog_manager.load_inline_resources(
        """
        dialog:
          - condition: message.text == "hey bot"
            response: hello world
    """
    )
    await bot.default_channel_adapter({}, channel)
    assert channel.sent == []


async def test_default_rpc_adapter(bot, channel):
    bot.dialog_manager.load_inline_resources(
        """
        rpc:
          - method: hey_bot
        dialog:
          - condition: rpc.method == "hey_bot"
            response: hello world
    """
    )
    await bot.default_rpc_adapter({"method": "hey_bot"}, channel, user_id="23")
    assert channel.sent == ["hello world"]


async def test_persistence_manager(channel):
    mock = MagicMock()
    bot = MaxBot(persistence_manager=Mock(return_value=mock))
    await bot.default_channel_adapter("hey bot", channel)

    bot.persistence_manager.assert_called_once_with(
        {"channel_name": channel.name, "user_id": "23"}
    )
    mock.__enter__.assert_called_once()
    mock.__exit__.assert_called_once()


async def test_track_history_channel(channel):
    tracker = MagicMock()
    mock = MagicMock()
    mock.__enter__ = Mock(return_value=tracker)
    bot = MaxBot(persistence_manager=Mock(return_value=mock), history_tracked=True)
    await bot.default_channel_adapter("hey bot", channel)

    tracker.set_message_history.assert_called_once()


async def test_track_history_rpc(channel):
    tracker = MagicMock()
    mock = MagicMock()
    mock.__enter__ = Mock(return_value=tracker)
    bot = MaxBot(persistence_manager=Mock(return_value=mock), history_tracked=True)
    await bot.default_rpc_adapter({}, channel, "34")

    tracker.set_rpc_history.assert_called_once()


async def test_track_history_channel_default(channel):
    tracker = MagicMock()
    mock = MagicMock()
    mock.__enter__ = Mock(return_value=tracker)
    bot = MaxBot(persistence_manager=Mock(return_value=mock))
    await bot.default_channel_adapter("hey bot", channel)

    tracker.set_message_history.assert_not_called()


async def test_track_history_rpc_default(channel):
    tracker = MagicMock()
    mock = MagicMock()
    mock.__enter__ = Mock(return_value=tracker)
    bot = MaxBot(persistence_manager=Mock(return_value=mock))
    await bot.default_rpc_adapter({}, channel, "34")

    tracker.set_rpc_history.assert_not_called()
