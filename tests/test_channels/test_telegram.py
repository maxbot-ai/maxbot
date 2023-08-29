import asyncio
import json
import threading
import time
from unittest.mock import AsyncMock, Mock

import pytest
from sanic import Blueprint, Sanic

try:
    from telegram import Bot, Update
except ImportError:
    pytest.skip("telegram not installed", allow_module_level=True)

from maxbot import MaxBot
from maxbot.schemas import MessageSchema

API_TOKEN = "110201543:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw"
API_URL = f"https://api.telegram.org/bot{API_TOKEN}"
USER_ID = 123456789
MESSAGE_TEXT = "hello world"
UPDATE_TEXT = {
    "update_id": 10,
    "message": {
        "message_id": 20,
        "from": {"id": USER_ID, "is_bot": False, "first_name": "name", "last_name": ""},
        "event": {"id": USER_ID, "first_name": "name", "last_name": "", "type": "private"},
        "date": 1535124996,
        "text": MESSAGE_TEXT,
    },
}
UPDATE_PHOTO = {
    "update_id": 11,
    "message": {
        "message_id": 892,
        "from": {"id": USER_ID, "is_bot": False, "first_name": "name", "last_name": ""},
        "event": {"id": USER_ID, "first_name": "name", "last_name": "", "type": "private"},
        "date": 1662724471,
        "photo": [
            {
                "file_unique_id": "AQADGL0xG-072Uh4",
                "height": 68,
                "file_size": 1212,
                "file_id": "AgACAgIAAxkBAAIDfGMbKXfhKTYRxvdl_0wS0zBOiK6YAAIYvTEb7TvZSP2JQK_5jziFAQADAgADcwADKQQ",
                "width": 90,
            },
            {
                "file_unique_id": "AQADGL0xG-072Uhy",
                "height": 130,
                "file_size": 4097,
                "file_id": "AgACAgIAAxkBAAIDfGMbKXfhKTYRxvdl_0wS0zBOiK6YAAIYvTEb7TvZSP2JQK_5jziFAQADAgADbQADKQQ",
                "width": 173,
            },
        ],
        "caption": MESSAGE_TEXT,
    },
}
UPDATE_START = {
    "update_id": 10,
    "message": {
        "date": 1534773696,
        "message_id": 45,
        "from": {
            "id": 1,
            "is_bot": False,
            "first_name": "name",
            "last_name": "",
            "language_code": "ru-RU",
        },
        "chat": {"id": 1, "first_name": "name", "last_name": "", "type": "private"},
        "entities": [{"offset": 0, "length": 6, "type": "bot_command"}],
    },
}


@pytest.fixture
def builder():
    builder = MaxBot.builder()
    builder.use_inline_resources(
        f"""
        channels:
            telegram:
                api_token: {API_TOKEN}
    """
    )
    return builder


@pytest.fixture
def bot(builder):
    return builder.build()


@pytest.fixture
def dialog():
    return {"channel_name": "telegram", "user_id": str(USER_ID)}


@pytest.fixture
def update_text(bot):
    return Update.de_json(UPDATE_TEXT, bot.channels.telegram.bot)


@pytest.fixture
def update_photo(bot):
    return Update.de_json(UPDATE_PHOTO, bot.channels.telegram.bot)


@pytest.fixture
def update_start(bot):
    return Update.de_json(UPDATE_START, bot.channels.telegram.bot)


async def test_create_dialog(update_text, bot, dialog):
    assert dialog == await bot.channels.telegram.create_dialog(update_text)


async def test_receive_text(update_text, bot):
    assert {"text": MESSAGE_TEXT} == await bot.channels.telegram.call_receivers(update_text)


async def test_receive_unknown(update_start, bot):
    assert not await bot.channels.telegram.call_receivers(update_start)


async def test_send_text(bot, dialog, respx_mock):
    respx_mock.post(f"{API_URL}/sendMessage").respond(json={"result": {}})
    text = Mock()
    text.render = Mock(return_value=MESSAGE_TEXT)
    await bot.channels.telegram.call_senders({"text": text}, dialog)
    request = respx_mock.calls.last.request
    assert request.content == b"chat_id=123456789&text=hello+world"


