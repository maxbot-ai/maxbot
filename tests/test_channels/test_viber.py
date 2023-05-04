import json
from unittest.mock import AsyncMock, Mock

import pytest
from sanic import Blueprint, Sanic

try:
    from viberbot import BotConfiguration
    from viberbot.api.viber_requests import ViberMessageRequest
except ImportError:
    pytest.skip("viber not installed", allow_module_level=True)

from maxbot import MaxBot
from maxbot.schemas import MessageSchema

API_TOKEN = "5f3fgc4de017e5af-8ea46569dc6b60d8-adf125afb5cfd2d1"
DEFAULT_AVATAR = "https://common.maxbot.ai/logo/viber_blue.jpg"
NAME = "MAXBOT"

USER_ID = "yJrPvKeVijZS45zGWhQoVA=="
API_URL = "https://chatapi.viber.com/pa"
MESSAGE_TEXT = "hello world"
IMAGE_URL = "http://example.com/123.jpg"

UPDATE_TEXT = {
    "event": "message",
    "timestamp": 1552550067857,
    "message_token": 5169578525269858576,
    "sender": {"id": USER_ID, "name": "user", "language": "ru", "country": "RU", "api_version": 4},
    "message": {"text": MESSAGE_TEXT, "type": "text", "media": "null", "thumbnail": "null"},
    "silent": False,
}

UPDATE_IMAGE = {
    "event": "message",
    "timestamp": 1552550067857,
    "message_token": 5169578525269858576,
    "sender": {"id": USER_ID, "name": "user", "language": "ru", "country": "RU", "api_version": 4},
    "message": {"type": "picture", "media": IMAGE_URL, "thumbnail": "null", "text": "CAPTION"},
    "silent": False,
}


@pytest.fixture
def builder():
    builder = MaxBot.builder()
    builder.use_inline_resources(
        f"""
        channels:
            viber:
                api_token: {API_TOKEN}
                avatar:  {DEFAULT_AVATAR}
                name: MAXBOT
    """
    )
    return builder


@pytest.fixture
def bot(builder):
    return builder.build()


@pytest.fixture
def dialog():
    return {"channel_name": "viber", "user_id": USER_ID}


async def test_create_dialog(bot, dialog):
    request = ViberMessageRequest().from_dict(UPDATE_TEXT)
    assert dialog == await bot.channels.viber.create_dialog(request)


async def test_send_text(bot, dialog, respx_mock):
    respx_mock.post(f"{API_URL}/send_message").respond(json={"status": 0, "message_token": "11"})

    await bot.channels.viber.call_senders(
        {"text": MESSAGE_TEXT},
        dialog,
    )

    request = respx_mock.calls.last.request
    assert json.loads(request.content) == {
        "type": "text",
        "text": MESSAGE_TEXT,
        "auth_token": API_TOKEN,
        "receiver": USER_ID,
        "sender": {"name": "MAXBOT", "avatar": DEFAULT_AVATAR},
    }


async def test_receive_text(bot):
    request = ViberMessageRequest().from_dict(UPDATE_TEXT)
    assert {"text": MESSAGE_TEXT} == await bot.channels.viber.call_receivers(request)


async def test_receive_image(bot):
    request = ViberMessageRequest().from_dict(UPDATE_IMAGE)
    message = await bot.channels.viber.call_receivers(request)
    MessageSchema().validate(message)
    assert message == {"image": {"url": IMAGE_URL, "caption": "CAPTION"}}


async def test_receive_unknown(bot):
    assert not await bot.channels.viber.call_receivers({})


async def test_send_image(bot, dialog, respx_mock):
    respx_mock.post(f"{API_URL}/send_message").respond(json={"status": 0, "message_token": "11"})

    await bot.channels.viber.call_senders(
        {"image": {"url": IMAGE_URL, "caption": MESSAGE_TEXT}}, dialog
    )

    request = respx_mock.calls.last.request
    assert json.loads(request.content) == {
        "auth_token": API_TOKEN,
        "media": IMAGE_URL,
        "receiver": USER_ID,
        "sender": {"avatar": DEFAULT_AVATAR, "name": NAME},
        "text": MESSAGE_TEXT,
        "type": "picture",
    }


async def test_send_error(bot, dialog, respx_mock):
    respx_mock.post(f"{API_URL}/send_message").respond(
        json={"status": 1, "status_message": "error reason"}
    )

    with pytest.raises(RuntimeError, match="failed with status: 1, message: error reason"):
        await bot.channels.viber.call_senders(
            {"text": MESSAGE_TEXT},
            dialog,
        )


async def test_sanic_endpoint(bot, respx_mock):
    callback = AsyncMock()

    app = Sanic(__name__)
    app.blueprint(bot.channels.viber.blueprint(callback))
    _, response = await app.asgi_client.post("/viber", json=UPDATE_TEXT)
    assert response.status_code == 204, response.text
    assert response.text == ""
    (viber_request, viber_channel) = callback.call_args.args
    assert str(viber_request) == str(ViberMessageRequest().from_dict(UPDATE_TEXT))
    assert viber_channel == bot.channels.viber


async def test_sanic_register_webhook(bot, respx_mock, monkeypatch):
    respx_mock.post(f"{API_URL}/set_webhook").respond(json={"status": 0, "event_types": []})
    monkeypatch.setattr(Blueprint, "after_server_start", Mock())

    bp = bot.channels.viber.blueprint(AsyncMock(), public_url="https://example.com/")
    for call in bp.after_server_start.call_args_list:
        (coro,) = call.args
        await coro(Mock(), Mock())

    request = respx_mock.calls.last.request
    assert json.loads(request.content) == {
        "auth_token": API_TOKEN,
        "url": "https://example.com/viber",
    }


async def test_get_avatar_and_name(dialog, respx_mock):
    name = "NAME_FROM_get_account_info"
    avatar = "ICON_FROM_get_account_info"
    respx_mock.post(f"{API_URL}/get_account_info").respond(
        json={"status": 0, "name": name, "icon": avatar}
    )
    respx_mock.post(f"{API_URL}/send_message").respond(json={"status": 0, "message_token": "11"})

    builder = MaxBot.builder()
    builder.use_inline_resources(
        f"""
        channels:
            viber:
                api_token: {API_TOKEN}
    """
    )
    bot = builder.build()
    await bot.channels.viber.call_senders({"text": MESSAGE_TEXT}, dialog)

    request = respx_mock.calls.last.request
    assert json.loads(request.content) == {
        "type": "text",
        "text": MESSAGE_TEXT,
        "auth_token": API_TOKEN,
        "receiver": USER_ID,
        "sender": {"name": name, "avatar": avatar},
    }
