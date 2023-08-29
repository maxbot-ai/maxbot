"""VK Bots Channel."""
import logging
import secrets
from functools import cached_property
from urllib.parse import urljoin

import httpx

from .._download import download_to_tempfile
from ..errors import BotError
from ..maxml import PoolLimitSchema, Schema, TimeoutSchema, fields

logger = logging.getLogger(__name__)


def _response_validate(response, keys):
    """Validate VK response."""
    for key in keys:
        # VK Bug: on upload file sometimes receive {'phone': "[]", ...}
        if not response.get(key) or response[key] == "[]":
            raise RuntimeError(f"Wrong key response={response}, key={key}")


class Gateway:
    """Sender VK method."""

    # VK API version with which this gateway is well tested.
    # @See https://dev.vk.com/reference/versions
    API_VERSION = "5.131"

    def __init__(self, access_token, group_id, **kwargs):
        """Create a new class instance.

        :param int access_token: VK access_token
        :param int group_id: VK group_id, may be None
        :param dict kwargs: Arguments for creating HTTPX asynchronous client.
        """
        self.access_token = access_token
        self.group_id = group_id
        self.httpx_client = httpx.AsyncClient(base_url="https://api.vk.com/method", **kwargs)

    async def _send_request(self, method, common_params, payload, error_on_empty_response=True):
        params = {**common_params, **(payload or {})}
        response = await self.httpx_client.post(method, data=params)
        response.raise_for_status()
        result = response.json().get("response")
        if error_on_empty_response and result is None:
            raise RuntimeError(f"empty response: {response.json()!r}")
        return result

    async def send_request(self, method, payload=None):
        """Send VK method with payload.

        :param str method: example 'messages.send'
        :param dict payload: additional payload
        :raise RuntimeError: unexpected response.
        :return dict response: response data
        """
        common_params = {
            "v": self.API_VERSION,
            "access_token": self.access_token,
            # https://dev.vk.com/method/messages.send: random_id < max(int32)
            "random_id": secrets.randbelow(0x7FFFFFFF),
        }
        return await self._send_request(method, common_params, payload)

    async def send_callback_api_request(self, method, payload=None, error_on_empty_response=True):
        """Send VK method with payload for configuration callback API.

        :param str method: example 'messages.send'
        :param dict payload: additional payload
        :param true error_on_empty_response: raise error on empty response
        :raise RuntimeError: unexpected response.
        :raise BotError: `group_id` is not set.
        :return dict response: response data
        """
        if not self.group_id:
            raise BotError("`group_id` is not set")
        common_params = {
            "v": self.API_VERSION,
            "access_token": self.access_token,
            "group_id": self.group_id,
        }
        return await self._send_request(method, common_params, payload, error_on_empty_response)