async def test_receive_image(update_photo, bot, respx_mock):
    respx_mock.post(f"{API_URL}/getFile").respond(
        json={
            "result": {
                "file_id": "AgACAgIAAxkBAAIDfGMbKXfhKTYRxvdl_0wS0zBOiK6YAAIYvTEb7TvZSP2JQK_5jziFAQADAgADbQADKQQ",
                "file_unique_id": "AQADGL0xG-072Uhy",
                "file_path": "123.jpg",
                "file_size": 4097,
            }
        }
    )
    message = await bot.channels.telegram.call_receivers(update_photo)
    MessageSchema().validate(message)
    assert message == {
        "image": {
            "url": f"https://api.telegram.org/file/bot{API_TOKEN}/123.jpg",
            "size": 4097,
            "caption": MESSAGE_TEXT,
        }
    }


async def test_send_image(bot, dialog, respx_mock):
    respx_mock.post(f"{API_URL}/sendPhoto").respond(json={"result": {}})

    url = "http://example.com/123.jpg"
    caption = Mock()
    caption.render = Mock(return_value=MESSAGE_TEXT)
    await bot.channels.telegram.call_senders(
        {"image": {"url": url, "caption": caption}},
        dialog,
    )
    request = respx_mock.calls.last.request
    assert (
        request.content
        == b"chat_id=123456789&photo=http%3A%2F%2Fexample.com%2F123.jpg&caption=hello+world"
    )


async def test_send_image_from_tg(bot, dialog, respx_mock):
    respx_mock.post(f"{API_URL}/sendPhoto").respond(json={"result": {}})
    url = "https://api.telegram.org/file/bot110201543/photos/file_21.jpg"
    respx_mock.get(url).respond(stream=b"IMAGE_CONTENT")

    await bot.channels.telegram.call_senders({"image": {"url": url}}, dialog)

    request = respx_mock.calls.last.request
    assert b"123456789" in request.content
    assert b"IMAGE_CONTENT" in request.content


async def test_sanic_endpoint(bot, respx_mock, update_text):
    callback = AsyncMock()

    app = Sanic(__name__)
    app.blueprint(bot.channels.telegram.blueprint(callback, None))
    _, response = await app.asgi_client.post("/telegram", json=UPDATE_TEXT)
    assert response.status_code == 204, response.text
    assert response.text == ""
    callback.assert_called_once_with(update_text, bot.channels.telegram)


async def test_sanic_register_webhook(bot, respx_mock, monkeypatch):
    respx_mock.post(f"{API_URL}/setWebhook").respond(json={"result": {}})
    monkeypatch.setattr(Blueprint, "after_server_start", Mock())

    async def execute_once(app, fn):
        await fn()

    bp = bot.channels.telegram.blueprint(
        AsyncMock(), execute_once, public_url="https://example.com/"
    )
    for call in bp.after_server_start.call_args_list:
        (coro,) = call.args
        await coro(Mock(), Mock())

    request = respx_mock.calls.last.request
    assert request.content == b"url=https%3A%2F%2Fexample.com%2Ftelegram"


async def test_timeout_not_specified(bot, respx_mock, dialog):
    respx_mock.post(f"{API_URL}/sendMessage").respond(json={"result": {}})
    text = Mock()
    text.render = Mock(return_value=MESSAGE_TEXT)

    await bot.channels.telegram.call_senders({"text": text}, dialog)
    assert [c.request.extensions["timeout"] for c in respx_mock.calls] == [
        {"connect": 5.0, "read": 5.0, "write": 5.0, "pool": 5.0},
    ]


async def test_timeout_send_photo(respx_mock, dialog):
    bot = MaxBot.inline(
        f"""
        channels:
            telegram:
                api_token: {API_TOKEN}
                timeout:
                  default: 3.5
                  connect: 1.0
    """
    )
    respx_mock.post(f"{API_URL}/sendPhoto").respond(json={"result": {}})
    url = "https://api.telegram.org/file/bot110201543/photos/file_21.jpg"
    respx_mock.get(url).respond(stream=b"IMAGE_CONTENT")

    await bot.channels.telegram.call_senders({"image": {"url": url}}, dialog)
    assert [c.request.extensions["timeout"] for c in respx_mock.calls] == [
        {"connect": 1.0, "read": 3.5, "write": 3.5, "pool": 3.5},
        {"connect": 1.0, "read": 3.5, "write": 20, "pool": 3.5},  # send_photo(write_timeout=20)
    ]


async def test_limits():
    MaxBot.inline(
        f"""
        channels:
            telegram:
                api_token: {API_TOKEN}
                limits:
                  max_keepalive_connections: 1
                  max_connections: 2
                  keepalive_expiry: 3
    """
    )
