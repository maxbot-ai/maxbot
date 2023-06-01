"""Viber Bots Channel."""
import logging
from functools import cached_property
from urllib.parse import urljoin

import httpx
from viberbot.api.messages import PictureMessage
from viberbot.api.messages.text_message import TextMessage
from viberbot.api.viber_requests import ViberMessageRequest, create_request
from viberbot.api.viber_requests.viber_request import ViberRequest

from ..maxml import Schema, fields

logger = logging.getLogger(__name__)


class Gateway:
    """Viber Gateway."""

    httpx_client = httpx.AsyncClient(base_url="https://chatapi.viber.com/pa", timeout=3)

    def __init__(self, api_token):
        """Create a new class instance.

        :param str auth_token: Viber auth token.
        """
        self.api_token = api_token

    async def send_request(self, method, payload=None):
        """Send request to Facebook.

        :param str method: Method to call.
        :param dict payload: Method params.
        :return dict: response data
        :raise RuntimeError: The server returned error.
        """
        response = await self.httpx_client.post(
            method, json={"auth_token": self.api_token, **(payload or {})}
        )
        response.raise_for_status()
        result = response.json()
        if result["status"] != 0:
            raise RuntimeError(
                f'failed with status: {result["status"]}, message: {result.get("status_message")}'
            )
        return result


class _Api:
    """Simple Viber Bot API client."""

    def __init__(self, gateway, name=None, avatar=None):
        self.gateway = gateway
        self._name = name
        self._avatar = avatar
        self._sender = {}

    async def _build_sender(self):
        account = {}
        if self._name is None or self._avatar is None:
            account = await self.gateway.send_request("get_account_info")
        self._sender["name"] = self._name or account["name"]
        avatar = self._avatar or account.get("icon")
        if avatar:
            self._sender["avatar"] = avatar
        return self._sender

    async def set_webhook(self, url):
        result = await self.gateway.send_request("set_webhook", {"url": url})
        return result["event_types"]

    async def send_message(self, to, message):
        """
        Send a message of any type.

        :param str to: Viber user id
        :param Message message: Message object to be sent
        :return str: token of the sent message
        :raise RuntimeError: invalid message.
        """
        result = await self.gateway.send_request(
            "send_message",
            {
                **self._remove_empty_fields(message.to_dict()),
                "receiver": to,
                "sender": self._sender or await self._build_sender(),
            },
        )
        return result["message_token"]

    def _remove_empty_fields(self, message):
        return {k: v for k, v in message.items() if v is not None}


