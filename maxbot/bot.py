"""Create and run conversations applications."""
import asyncio
import logging
import os

from .channels import ChannelsCollection
from .dialog_manager import DialogManager
from .errors import BotError
from .resources import Resources
from .user_locks import AsyncioLocks

logger = logging.getLogger(__name__)


class MaxBot:
    """The central point of the libray."""

    def __init__(
        self,
        dialog_manager=None,
        channels=None,
        user_locks=None,
        state_store=None,
        resources=None,
    ):
        """Create new class instance.

        :param DialogManager dialog_manager: Dialog manager.
        :param ChannelsCollection channels: Channels for communication with users.
        :param StateStore state_store: State store.
        :param Resources resources: Resources for tracking and reloading changes.
        """
        self.dialog_manager = dialog_manager or DialogManager()
        self.channels = channels or ChannelsCollection.empty()
        self._state_store = state_store  # the default value is initialized lazily
        self.user_locks = user_locks or AsyncioLocks()
        self.resources = resources or Resources.empty()

    @classmethod
    def builder(cls, **kwargs):
        """Create a :class:`~BotBuilder` in a convenient way.

        :param dict kwargs: A keyword arguments passed directly to :class:`~BotBuilder` constructor.
        :return BotBuilder: New instance of :class:`~BotBuilder`.
        """
        # avoid circular imports
        from .builder import BotBuilder

        return BotBuilder(**kwargs)

    @classmethod
    def inline(cls, source, **kwargs):
        """Create a bot using YAML-string as a source of resources.

        :param str source: A YAML-string with resources.
        :param dict kwargs: A keyword arguments passed directly to :class:`~BotBuilder` constructor.
        :return MaxBot: New instance of :class:`~MaxBot`.
        """
        builder = cls.builder(**kwargs)
        builder.use_inline_resources(source)
        return builder.build()

    @classmethod
    def from_file(cls, path, **kwargs):
        """Create a bot using a path to a file as a source of resources.

        :param str path: A path to a file with resources.
        :param dict kwargs: A keyword arguments passed directly to :class:`~BotBuilder` constructor.
        :return MaxBot: New instance of :class:`~MaxBot`.
        """
        builder = cls.builder(**kwargs)
        builder.use_file_resources(path)
        return builder.build()

    @classmethod
    def from_directory(cls, bot_dir, **kwargs):
        """Create a bot using a directory of YAML-files as a source of resources.

        :param str bot_dir: A path to a directory with resources.
        :param dict kwargs: A keyword arguments passed directly to :class:`~BotBuilder` constructor.
        :return MaxBot: New instance of :class:`~MaxBot`.
        """
        builder = cls.builder(**kwargs)
        builder.use_directory_resources(bot_dir)
        return builder.build()

    @property
    def rpc(self):
        """Get RPC manager used by the bot.

        :return RpcManager: RPC manager.
        """
        return self.dialog_manager.rpc

    @property
    def state_store(self):
        """State store used to maintain state variables."""
        if self._state_store is None:
            # lazy import to speed up load time
            from .state_store import SQLAlchemyStateStore

            self._state_store = SQLAlchemyStateStore()
        return self._state_store

    def process_message(self, message, dialog=None):
        """Process user message.

        This method is a simple wrapper to avoid the hassle with async/await on a quick start.
        This is very inefficient because new event loop is created and closed on each call.
        Also it won't work if the event loop is already running on the current thread.

        :param dict message: A message received from the user.
        :param dict dialog: Information about the dialog from which the message was received.
        :return List[dict]: A list of commands to respond to the user.
        """
        if dialog is None:
            dialog = self._default_dialog()
        with self.state_store(dialog) as state:
            return asyncio.run(self.dialog_manager.process_message(message, dialog, state))

    def process_rpc(self, request, dialog=None):
        """Process RPC request.

        This method is a simple wrapper to avoid the hassle with async/await on a quick start.
        This is very inefficient because new event loop is created and closed on each call.
        Also it won't work if the event loop is already running on the current thread.

        :param dict request: A request received from the RPC client.
        :param dict dialog: Information about the dialog from which the message was received.
        :return List[dict]: A list of commands to respond to the user.
        """
        if dialog is None:
            dialog = self._default_dialog()
        with self.state_store(dialog) as state:
            return asyncio.run(self.dialog_manager.process_rpc(request, dialog, state))

    def _default_dialog(self):
        return {"channel_name": "builtin", "user_id": "1"}

    async def default_channel_adapter(self, data, channel):
        """Handle user message received from channel.

        :param dict data: Incoming request data.
        :param dict channel: Channel to process request.
        """
        dialog = await channel.create_dialog(data)
        async with self.user_locks(dialog):
            message = await channel.call_receivers(data)
            if message is None:
                return
            with self.state_store(dialog) as state:
                commands = await self.dialog_manager.process_message(message, dialog, state)
                for command in commands:
                    await channel.call_senders(command, dialog)

    async def default_rpc_adapter(self, request, channel, user_id):
        """Handle RPC request for specific channel.

        :param dict request: Incoming request data.
        :param dict channel: Channel to process request.
        :param str user_id: Channel-specific user identifier.
        """
        dialog = {"channel_name": channel.name, "user_id": str(user_id)}
        async with self.user_locks(dialog):
            with self.state_store(dialog) as state:
                commands = await self.dialog_manager.process_rpc(request, dialog, state)
                for command in commands:
                    await channel.call_senders(command, dialog)

    def run_webapp(self, host="localhost", port="8080", *, public_url=None, autoreload=False):
        """Run web application.

        :param str host: Hostname or IP address on which to listen.
        :param int port: TCP port on which to listen.
        :param str public_url: Base url to register webhook.
        :param bool autoreload: Enable tracking and reloading bot resource changes.
        """
        # lazy import to speed up load time
        import sanic

        self._validate_at_least_one_channel()

        app = sanic.Sanic("maxbot", configure_logging=False)
        app.config.FALLBACK_ERROR_FORMAT = "text"

        for channel in self.channels:
            if public_url is None:
                logger.warning(
                    "Make sure you have a public URL that is forwarded to -> "
                    f"http://{host}:{port}/{channel.name} and register webhook for it."
                )

            app.blueprint(
                channel.blueprint(
                    self.default_channel_adapter,
                    public_url=public_url,
                    webhook_path=f"/{channel.name}",
                )
            )

        if self.rpc:
            app.blueprint(self.rpc.blueprint(self.channels, self.default_rpc_adapter))

        if autoreload:

            @app.after_server_start
            async def start_autoreloader(app, loop):
                app.add_task(self.autoreloader, name="autoreloader")

            @app.before_server_stop
            async def stop_autoreloader(app, loop):
                await app.cancel_task("autoreloader")

        @app.after_server_start
        async def report_started(app, loop):
            logger.info(
                f"Started webhooks updater on http://{host}:{port}. Press 'Ctrl-C' to exit."
            )

        if sanic.__version__.startswith("21."):
            app.run(host, port, motd=False, workers=1)
        else:
            os.environ["SANIC_IGNORE_PRODUCTION_WARNING"] = "true"
            app.run(host, port, motd=False, single_process=True)

    def run_polling(self, autoreload=False):
        """Run polling application.

        :param bool autoreload: Enable tracking and reloading bot resource changes.
        """
        # lazy import to speed up load time
        from telegram.ext import ApplicationBuilder, MessageHandler, filters

        self._validate_at_least_one_channel()
        self._validate_polling_support()

        builder = ApplicationBuilder()
        builder.token(self.channels.telegram.config["api_token"])
        background_tasks = []

        @builder.post_init
        async def when_started(app):
            if autoreload:
                background_tasks.append(
                    asyncio.create_task(self.autoreloader(), name="autoreloader")
                )
            logger.info("Started polling updater... Press 'Ctrl-C' to exit.")

        @builder.post_stop
        async def when_stopped(app):
            for task in background_tasks:
                task.cancel()
            if background_tasks:
                # give canceled tasks the last chance to run and ignore errors
                await asyncio.gather(*background_tasks, return_exceptions=True)
            logger.info("Stopped polling updater.")

        async def callback(update, context):
            await self.default_channel_adapter(update, self.channels.telegram)

        async def error_handler(update, context):
            logger.exception("Exception while handling an update")

        app = builder.build()
        app.add_handler(MessageHandler(filters.ALL, callback))
        app.add_error_handler(error_handler)
        app.run_polling()

    async def autoreloader(self):
        """Track and reload bot resource changes."""
        try:
            if not hasattr(self.resources, "poll"):
                logger.warning("Autoreload is not supported and therefore skipped.")
                return

            error_recovery = False
            logger.debug("start autoreloader")
            while True:
                try:
                    changes = self.resources.poll(error_recovery)
                    error_recovery = False
                    if changes:
                        supported = self._exclude_unsupported_changes(changes)
                        if supported:
                            self.dialog_manager.load_resources(self.resources)
                            logger.info("The bot reloaded successfully!")
                except BotError as err:
                    error_recovery = True
                    logger.error("An error occured while reloading the bot: %s", err)

                try:
                    await asyncio.sleep(0.1)
                except asyncio.CancelledError:
                    logger.debug("stop autoreloader")
                    return
        except Exception:
            logger.exception("Unhandled exception in autoreloader")

    def _exclude_unsupported_changes(self, changes):
        unsupported = changes.intersection({"extensions", "channels"})
        if unsupported:
            logger.warning(
                f"The following resources could not be changed after the bot is started: {', '.join(unsupported)}.\n"
                "These changes will be ignored until you restart the bot."
            )
        if "rpc" in changes and not self.rpc:
            unsupported.add("rpc")
            logger.warning(
                "Could not add RPC endpoint while the bot is running. "
                "These changes will be ignored until you restart the bot."
            )
        return changes - unsupported

    def _validate_at_least_one_channel(self):
        if not self.channels:
            raise BotError(
                "At least one channel is required to run a bot. "
                "Please, fill the 'channels' section of your bot.yaml.",
            )

    def _validate_polling_support(self):
        unsupported = self.channels.names - {"telegram"}
        if unsupported:
            raise BotError(
                f"The 'polling' updater does not support following channels: {', '.join(unsupported)}. "
                "Please, remove unsupported channels or use the 'webhooks' updater."
            )
        if self.rpc:
            logger.warning(
                "Your bot requires RPC service. But you force the 'polling' updater which does not support it. "
                "So RPC requests will not be processed. Please use the 'webhooks' updater in order to use RPC."
            )
