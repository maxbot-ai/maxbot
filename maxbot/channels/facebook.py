"""Facebook Bots Channel."""
import hmac
import logging
from functools import cached_property
from urllib.parse import urljoin

import httpx

from ..maxml import Schema, fields

logger = logging.getLogger(__name__)


class Gateway:
    """Facebook sender and verifier incoming messages."""

    # Facebook graph api version with which this gateway is well tested.
    # @See https://developers.facebook.com/docs/graph-api/guides/versioning
    httpx_client = httpx.AsyncClient(base_url="https://graph.facebook.com/v15.0", timeout=3)

    def __init__(self, app_secret, access_token):
        """Create a new class instance.

        :param str app_secret: Facebook application secret
        :param str access_token: Facebook access_token
        """
        self.app_secret = app_secret
        self.access_token = access_token

    async def send_request(self, json_data):
        """Send request to Facebook.

        :param dict json_data: additional params
        :return dict: response data
        """
        url = f"/me/messages?access_token={self.access_token}"
        response = await self.httpx_client.post(url, json=json_data)
        response.raise_for_status()
        return response.json()

    def verify_token(self, data, headers):
        """Validate Payloads.

        @See https://developers.facebook.com/docs/messenger-platform/webhooks#event-notifications

        :param bytes data: request.data
        :param dict headers: request.headers
        :return http status
        """
        header_signature = headers.get("x-hub-signature")
        if header_signature is None:
            return 403
        sha_name, signature = header_signature.split("=")
        if sha_name != "sha1":
            return 501
        mac = hmac.new(bytes(self.app_secret, "utf-8"), msg=data, digestmod="sha1").hexdigest()
        if not hmac.compare_digest(mac, signature):
            return 403
        return 200


class _Api:
    """Simple Facebook graph api client.

    * send text message
    * send image message
    """

    def __init__(self, gateway):
        """Create a new class instance.

        :param Gateway gateway
        """
        self.gateway = gateway

    async def send_text(self, recipient_id, text):
        """Send text message.

        @See https://developers.facebook.com/docs/messenger-platform/reference/send-api/

        :param str recipient_id: Facebook recipient.id
        :param str text: Message text
        """
        params = {
            "recipient": {"id": recipient_id},
            "message": {"text": text},
            "messaging_type": "RESPONSE",
        }
        await self.gateway.send_request(params)

    async def send_image(self, recipient_id, media_url):
        """Send image message.

        @See https://developers.facebook.com/docs/messenger-platform/reference/send-api/

        :param str recipient_id: Facebook recipient.id
        :param str media_url: Image URL
        """
        params = {
            "recipient": {"id": recipient_id},
            "message": {
                "attachment": {"type": "image", "payload": {"is_reusable": True, "url": media_url}}
            },
        }
        await self.gateway.send_request(params)


class FacebookChannel:
    """Channel for Facebook Bots.

    Set webhook for Messenger Platform:
    https://developers.facebook.com/docs/messenger-platform/webhooks

    You need to install additional dependencies to use this channel.
    Try `pip install -U maxbot[facebook]`.

    There are two channel arguments (chargs) in this channel.

    dict messaging: incoming data (entry.messaging[0])
    @See https://developers.facebook.com/docs/messenger-platform/reference/webhook-events

    A :class:`Gateway` object represents the Facebook sender and verifier you are working with.
    """

    class ConfigSchema(Schema):
        """Configuration schema for Facebook bot."""

        # Facebook appsecret
        # @See https://developers.facebook.com/docs/facebook-login/security/#appsecret
        app_secret = fields.Str(required=True)
        # Facebook access_token
        # @See https://developers.facebook.com/docs/facebook-login/security/#appsecret
        access_token = fields.Str(required=True)

    @cached_property
    def gateway(self):
        """Return Facebook gateway connected to you bot.

        :return Gateway:
        """
        return Gateway(self.config["app_secret"], self.config["access_token"])

    @cached_property
    def _api(self):
        return _Api(self.gateway)

    async def create_dialog(self, messaging: dict):
        """Create a dialog object from the incomming update.

        :param dict messaging: an incoming update.
        :return dict: a dialog with the schema :class:`~maxbot.schemas.DialogSchema`
        """
        recipient_id = messaging.get("recipient", {}).get("id")
        if recipient_id:
            return {"channel_name": self.name, "user_id": str(recipient_id)}
        return None

    async def send_text(self, command: dict, dialog: dict):
        """Send an text message to the channel.

        @See https://developers.facebook.com/docs/messenger-platform/reference/send-api/

        :param dict command: a command with the payload :attr:`~maxbot.schemas.CommandSchema.text`.
        :param dict dialog: a dialog we respond in, with the schema :class:`~maxbot.schemas.DialogSchema`
        """
        await self._api.send_text(dialog["user_id"], command["text"].render())

    async def send_image(self, command: dict, dialog: dict):
        """Send an image message to the channel.

        @See https://developers.facebook.com/docs/messenger-platform/reference/send-api/

        :param dict command: a command with the payload :attr:`~maxbot.schemas.CommandSchema.image`.
        :param dict dialog: a dialog we respond in, with the schema :class:`~maxbot.schemas.DialogSchema`
        """
        caption = command["image"].get("caption")
        if caption:
            await self._api.send_text(dialog["user_id"], caption.render())
        await self._api.send_image(dialog["user_id"], command["image"]["url"])

    async def receive_text(self, messaging: dict):
        """Receive an text message from the channel.

        @See https://developers.facebook.com/docs/messenger-platform/reference/webhook-events/
        @See https://developers.facebook.com/docs/messenger-platform/reference/webhook-events/messages

        :param dict messaging: an incoming update.
        :return dict: a message with the payload :class:`~maxbot.schemas.MessageSchema.text`
        """
        if messaging.get("message", {}).get("text"):
            return {"text": messaging["message"]["text"]}
        return None

    async def receive_image(self, messaging: dict):
        """Receive an image message from the channel.

        @See https://developers.facebook.com/docs/messenger-platform/reference/webhook-events/
        @See https://developers.facebook.com/docs/messenger-platform/reference/webhook-events/messages#payload

        :param dict messaging: an incoming update.
        :return dict: a message with the payload :class:`~maxbot.schemas.MessageSchema.image`
        """
        if messaging.get("message", {}).get("attachments"):
            images = [
                a["payload"]["url"]
                for a in messaging["message"]["attachments"]
                if a["type"] == "image"
            ]
            if images:
                return {"image": {"url": images[0]}}
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
            # @See https://developers.facebook.com/docs/messenger-platform/webhooks#event-notifications

            http_code = self.gateway.verify_token(request.body, request.headers)
            if http_code != 200:
                return empty(status=http_code)

            # Has many update message (entry)
            for event in request.json["entry"]:
                messaging = event.get("messaging")
                if messaging:
                    # https://developers.facebook.com/docs/messenger-platform/reference/webhook-events/
                    # Array containing one messaging object. Note that even though this is an array,
                    # it will only contain one messaging object.
                    (messaging,) = messaging
                    if not messaging.get("message", {}).get("is_echo"):
                        await callback(messaging)
            return empty()

        if public_url:
            webhook_url = urljoin(public_url, webhook_path)
            logger.warning(
                f"The {self.name} platform has no suitable api, register a webhook yourself {webhook_url}."
            )

        return bp