class ViberChannel:
    """
    Channel for Viber Bots. See https://developers.viber.com/docs/api/rest-bot-api/.

    The implementation is based on viberbot library.
    See https://developers.viber.com/docs/api/python-bot-api/.

    You need to install additional dependencies to use this channel.
    Try `pip install -U maxbot[viber]`.
    """

    class ConfigSchema(Schema):
        """Configuration schema for viber bot."""

        # Authentication token to access viber bot api.
        # https://developers.viber.com/docs/api/rest-bot-api/#authentication-token
        api_token = fields.Str(required=True)

        # Bot name, See BotConfiguration
        # https://developers.viber.com/docs/api/python-bot-api/#firstly-lets-import-and-configure-our-bot
        # https://developers.viber.com/docs/api/python-bot-api/#userprofile-object
        name = fields.Str()

        # Bot avatar, See BotConfiguration
        # https://developers.viber.com/docs/api/python-bot-api/#firstly-lets-import-and-configure-our-bot
        # https://developers.viber.com/docs/api/python-bot-api/#userprofile-object
        avatar = fields.Str()

    @cached_property
    def _api(self):
        """Return viber api connected to your bot.

        See https://developers.viber.com/docs/api/python-bot-api/#api-class for more information about viber bot methods.

        :return Api:
        """
        return _Api(
            Gateway(self.config["api_token"]), self.config.get("name"), self.config.get("avatar")
        )

    async def create_dialog(self, request: ViberRequest):
        """Create a dialog object from the incomming update.

        :param ViberRequest request: an incoming update.
        :return dict: a dialog with the schema :class:`~maxbot.schemas.DialogSchema`
        """
        messenger_id = str(request.sender.id)
        return {"channel_name": "viber", "user_id": messenger_id}

    async def send_text(self, command: dict, dialog: dict):
        """Send an image command to the channel.

        See https://developers.viber.com/docs/api/python-bot-api/#apisend_messagesto-messages
        See https://developers.viber.com/docs/api/python-bot-api/#textmessage-object

        :param dict command: a command with the payload :attr:`~maxbot.schemas.CommandSchema.text`.
        :param dict dialog: a dialog we respond in, with the schema :class:`~maxbot.schemas.DialogSchema`
        """
        await self._api.send_message(dialog["user_id"], TextMessage(text=command["text"].render()))

    async def send_image(self, command: dict, dialog: dict):
        """Send an image command to the channel.

        See https://developers.viber.com/docs/api/python-bot-api/#apisend_messagesto-messages
        See https://developers.viber.com/docs/api/python-bot-api/#picturemessage-object

        :param dict command: a command with the payload :attr:`~maxbot.schemas.CommandSchema.image`.
        :param dict dialog: a dialog we respond in, with the schema :class:`~maxbot.schemas.DialogSchema`
        """
        caption = command["image"].get("caption")
        await self._api.send_message(
            dialog["user_id"],
            PictureMessage(
                media=command["image"]["url"], text=None if caption is None else caption.render()
            ),
        )

    async def receive_text(self, request: ViberRequest):
        """Receive an text message from the channel.

        See https://developers.viber.com/docs/api/rest-bot-api/#receive-message-from-user.
        See https://developers.viber.com/docs/api/python-bot-api/#vibermessagerequest-object.
        See https://developers.viber.com/docs/api/python-bot-api/#textmessage-object

        :param ViberRequest request: an incoming update.
        :return dict: a message with the payload :class:`~maxbot.schemas.MessageSchema.text`
        """
        if isinstance(request, ViberMessageRequest):
            message = request.message
            if isinstance(message, TextMessage):
                return {"text": message.text}
        return None

    async def receive_image(self, request: ViberRequest):
        """Receive an image message from the channel.

        See https://developers.viber.com/docs/api/rest-bot-api/#receive-message-from-user.
        See https://developers.viber.com/docs/api/python-bot-api/#vibermessagerequest-object.
        See https://developers.viber.com/docs/api/python-bot-api/#picturemessage-object

        :param ViberRequest request: an incoming update.
        :return dict: a message with the payload :class:`~maxbot.schemas.MessageSchema.image`
        """
        if isinstance(request, ViberMessageRequest):
            message = request.message
            if isinstance(message, PictureMessage) and message.media:
                content = {"image": {"url": message.media}}
                if message.text:
                    content["image"]["caption"] = message.text
                return content
        return None

    def blueprint(self, callback, public_url=None, webhook_path=None):
        """Create web application blueprint to receive incoming updates.

        :param callable callback: a callback for received messages.
        :param string public_url: Base url to register webhook.
        :param string webhook_path: An url path to receive incoming updates.
        :return Blueprint: Blueprint for sanic app.
        """
        from sanic import Blueprint
        from sanic.response import empty

        bp = Blueprint(self.name)

        if webhook_path is None:
            webhook_path = f"/{self.name}"

        @bp.post(webhook_path)
        async def webhook(request):
            request_data = create_request(request.json)
            if request_data.event_type == "message":
                await callback(request_data, self)
            return empty()

        if public_url:

            @bp.after_server_start
            async def register_webhook(app, loop):
                webhook_url = urljoin(public_url, webhook_path)
                await self._api.set_webhook(webhook_url)
                logger.info(f"Registered webhook {webhook_url}.")

        return bp
