import json
import logging
from unittest.mock import AsyncMock, Mock

import pytest
from sanic import Sanic

from maxbot import MaxBot
from maxbot.channels.vk import Gateway
from maxbot.errors import BotError
from maxbot.schemas import MessageSchema

VK_ACCESS_TOKEN = "4fdfac4de0e7e5af-8ea26569db6b60d8-adf115afb5cfe2d0"
USER_ID = 12345
VK_GROUP_ID = 12345678
VK_CONFIRM_SECRET = "confirm"
API_URL = "https://api.vk.com/method"
MESSAGE_TEXT = "hello world"
IMAGE_URL = "http://example.com/123.jpg"
IMAGE_URL_WITHOUT_EXT = "http://example.com/123"
IMAGE_URL_2 = "http://example.com/1234.jpg"

UPDATE_TEXT = {
    "type": "message_new",
    "secret": "unittest",
    "object": {
        "message": {
            "date": 1533043910,
            "from_id": USER_ID,
            "text": MESSAGE_TEXT,
            "random_id": 0,
            "attachments": [],
            "is_hidden": False,
        },
    },
    "group_id": VK_GROUP_ID,
}

ATTACHMENTS = [
    {
        "type": "photo",
        "photo": {
            "id": 456239467,
            "album_id": -15,
            "owner_id": 1983541,
            "sizes": [
                {"type": "o", "url": IMAGE_URL_2, "width": 130, "height": 120},
                {"type": "o", "url": IMAGE_URL, "width": 130, "height": 130},
            ],
            "text": "",
            "access_key": "94016eaf12fc0533bb",
        },
    }
]

UPDATE_IMAGE = {
    "type": "message_new",
    "secret": "unittest",
    "object": {
        "message": {
            "date": 1530010106,
            "from_id": USER_ID,
            "attachments": ATTACHMENTS,
            "text": "CAPTION",
        }
    },
    "group_id": VK_GROUP_ID,
}

UPDATE_CONFIRM = {"type": "confirmation", "group_id": VK_GROUP_ID}


@pytest.fixture
def builder():
    builder = MaxBot.builder()
    builder.use_inline_resources(
        f"""
        channels:
            vk:
               confirm_secret: {VK_CONFIRM_SECRET}
               access_token: {VK_ACCESS_TOKEN}
               group_id: {VK_GROUP_ID}
    """
    )
    return builder


@pytest.fixture
def bot(builder):
    return builder.build()


@pytest.fixture
def dialog():
    return {"channel_name": "vk", "user_id": str(USER_ID)}


async def test_create_dialog(bot, dialog):
    incoming_message = UPDATE_IMAGE["object"]["message"]
    assert dialog == await bot.channels.vk.create_dialog(incoming_message)
    incoming_message = UPDATE_TEXT["object"]["message"]
    assert dialog == await bot.channels.vk.create_dialog(incoming_message)


async def test_send_text(bot, dialog, respx_mock):
    respx_mock.post(f"{API_URL}/messages.send").respond(json={"response": 1})

    text = Mock()
    text.render = Mock(return_value=MESSAGE_TEXT)
    await bot.channels.vk.call_senders(
        command={"text": text},
        dialog=dialog,
    )

    request = respx_mock.calls.last.request
    assert (
        json.loads(request.content).items()
        >= {
            "message": MESSAGE_TEXT,
            "user_id": USER_ID,
            "v": Gateway.API_VERSION,
            "access_token": VK_ACCESS_TOKEN,
        }.items()
    )


async def test_send_text_error(bot, dialog, respx_mock):
    respx_mock.post(f"{API_URL}/messages.send").respond(json={"error": "error_code"})
    text = Mock()
    text.render = Mock(return_value=MESSAGE_TEXT)
    with pytest.raises(RuntimeError):
        await bot.channels.vk.call_senders({"text": text}, dialog)


async def test_receive_text(bot):
    incoming_message = UPDATE_TEXT["object"]["message"]
    assert {"text": MESSAGE_TEXT} == await bot.channels.vk.call_receivers(incoming_message)


async def test_receive_image(bot):
    incoming_message = UPDATE_IMAGE["object"]["message"]
    message = await bot.channels.vk.call_receivers(incoming_message)
    MessageSchema().validate(message)
    assert message == {"image": {"url": IMAGE_URL, "caption": "CAPTION"}}


