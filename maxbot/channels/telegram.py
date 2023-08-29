"""Telegram Bots Channel."""
import logging
import os
from functools import cached_property
from urllib.parse import urljoin

import httpx
from telegram import Bot, Update
from telegram.request import HTTPXRequest

from ..maxml import PoolLimitSchema, Schema, TimeoutSchema, fields

TG_FILE_URL = "https://api.telegram.org/file"

logger = logging.getLogger(__name__)


class TelegramChannel:
    """A channel for Telegram Bots. See https://core.telegram.org/bots.

    The implementation is based on python-telegram-bot library.
    See https://python-telegram-bot.org.

    You need to install additional dependencies to use this channel.
    Try `pip install -U maxbot[telegram]`.
    """

    class ConfigSchema(Schema):
        """Configuration schema for telegram bot."""

        # Authentication token to access telegram bot api.
        # @see https://core.telegram.org/bots#6-botfather.
        api_token = fields.Str(required=True)

        # Default HTTP request timeouts
        # @see https://www.python-httpx.org/advanced/#timeout-configuration
        timeout = fields.Nested(TimeoutSchema())

        # Pool limit configuration
        # @see https://www.python-httpx.org/advanced/#pool-limit-configuration
        limits = fields.Nested(PoolLimitSchema())

    class Request(HTTPXRequest):
        """Local implementation of telegram.request.HTTPXRequest."""

        def __init__(self, timeout, limits):  # pylint: disable=super-init-not-called
            """Create new instance.

            :param httpx.Timeout timeout: HTTPX client timeout.
            :param httpx.Limits limits: HTTPX client limits.
            """
            self._http_version = "1.1"
            self._client_kwargs = {
                "timeout": timeout,
                "proxies": None,
                "limits": limits,
                "http1": True,
                "http2": False,
            }
            self._client = self._build_client()

    def create_request(self):
        """Create new instance of `telegram.request.BaseRequest` implementation."""
        return self.Request(self.timeout, self.limits)

    @cached_property
    def timeout(self):
        """Create `httpx.Timeout` from channel configuration."""
        return self.config.get("timeout", TimeoutSchema.DEFAULT)

    @cached_property
    def limits(self):
        """Create `httpx.Limits` from channel configuration."""
        return self.config.get("limits", PoolLimitSchema.DEFAULT)

    @cached_property
    def httpx_client(self):
        """Create HTTPX asynchronous client."""
        return httpx.AsyncClient(timeout=self.timeout, limits=self.limits)

    @cached_property
    def bot(self):
        """Return telegram bot connected to you bot.

        See https://core.telegram.org/bots/api#available-methods for more information about telegram bot methods.

        :return Bot:
        """
        return Bot(
            self.config["api_token"],
            get_updates_request=self.create_request(),
            request=self.create_request(),
        )

    async def create_dialog(self, update: Update):
        """Create a dialog object from the incomming update.

        See https://core.telegram.org/bots/api#update.
        See https://docs.python-telegram-bot.org/en/latest/telegram.update.html.

        :param Update update: An incoming update.
        :return dict: A dialog information that matches the :class:`~maxbot.schemas.DialogSchema`.
        """
        return {"channel_name": "telegram", "user_id": str(update.effective_user.id)}

    async def receive_text(self, update: Update):
        """Receive a text message from the channel.

        See https://core.telegram.org/bots/api#message.

        :param Update update: An incoming update.
        :return dict: A message with the payload :class:`~maxbot.schemas.MessageSchema.text`.
        """
        if update.message and update.message.text:
            return {"text": update.message.text}
        return None

    async def send_text(self, command: dict, dialog: dict):
        """Send a text command to the channel.

        See https://core.telegram.org/bots/api#sendmessage.

        :param dict command: A command with the payload :attr:`~maxbot.schemas.CommandSchema.text`.
        :param dict dialog: A dialog we respond in, with the schema :class:`~maxbot.schemas.DialogSchema`.
        """
        await self.bot.send_message(dialog["user_id"], command["text"].render())

    async def receive_image(self, update: Update):
        """Receive an image message from the channel.

        See https://core.telegram.org/bots/api#message.
        See https://core.telegram.org/bots/api#photosize.
        See https://core.telegram.org/bots/api#getfile.
        See https://core.telegram.org/bots/api#file.

        :param Update update: An incoming update.
        :return dict: A message with the payload :class:`~maxbot.schemas.MessageSchema.image`.
        """
        if update.message and update.message.photo:
            # get the biggest image version
            photo = max(update.message.photo, key=lambda p: p.file_size)
            obj = await self.bot.getFile(photo.file_id)
            message = {"image": {"url": obj.file_path, "size": obj.file_size}}
            if update.message.caption:
                message["image"]["caption"] = update.message.caption
            return message
        return None

    async def send_image(self, command: dict, dialog: dict):
        """Send an image command to the channel.

        See https://core.telegram.org/bots/api#sendphoto.

        :param dict command: A command with the payload :attr:`~maxbot.schemas.CommandSchema.image`.
        :param dict dialog: A dialog we respond in, with the schema :class:`~maxbot.schemas.DialogSchema`.
        """
        image = command["image"]
        caption = image.get("caption")
        # Error on send_photo with url starts with {TG_FILE_URL}:
        # telegram.error.BadRequest: Wrong file identifier/http url specified
        # In this case send content photo
        if image["url"].startswith(TG_FILE_URL):
            response = await self.httpx_client.get(image["url"])
            response.raise_for_status()
            await self.bot.send_photo(
                dialog["user_id"],
                response.content,
                None if caption is None else caption.render(),
                filename=os.path.basename(response.url.path),
            )
        else:
            await self.bot.send_photo(
                dialog["user_id"], image["url"], None if caption is None else caption.render()
            )

    def blueprint(self, callback, execute_once, public_url=None, webhook_path=None):
        """Create web application blueprint to receive incoming updates.

        :param callable callback: a callback for received messages.
        :param callable execute_once: Execute only for first WEB application worker.
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
            logger.debug("%s", request.json)
            update = Update.de_json(data=request.json, bot=self.bot)
            await callback(update, self)
            return empty()

        if public_url:

            @bp.after_server_start
            async def register_webhook(app, loop):
                async def _impl():
                    webhook_url = urljoin(public_url, webhook_path)
                    await self.bot.setWebhook(webhook_url)
                    logger.info(f"Registered webhook {webhook_url}.")

                await execute_once(app, _impl)

        return bp
