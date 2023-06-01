import json
import logging
from unittest.mock import AsyncMock, Mock

import pytest
from sanic import Sanic

from maxbot import MaxBot
from maxbot.channels.facebook import Gateway
from maxbot.schemas import MessageSchema

API_URL = "https://graph.facebook.com/v15.0"
FB_APP_SECRET = "4fdfac4de0e7e5af-8ea26569db6b60d8-adf115afb5cfe2d0"
USER_ID = 12345
MESSAGE_TEXT = "hello world"
IMAGE_URL = "http://example.com/123.jpg"
IMAGE_URL_2 = "http://example.com/456.jpg"
ACCESS_TOKEN = "a2140b9e102c75db7cbe938d053b5843"
CONFIRMATION_CODE = "1a2b3c"


UPDATE_TEXT = {
    "object": "page",
    "entry": [
        {
            "id": "1838527126483620460",
            "time": 1536239175555,
            "messaging": [
                {
                    "sender": {"id": 24523},
                    "recipient": {"id": USER_ID},
                    "timestamp": 1536239175164,
                    "message": {"mid": "mid_key", "seq": 100, "text": MESSAGE_TEXT},
                }
            ],
        }
    ],
}

UPDATE_IMAGE = {
    "object": "page",
    "entry": [
        {
            "id": "1838527126483620460",
            "time": 1536262215747,
            "messaging": [
                {
                    "sender": {"id": 54321},
                    "recipient": {"id": USER_ID},
                    "timestamp": 1536262215171,
                    "message": {
                        "mid": "mid_key",
                        "seq": 2760,
                        "attachments": [
                            {"type": "document", "payload": {"url": IMAGE_URL_2}},
                            {"type": "image", "payload": {"url": IMAGE_URL}},
                            {"type": "image", "payload": {"url": IMAGE_URL_2}},
                        ],
                    },
                }
            ],
        }
    ],
}


@pytest.fixture
def builder():
    builder = MaxBot.builder()
    builder.use_inline_resources(
        f"""
        channels:
            facebook:
                app_secret: {FB_APP_SECRET}
                access_token: {ACCESS_TOKEN}
    """
    )
    return builder


@pytest.fixture
def bot(builder):
    return builder.build()


@pytest.fixture
def dialog():
    return {"channel_name": "facebook", "user_id": str(USER_ID)}


async def test_create_dialog(bot, dialog):
    messaging = UPDATE_TEXT["entry"][0]["messaging"][0]
    assert dialog == await bot.channels.facebook.create_dialog(messaging=messaging)


async def test_create_dialog_no_recipient(bot, dialog):
    assert not await bot.channels.facebook.create_dialog(messaging={})


async def test_send_text(bot, dialog, respx_mock):
    respx_mock.post(f"{API_URL}/me/messages?access_token={ACCESS_TOKEN}").respond(json={})
    text = Mock()
    text.render = Mock(return_value=MESSAGE_TEXT)
    await bot.channels.facebook.call_senders({"text": text}, dialog)
    request = respx_mock.calls.last.request
    assert json.loads(request.content) == {
        "recipient": {"id": str(USER_ID)},
        "message": {"text": MESSAGE_TEXT},
        "messaging_type": "RESPONSE",
    }


async def test_receive_text(bot):
    messaging = UPDATE_TEXT["entry"][0]["messaging"][0]
    assert {"text": MESSAGE_TEXT} == await bot.channels.facebook.call_receivers(messaging)


async def test_receive_image(bot):
    messaging = UPDATE_IMAGE["entry"][0]["messaging"][0]
    message = await bot.channels.facebook.call_receivers(messaging)
    MessageSchema().validate(message)
    assert message == {"image": {"url": IMAGE_URL}}


async def test_receive_unknown(bot):
    assert not await bot.channels.facebook.call_receivers({})


async def test_send_image(bot, dialog, respx_mock):
    respx_mock.post(f"{API_URL}/me/messages?access_token={ACCESS_TOKEN}").respond(
        json={"status": 0, "message_token": "11"}
    )

    caption = Mock()
    caption.render = Mock(return_value=MESSAGE_TEXT)
    await bot.channels.facebook.call_senders(
        {"image": {"url": IMAGE_URL, "caption": caption}}, dialog
    )
    request = respx_mock.calls[0].request
    assert json.loads(request.content) == {
        "recipient": {"id": str(USER_ID)},
        "message": {"text": MESSAGE_TEXT},
        "messaging_type": "RESPONSE",
    }
    request = respx_mock.calls[1].request
    assert json.loads(request.content) == {
        "recipient": {"id": str(USER_ID)},
        "message": {
            "attachment": {"type": "image", "payload": {"is_reusable": True, "url": IMAGE_URL}}
        },
    }

    await bot.channels.facebook.call_senders({"image": {"url": IMAGE_URL}}, dialog)
    request = respx_mock.calls[2].request
    assert json.loads(request.content) == {
        "recipient": {"id": str(USER_ID)},
        "message": {
            "attachment": {"type": "image", "payload": {"is_reusable": True, "url": IMAGE_URL}}
        },
    }


async def test_sanic_endpoint(bot):
    callback = AsyncMock()

    app = Sanic(__name__)
    app.blueprint(bot.channels.facebook.blueprint(callback))
    _, response = await app.asgi_client.post(
        "/facebook",
        json=UPDATE_TEXT,
        headers={"X-Hub-Signature": "sha1=d2b1782caeffa23acfad404ab627f0a774794510"},
    )
    assert response.status_code == 204
    assert response.text == ""
    callback.assert_called_once_with(UPDATE_TEXT["entry"][0]["messaging"][0])

    _, response = await app.asgi_client.post("/facebook", json=UPDATE_TEXT)
    assert response.status_code == 403

    _, response = await app.asgi_client.post(
        "/facebook", json=UPDATE_TEXT, headers={"X-Hub-Signature": "md=1"}
    )
    assert response.status_code == 501

    _, response = await app.asgi_client.post(
        "/facebook", json=UPDATE_TEXT, headers={"X-Hub-Signature": "sha1=1"}
    )
    assert response.status_code == 403


async def test_sanic_register_webhook(bot, caplog):
    with caplog.at_level(logging.WARNING):
        bot.channels.facebook.blueprint(AsyncMock(), public_url="https://example.com/")
    assert (
        "The facebook platform has no suitable api, register a webhook yourself https://example.com/facebook."
    ) in caplog.text