class _Api:
    """Simple VK api client.

    wrap VK methods:
    * photos.getMessagesUploadServer (get_upload_url)
    * photos.saveMessagesPhoto (save_photo)
    * messages.send (send_image, send_text)
    * upload photo (upload_media_file)
    """

    def __init__(self, gateway, **kwargs):
        """Create a new class instance.

        :param Gateway gateway: send VK command
        :param dict kwargs: Arguments for creating HTTPX asynchronous client.
        """
        self.gateway = gateway
        self.upload_client = httpx.AsyncClient(**kwargs)

    async def send_text(self, user_id, text):
        """Send text message.

        @See  https://dev.vk.com/method/messages.send

        :param int user_id: VK client_id
        :param str text: Text message
        """
        message = {"message": text, "user_id": int(user_id)}
        await self.gateway.send_request("messages.send", message)

    async def send_image(self, user_id, photo, caption):
        """Send message with attachments (photo).

        @See  https://dev.vk.com/method/messages.send

        :param int user_id: VK client_id
        :param str photo: "photo{owner_id}_{id"}" from response 'photos.saveMessagesPhoto'
        :param str caption: Image caption
        """
        message = {"attachment": photo, "user_id": int(user_id)}
        if caption:
            message["message"] = caption
        await self.gateway.send_request("messages.send", message)

    async def get_upload_url(self):
        """Get upload_url for post image.

        @See https://dev.vk.com/method/photos.getMessagesUploadServer

        :return str
        """
        result = await self.gateway.send_request("photos.getMessagesUploadServer")
        _response_validate(result, ["upload_url"])
        return result["upload_url"]

    async def upload_media_file(self, upload_url, filename, file_handle, content_type):
        """Upload media file (get_file) to upload_url.

        :param str filename: temporary file path
        :param str upload_url: Upload url from photos.getMessagesUploadServer
        :param file file_handle: file handle
        :param str content_type: Request content_type
        :return tuple(server: str, photo: str, hash: str): Result tuple
        """
        files = {"photo": (filename, file_handle, content_type)}
        response = await self.upload_client.post(upload_url, files=files)
        response.raise_for_status()
        result = response.json()
        _response_validate(result, ["server", "photo", "hash"])
        return result["server"], result["photo"], result["hash"]

    async def save_photo(self, server, photo, hash_param):
        """Save photo into VK.

        @See  https://dev.vk.com/method/photos.saveMessagesPhoto

        :param str server: Value 'server' from upload post response
        :param str photo: Value 'photo' from upload post response
        :param str hash_param: Value 'hash' from upload post response
        :return str "photo{owner_id}_{id"}": VK photo id for photos.saveMessagesPhoto
        """
        payload = {"server": server, "photo": photo, "hash": hash_param}
        result = await self.gateway.send_request("photos.saveMessagesPhoto", payload)
        _response_validate(result[0], ["owner_id", "id"])
        return f"photo{result[0]['owner_id']}_{result[0]['id']}"

    async def get_callback_confirmation_code(self):
        """Get confirmation code for VK callback API.

        @See https://dev.vk.com/method/groups.getCallbackConfirmationCode

        :return str: confirmation code, will use in answer on VK request with type=confirmation
        """
        result = await self.gateway.send_callback_api_request("groups.getCallbackConfirmationCode")
        _response_validate(result, ["code"])
        return result["code"]

    async def get_callback_servers(self):
        """Get callback API servers.

        @See https://dev.vk.com/method/groups.getCallbackServers

        :return list: list of server id
        """
        result = await self.gateway.send_callback_api_request("groups.getCallbackServers")
        return result.get("items", [])

    async def delete_callback_servers(self, server_id):
        """Delete callback API server.

        @See https://dev.vk.com/method/groups.deleteCallbackServer

        :param int server_id: server id
        """
        payload = {"server_id": server_id}
        result = await self.gateway.send_callback_api_request(
            "groups.deleteCallbackServer", payload, error_on_empty_response=False
        )
        return result

    async def add_callback_server(self, webhook_url, secret_key, title):
        """Add callback API server.

        @See https://dev.vk.com/method/groups.addCallbackServer

        :param str webhook_url: webhook url for incoming updates
        :param str secret_key: webhook secret key
        :param str title: Server title
        :return int: server id
        """
        payload = {"url": webhook_url, "secret_key": secret_key, "title": title}
        result = await self.gateway.send_callback_api_request("groups.addCallbackServer", payload)
        _response_validate(result, ["server_id"])
        return result["server_id"]

    async def set_callback_settings(self, server_id):
        """Set callback API server settings.

        @See https://dev.vk.com/method/groups.setCallbackSettings

        :param int server_id: server id
        :raise RuntimeError: unexpected response.
        """
        payload = {
            "api_version": self.gateway.API_VERSION,
            "server_id": server_id,
            "message_new": 1,
            "message_reply": 1,
            "message_allow": 1,
            "message_deny": 1,
        }
        result = await self.gateway.send_callback_api_request(
            "groups.setCallbackSettings", payload
        )
        if result != 1:
            raise RuntimeError(f"setCallbackSettings result error: {result!r}")