async def test_receive_unknown(bot):
    assert not await bot.channels.vk.call_receivers({})


@pytest.mark.parametrize(
    "url,headers",
    [
        (IMAGE_URL, {}),
        (IMAGE_URL_WITHOUT_EXT, {}),
        (IMAGE_URL, {"content-disposition": "attachment; filename=FILENAME.png"}),
    ],
)
async def test_send_image(bot, dialog, url, headers, respx_mock):
    respx_mock.get(url).respond(
        headers={"content-type": "image/jpeg", **headers}, stream=b"image contents"
    )
    respx_mock.post(f"{API_URL}/photos.getMessagesUploadServer").respond(
        json={"response": {"upload_url": "http://upload_photo.vk"}}
    )
    respx_mock.post("http://upload_photo.vk").respond(
        json={"photo": "file_id", "server": "server_vk", "hash": "hash_vk"}
    )
    respx_mock.post(f"{API_URL}/photos.saveMessagesPhoto").respond(
        json={"response": [{"owner_id": 121, "id": 212}]}
    )
    respx_mock.post(f"{API_URL}/messages.send").respond(json={"response": 1})

    caption = Mock()
    caption.render = Mock(return_value=MESSAGE_TEXT)
    await bot.channels.vk.call_senders({"image": {"url": url, "caption": caption}}, dialog)

    request = respx_mock.calls[0].request
    assert str(request.url) == url

    request = respx_mock.calls[1].request
    assert request.url.path.endswith("photos.getMessagesUploadServer")
    assert (
        json.loads(request.content).items()
        > {"v": Gateway.API_VERSION, "access_token": VK_ACCESS_TOKEN}.items()
    )

    request = respx_mock.calls[2].request
    assert str(request.url) == "http://upload_photo.vk/"

    request = respx_mock.calls[3].request
    assert request.url.path.endswith("photos.saveMessagesPhoto")
    assert (
        json.loads(request.content).items()
        > {
            "server": "server_vk",
            "photo": "file_id",
            "hash": "hash_vk",
            "v": Gateway.API_VERSION,
            "access_token": VK_ACCESS_TOKEN,
        }.items()
    )

    request = respx_mock.calls[4].request
    assert request.url.path.endswith("messages.send")
    assert (
        json.loads(request.content).items()
        > {
            "attachment": "photo121_212",
            "user_id": USER_ID,
            "message": MESSAGE_TEXT,
            "v": Gateway.API_VERSION,
            "access_token": VK_ACCESS_TOKEN,
        }.items()
    )


async def test_send_image_error(bot, dialog, respx_mock):
    respx_mock.post(f"{API_URL}/photos.getMessagesUploadServer").respond(
        json={"response": {"error": "error_code"}}
    )
    respx_mock.get(IMAGE_URL).respond(stream=b"image contents")
    with pytest.raises(RuntimeError):
        await bot.channels.vk.call_senders(
            command={"image": {"url": IMAGE_URL, "caption": MESSAGE_TEXT}}, dialog=dialog
        )


async def test_sanic_endpoint(bot):
    callback = AsyncMock()

    app = Sanic(__name__)
    app.blueprint(bot.channels.vk.blueprint(callback))

    _, response = await app.asgi_client.post("/vk", json=UPDATE_TEXT)
    assert response.status_code == 200, response.text
    assert response.text == "ok"
    callback.assert_called_once_with(UPDATE_TEXT["object"]["message"], bot.channels.vk)

    _, response = await app.asgi_client.post("/vk", json=UPDATE_CONFIRM)
    assert response.status_code == 200, response.text
    assert response.text == "confirm"

    _, response = await app.asgi_client.post(
        "/vk", json={"type": "confirmation", "group_id": 12345}
    )
    assert response.status_code == 400, response.text


async def test_sanic_register_webhook(bot, caplog):
    with caplog.at_level(logging.WARNING):
        bot.channels.vk.blueprint(AsyncMock(), public_url="https://example.com/")
    assert (
        "The vk platform has no suitable api, register a webhook yourself https://example.com/vk."
    ) in caplog.text
