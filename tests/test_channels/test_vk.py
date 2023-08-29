import logging
import urllib.parse
from unittest.mock import AsyncMock, Mock

import pytest
from sanic import Blueprint, Sanic

from maxbot import MaxBot
from maxbot.channels.vk import Gateway
from maxbot.schemas import MessageSchema

VK_ACCESS_TOKEN = "4fdfac4de0e7e5af-8ea26569db6b60d8-adf115afb5cfe2d0"
USER_ID = 12345
VK_GROUP_ID = 12345678
VK_CONFIRM_SECRET = "confirm"
SECRET_KEY = "secret"
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
               access_token: {VK_ACCESS_TOKEN}
               group_id: {VK_GROUP_ID}
               secret_key: {SECRET_KEY}
    """
    )
    return builder


@pytest.fixture
def bot(builder):
    return builder.build()


@pytest.fixture
def dialog():
    return {"channel_name": "vk", "user_id": str(USER_ID)}


def get_dict(content):
    return dict([(k, v[0]) for k, v in urllib.parse.parse_qs(content.decode("utf-8")).items()])


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
        get_dict(request.content).items()
        >= {
            "message": MESSAGE_TEXT,
            "user_id": str(USER_ID),
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
        get_dict(request.content).items()
        > {"v": Gateway.API_VERSION, "access_token": VK_ACCESS_TOKEN}.items()
    )

    request = respx_mock.calls[2].request
    assert str(request.url) == "http://upload_photo.vk/"

    request = respx_mock.calls[3].request
    assert request.url.path.endswith("photos.saveMessagesPhoto")
    assert (
        get_dict(request.content).items()
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
        get_dict(request.content).items()
        > {
            "attachment": "photo121_212",
            "user_id": str(USER_ID),
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


def _webhook_mock(bot, respx_mock, monkeypatch, responses, webhook=None):
    app = Sanic(__name__)
    monkeypatch.setattr(Blueprint, "after_server_start", Mock())

    async def execute_once(app, fn):
        await fn()

    bp = bot.channels.vk.blueprint(
        AsyncMock(), execute_once, public_url=webhook or "http://webhook"
    )
    app.blueprint(bp)
    while len(responses) < 5:
        responses.append({})
    respx_mock.post(f"{API_URL}/groups.getCallbackServers").respond(json=responses[0])
    respx_mock.post(f"{API_URL}/groups.deleteCallbackServer").respond(json=responses[1])
    respx_mock.post(f"{API_URL}/groups.addCallbackServer").respond(json=responses[2])
    respx_mock.post(f"{API_URL}/groups.setCallbackSettings").respond(json=responses[3])
    respx_mock.post(f"{API_URL}/groups.getCallbackConfirmationCode").respond(json=responses[4])
    return app, bp


async def test_set_webhook(bot, respx_mock, monkeypatch):
    confirm_code = "123456"
    old_server1, old_server2, new_server = 11, 22, 33
    webhook = "https://webhook.ai/"
    responses = [
        {"response": {"items": [{"id": old_server1}, {"id": old_server2}]}},
        {"response": 1},
        {"response": {"server_id": new_server}},
        {"response": 1},
        {"response": {"code": confirm_code}},
    ]
    app, bp = _webhook_mock(bot, respx_mock, monkeypatch, responses, webhook)

    for call in bp.after_server_start.call_args_list:
        (coro,) = call.args
        await coro(Mock(), Mock())

    calls = respx_mock.calls
    assert len(calls) == 6
    expected = {"v": "5.131", "access_token": VK_ACCESS_TOKEN, "group_id": str(VK_GROUP_ID)}
    assert get_dict(calls[0].request.content) == expected
    assert get_dict(calls[1].request.content) == dict(
        **expected, **{"server_id": str(old_server1)}
    )
    assert get_dict(calls[2].request.content) == dict(
        **expected, **{"server_id": str(old_server2)}
    )
    data = {"secret_key": SECRET_KEY, "title": "MAXBOT", "url": f"{webhook}vk"}
    assert get_dict(calls[3].request.content) == dict(**expected, **data)
    data = {
        "api_version": "5.131",
        "message_allow": "1",
        "message_deny": "1",
        "message_new": "1",
        "message_reply": "1",
        "server_id": str(new_server),
    }
    assert get_dict(calls[4].request.content) == dict(**expected, **data)
    assert get_dict(calls[5].request.content) == expected

    _, response = await app.asgi_client.post("/vk", json=UPDATE_CONFIRM)
    assert response.status_code == 200, response.text
    assert response.text == confirm_code


async def _assert_webhhok_error(bp, respx_mock, count):
    with pytest.raises(RuntimeError):
        for call in bp.after_server_start.call_args_list:
            (coro,) = call.args
            await coro(Mock(), Mock())
    calls = respx_mock.calls
    assert len(calls) == count


async def test_get_callback_error(bot, respx_mock, monkeypatch):
    responses = [{"error": {"error_code": 10}}]
    app, bp = _webhook_mock(bot, respx_mock, monkeypatch, responses)
    await _assert_webhhok_error(bp, respx_mock, count=1)


async def test_set_callback_error(bot, respx_mock, monkeypatch):
    responses = [
        {"response": {"items": [{"id": 1}, {"id": 2}]}},
        {"response": 0},
        {"error": {"error_code": 10}},
    ]
    app, bp = _webhook_mock(bot, respx_mock, monkeypatch, responses)
    await _assert_webhhok_error(bp, respx_mock, count=4)


async def test_callback_settings_error(bot, respx_mock, monkeypatch):
    responses = [
        {"response": {"items": [{"id": 1}, {"id": 2}]}},
        {"response": 1},
        {"response": {"server_id": 3}},
        {"response": 0},
    ]
    app, bp = _webhook_mock(bot, respx_mock, monkeypatch, responses)
    await _assert_webhhok_error(bp, respx_mock, count=5)


async def test_confirm_code_error(bot, respx_mock, monkeypatch):
    responses = [
        {"response": {"items": [{"id": 1}, {"id": 2}]}},
        {"response": 1},
        {"response": {"server_id": 3}},
        {"response": 1},
        {"error": {"error_code": 10}},
    ]
    app, bp = _webhook_mock(bot, respx_mock, monkeypatch, responses)
    await _assert_webhhok_error(bp, respx_mock, count=6)


async def test_sanic_endpoint(bot):
    callback = AsyncMock()

    app = Sanic(__name__)
    app.blueprint(bot.channels.vk.blueprint(callback, None))

    _, response = await app.asgi_client.post("/vk", json=UPDATE_TEXT)
    assert response.status_code == 200, response.text
    assert response.text == "ok"
    callback.assert_called_once_with(UPDATE_TEXT["object"]["message"], bot.channels.vk)

    _, response = await app.asgi_client.post(
        "/vk", json={"type": "confirmation", "group_id": 12345}
    )
    assert response.status_code == 400, response.text

    _, response = await app.asgi_client.post(
        "/vk", json={"type": "confirmation", "group_id": VK_GROUP_ID}
    )
    assert response.status_code == 500, response.text


async def test_skip_register_webhook(bot, caplog):
    builder = MaxBot.builder()
    builder.use_inline_resources(
        f"""     channels:
                    vk:
                       access_token: {VK_ACCESS_TOKEN}
        """
    )
    bot = builder.build()

    async def execute_once(app, fn):
        await fn()

    with caplog.at_level(logging.WARNING):
        bot.channels.vk.blueprint(AsyncMock(), execute_once, public_url="https://example.com/")
    assert (
        "Skip register webhook, set secret_key and group_id for register new webhook"
    ) in caplog.text


async def test_timeout_not_specified(bot, dialog, respx_mock):
    respx_mock.post(f"{API_URL}/messages.send").respond(json={"response": 1})

    text = Mock()
    text.render = Mock(return_value=MESSAGE_TEXT)
    await bot.channels.vk.call_senders(
        command={"text": text},
        dialog=dialog,
    )

    assert [c.request.extensions["timeout"] for c in respx_mock.calls] == [
        {"connect": 5.0, "pool": 5.0, "read": 5.0, "write": 5.0},
    ]


async def test_timeout(dialog, respx_mock):
    bot = MaxBot.inline(
        f"""
        channels:
            vk:
                access_token: {VK_ACCESS_TOKEN}
                group_id: {VK_GROUP_ID}
                secret_key: {SECRET_KEY}
                timeout:
                    default: 3.1
                    connect: 10
    """
    )
    respx_mock.post(f"{API_URL}/messages.send").respond(json={"response": 1})

    text = Mock()
    text.render = Mock(return_value=MESSAGE_TEXT)
    await bot.channels.vk.call_senders(
        command={"text": text},
        dialog=dialog,
    )

    assert [c.request.extensions["timeout"] for c in respx_mock.calls] == [
        {"connect": 10, "pool": 3.1, "read": 3.1, "write": 3.1},
    ]


async def test_send_image_timeout(bot, dialog, respx_mock):
    respx_mock.get(IMAGE_URL).respond(
        headers={"content-type": "image/jpeg"}, stream=b"image contents"
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
    await bot.channels.vk.call_senders({"image": {"url": IMAGE_URL, "caption": caption}}, dialog)

    assert [c.request.extensions["timeout"] for c in respx_mock.calls] == [
        {"connect": 30, "pool": 30, "read": 30, "write": 30},  # maxbot._download.HTTPX_CLIENT
        {"connect": 5.0, "pool": 5.0, "read": 5.0, "write": 5.0},
        {"connect": 5.0, "pool": 5.0, "read": 5.0, "write": 5.0},
        {"connect": 5.0, "pool": 5.0, "read": 5.0, "write": 5.0},
        {"connect": 5.0, "pool": 5.0, "read": 5.0, "write": 5.0},
    ]


async def test_limits():
    MaxBot.inline(
        f"""
        channels:
            vk:
                access_token: {VK_ACCESS_TOKEN}
                group_id: {VK_GROUP_ID}
                secret_key: {SECRET_KEY}
                limits:
                  max_keepalive_connections: 1
                  max_connections: 2
                  keepalive_expiry: 3
    """
    )