class VkChannel:
    """Channel for VK Bots.

    Set webhook for Callback API:
    @See https://dev.vk.com/api/bots/getting-started.

    You need to install additional dependencies to use this channel.
    Try `pip install -U maxbot[vk]`.
    """

    class ConfigSchema(Schema):
        """Configuration schema for VK bot."""

        # Authentication token to access VK bot api.
        # @See https://dev.vk.com/api/access-token/authcode-flow-user
        access_token = fields.Str(required=True)

        # Group_id for VK page, if present, the incoming messages will be checked against it
        # And use for set webhook
        group_id = fields.Integer()

        # Secret key, use for set webhook
        # @See https://dev.vk.com/method/groups.addCallbackServer
        secret_key = fields.Str()

        # Server title, use for set webhook
        # @See https://dev.vk.com/method/groups.addCallbackServer
        server_title = fields.Str(load_default="MAXBOT")

        # Default HTTP request timeouts
        # @See https://www.python-httpx.org/advanced/#timeout-configuration
        timeout = fields.Nested(TimeoutSchema())

        # Pool limit configuration
        # @See https://www.python-httpx.org/advanced/#pool-limit-configuration
        limits = fields.Nested(PoolLimitSchema())

    @cached_property
    def timeout(self):
        """Create `httpx.Timeout` from channel configuration."""
        return self.config.get("timeout", TimeoutSchema.DEFAULT)

    @cached_property
    def gateway(self):
        """Return VK gateway connected to you bot.

        :return Gateway:
        """
        return Gateway(
            self.config["access_token"],
            self.config.get("group_id"),
            timeout=self.timeout,
            limits=self.config.get("limits", PoolLimitSchema.DEFAULT),
        )

    @cached_property
    def _api(self):
        return _Api(
            self.gateway,
            timeout=self.timeout,
            limits=self.config.get("limits", PoolLimitSchema.DEFAULT),
        )

    async def create_dialog(self, incoming_message: dict):
        """
        Create a dialog object from the incomming update.

        :param dict incoming_message: an incoming update.
        :return dict: a dialog with the schema :class:`~maxbot.schemas.DialogSchema`
        """
        return {"channel_name": "vk", "user_id": str(incoming_message["from_id"])}

    async def send_text(self, command: dict, dialog: dict):
        """
        Send an text command to the channel.

        See https://dev.vk.com/method/messages.send  (message)

        :param dict command: a command with the payload :attr:`~maxbot.schemas.CommandSchema.text`.
        :param dict dialog: a dialog we respond in, with the schema :class:`~maxbot.schemas.DialogSchema`
        """
        await self._api.send_text(dialog["user_id"], command["text"].render())

    async def send_image(self, command: dict, dialog: dict):
        """Send an image command to the channel.

        See https://dev.vk.com/method/messages.send  (attachment.type=photo)

        :param dict command: a command with the payload :attr:`~maxbot.schemas.CommandSchema.text`.
        :param dict dialog: a dialog we respond in, with the schema :class:`~maxbot.schemas.DialogSchema`
        """
        async with download_to_tempfile(command["image"]["url"]) as download_result:
            upload_url = await self._api.get_upload_url()
            server, photo, hash_param = await self._api.upload_media_file(
                upload_url,
                download_result.determine_filename(),
                download_result.temp_file,
                download_result.response.headers["content-type"],
            )
            photo = await self._api.save_photo(server, photo, hash_param)
            caption = command["image"].get("caption")
            await self._api.send_image(
                dialog["user_id"], photo, None if caption is None else caption.render()
            )

    async def receive_text(self, incoming_message: dict):
        """
        Receives an text message from the channel.

        @See https://dev.vk.com/api/community-events/json-schema#Сообщения

        :param UserMessage incoming_message: an incoming update.
        :return dict: a message with the payload :class:`~maxbot.schemas.MessageSchema.text`
        """
        text = incoming_message.get("text")
        if text:
            return {"text": text}
        return None

    async def receive_image(self, incoming_message: dict):
        """
        Receives an image message from the channel.

        @See https://dev.vk.com/api/community-events/json-schema#Фотографии

        :param UserMessage incoming_message: an incoming update.
        :return dict: a message with the payload :class:`~maxbot.schemas.MessageSchema.image`
        """
        attachments = incoming_message.get("attachments", [])
        caption = incoming_message.get("text")
        images = [a for a in attachments if a["type"] == "photo"]
        if images:
            first_image = images[0]["photo"]
            best_size = max(first_image["sizes"], key=lambda i: i["width"] + i["height"])
            payload = {"url": best_size["url"].replace("\\", "")}
            if caption:
                payload["caption"] = caption
            return {"image": payload}
        return None

    async def set_webhook(self, webhook_url):
        """Set webhook url for receive incoming updates.

        See https://dev.vk.com/api/callback/getting-started

        :param str webhook_url: An url to receive incoming updates.
        :raise BotError: `secret_key` is not set.
        :return str: confirmation code, will use in answer on VK request with type=confirmation
        """
        if not self.config.get("secret_key"):
            raise BotError("`secret_key` is not set")
        servers = await self._api.get_callback_servers()
        for server in servers:
            result = await self._api.delete_callback_servers(server["id"])
            if result != 1:
                logger.error("deleteCallbackServer error: %s (%s)", server, result)
        server_id = await self._api.add_callback_server(
            webhook_url, self.config["secret_key"], self.config["server_title"]
        )
        await self._api.set_callback_settings(server_id)
        return await self._api.get_callback_confirmation_code()

    def blueprint(self, callback, execute_once, public_url=None, webhook_path=None):
        """Create web application blueprint to receive incoming updates.

        :param callable callback: a callback for received messages.
        :param callable execute_once: Execute only for first WEB application worker.
        :param string public_url: Base url to register webhook.
        :param string webhook_path: An url path to receive incoming updates.
        :return Blueprint: Blueprint for sanic app.
        """
        from sanic import Blueprint
        from sanic.response import text as text_response

        bp = Blueprint(self.name)

        if webhook_path is None:
            webhook_path = f"/{self.name}"

        bp.ctx.confirmation_code = None

        @bp.post(webhook_path)
        async def endpoint(request):
            logger.debug("%s", request.json)
            data = request.json
            if "group_id" in self.config and data.get("group_id") != self.config["group_id"]:
                return text_response("not my group", status=400)
            if data.get("type") == "message_new":
                await callback(data["object"]["message"], self)
            elif data.get("type") == "confirmation":
                if bp.ctx.confirmation_code:
                    return text_response(bp.ctx.confirmation_code)
                raise RuntimeError("No confirmation_code")
            # @See https://dev.vk.com/api/callback/getting-started
            return text_response("ok")

        if public_url:
            if self.config.get("group_id") and self.config.get("secret_key"):

                @bp.after_server_start
                async def register_webhook(app, loop):
                    async def _impl():
                        webhook_url = urljoin(public_url, webhook_path)
                        bp.ctx.confirmation_code = await self.set_webhook(webhook_url)
                        logger.info(f"Registered webhook {webhook_url}.")

                    await execute_once(app, _impl)

            else:
                logger.warning(
                    "Skip register webhook, set secret_key and group_id for register new webhook"
                )

        return bp
