from unittest.mock import AsyncMock, sentinel

import pytest

from maxbot import MaxBot
from maxbot.channels import Channel, ChannelFactory, ChannelManager, ChannelsCollection
from maxbot.channels._manager import BUILTIN_CHANNELS
from maxbot.maxml import Schema, fields
from maxbot.resources import InlineResources


def create_mixin_mock():
    class MyChannel:
        create_dialog = AsyncMock()
        receive_text = AsyncMock()
        send_text = AsyncMock()

    return MyChannel


@pytest.fixture
def mixin_mock():
    return create_mixin_mock()


@pytest.fixture
def my_channel(mixin_mock):
    factory = ChannelFactory("my_channel")
    factory.add_mixin(mixin_mock)
    return factory.create_instance()


def test_create_instance_missing_mixins():
    factory = ChannelFactory("my_channel")
    with pytest.raises(TypeError):
        factory.create_instance()


async def test_create_dialog(my_channel, mixin_mock):
    mixin_mock.create_dialog.return_value = sentinel.dialog
    assert await my_channel.create_dialog(sentinel.data) == sentinel.dialog
    mixin_mock.create_dialog.assert_called_once_with(sentinel.data)


async def test_receiver_none(my_channel, mixin_mock):
    mixin_mock.receive_text.return_value = None
    assert await my_channel.call_receivers(sentinel.data) is None
    mixin_mock.receive_text.assert_awaited_once_with(sentinel.data)


async def test_receiver_message(mixin_mock):
    mixin_mock.receive_text.return_value = None
    # hooks are sorted by their names, we add the hook at the end
    mixin_mock.receive_xxx = AsyncMock(return_value=sentinel.message)

    my_channel = ChannelFactory("my_channel").add_mixin(mixin_mock).create_instance()

    assert await my_channel.call_receivers(sentinel.data) == sentinel.message
    mixin_mock.receive_text.assert_awaited_once_with(sentinel.data)
    mixin_mock.receive_xxx.assert_awaited_once_with(sentinel.data)


async def test_receiver_replace():
    mixin1 = create_mixin_mock()
    mixin2 = create_mixin_mock()
    mixin2.receive_text.return_value = sentinel.message

    my_channel = ChannelFactory("my_channel").add_mixin(mixin1).add_mixin(mixin2).create_instance()

    assert await my_channel.call_receivers(sentinel.data) == sentinel.message
    assert not mixin1.receive_text.called


async def test_sender_command(mixin_mock):
    mixin_mock.send_xxx = AsyncMock()

    my_channel = ChannelFactory("my_channel").add_mixin(mixin_mock).create_instance()
    command = {"xxx": sentinel.command}

    await my_channel.call_senders(command, sentinel.dialog)
    mixin_mock.send_xxx.assert_awaited_once_with(command, sentinel.dialog)


async def test_sender_unknown_command(my_channel):
    with pytest.raises(ValueError):
        await my_channel.call_senders({"unknown": sentinel.command}, sentinel.dialog)


async def test_sender_replace():
    mixin1 = create_mixin_mock()
    mixin2 = create_mixin_mock()
    mixin2.send_text.return_value = sentinel.message

    my_channel = ChannelFactory("my_channel").add_mixin(mixin1).add_mixin(mixin2).create_instance()

    command = {"text": sentinel.command}

    await my_channel.call_senders(command, sentinel.dialog)
    assert not mixin1.receive_text.called
    mixin2.send_text.assert_awaited_once_with(command, sentinel.dialog)


def test_channel_config(mixin_mock):
    class MyChannel:
        class ConfigSchema(Schema):
            xxx = fields.String()

    channels = (
        ChannelManager()
        .add_mixin(mixin_mock, "my_channel")
        .add_mixin(MyChannel, "my_channel")
        .create_channels(
            InlineResources(
                """
                channels:
                    my_channel: {xxx: yyy}
            """
            )
        )
    )

    assert channels.my_channel.config == {"xxx": "yyy"}


def test_builtin_channel(monkeypatch, mixin_mock):
    global MyChannel
    MyChannel = mixin_mock
    monkeypatch.setitem(BUILTIN_CHANNELS, "my_channel", f"{__name__}.MyChannel")

    manager = ChannelManager()
    assert not manager.factories["my_channel"].loaded  # ensure lazy load

    channels = manager.create_channels(
        InlineResources(
            """
                channels:
                    my_channel: {}
            """
        )
    )

    assert isinstance(channels.my_channel, (MyChannel, Channel))


def test_channels_collection():
    assert bool(ChannelsCollection.empty()) is False

    channels = ChannelsCollection([sentinel.channel1, sentinel.channel2])

    assert list(iter(channels)) == [sentinel.channel1, sentinel.channel2]
    assert channels.names == {"channel1", "channel2"}
    assert channels.channel1 == sentinel.channel1
    assert channels.channel2 == sentinel.channel2
    assert channels.get("channel1") == sentinel.channel1
    assert channels.get("channel2") == sentinel.channel2

    with pytest.raises(AttributeError, match="Unknown channel 'xxx'"):
        channels.xxx
