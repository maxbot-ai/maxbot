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


async def test_state_store(channel):
    mock = MagicMock()
    bot = MaxBot(state_store=Mock(return_value=mock))
    await bot.default_channel_adapter("hey bot", channel)

    bot.state_store.assert_called_once_with({"channel_name": channel.name, "user_id": "23"})
    mock.__enter__.assert_called_once()
    mock.__exit__.assert_called_once()
