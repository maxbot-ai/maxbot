"""Create and run conversations applications."""
import asyncio
import logging

from .channels import ChannelsCollection
from .dialog_manager import DialogManager
from .errors import BotError
from .resources import Resources
from .user_locks import AsyncioLocks, UnixSocketStreams

logger = logging.getLogger(__name__)


class MaxBot:
    """The central point of the libray."""

    def __init__(
        self,
        dialog_manager=None,
        channels=None,
        user_locks=None,
        persistence_manager=None,
        resources=None,
        history_tracked=False,
    ):
        """Create new class instance.

        :param DialogManager dialog_manager: Dialog manager.
        :param ChannelsCollection channels: Channels for communication with users.
        :param PersistenceManager persistence_manager: Persistence manager.
        :param Resources resources: Resources for tracking and reloading changes.
        """
        self.dialog_manager = dialog_manager or DialogManager()
        self.channels = channels or ChannelsCollection.empty()
        self._persistence_manager = persistence_manager  # the default value is initialized lazily
        self._history_tracked = history_tracked
        self._user_locks = user_locks
        self.resources = resources or Resources.empty()

    SocketStreams = UnixSocketStreams
    SUFFIX_LOCKS = "-locks.sock"
    SUFFIX_DB = ".db"

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
    def user_locks(self):
        """Get user locks implementation."""
        if self._user_locks is None:
            self._user_locks = AsyncioLocks()
        return self._user_locks

    def setdefault_user_locks(self, value):
        """Set .user_locks field value if it is not set.

        :param AsyncioLocks value: User locks object.
        :return AsyncioLocks: .user_locks field value
        """
        if self._user_locks is None:
            self._user_locks = value
        return self._user_locks

    @property
    def rpc(self):
        """Get RPC manager used by the bot.

        :return RpcManager: RPC manager.
        """
        return self.dialog_manager.rpc

    @property
    def persistence_manager(self):
        """Return persistence manager."""
        if self._persistence_manager is None:
            # lazy import to speed up load time
            from .persistence_manager import SQLAlchemyManager

            self._persistence_manager = SQLAlchemyManager()
        return self._persistence_manager

    def setdefault_persistence_manager(self, factory):
        """Set .persistence_manager field value if it is not set.

        :param callable factory: Persistence manager factory.
        :return SQLAlchemyStateStore: .persistence_manager field value.
        """
        if self._persistence_manager is None:
            self._persistence_manager = factory()
        return self._persistence_manager

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
        with self.persistence_manager(dialog) as tracker:
            return asyncio.run(
                self.dialog_manager.process_message(message, dialog, tracker.get_state())
            )

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
        with self.persistence_manager(dialog) as tracker:
            return asyncio.run(
                self.dialog_manager.process_rpc(request, dialog, tracker.get_state())
            )

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
            with self.persistence_manager(dialog) as tracker:
                commands = await self.dialog_manager.process_message(
                    message, dialog, tracker.get_state()
                )
                for command in commands:
                    await channel.call_senders(command, dialog)
                if self._history_tracked:
                    tracker.set_message_history(message, commands)

    async def default_rpc_adapter(self, request, channel, user_id):
        """Handle RPC request for specific channel.

        :param dict request: Incoming request data.
        :param dict channel: Channel to process request.
        :param str user_id: Channel-specific user identifier.
        """
        dialog = {"channel_name": channel.name, "user_id": str(user_id)}
        async with self.user_locks(dialog):
            with self.persistence_manager(dialog) as tracker:
                commands = await self.dialog_manager.process_rpc(
                    request, dialog, tracker.get_state()
                )
                for command in commands:
                    await channel.call_senders(command, dialog)
                if self._history_tracked:
                    tracker.set_rpc_history(request, commands)

    def run_polling(self, autoreload=False):
        """Run polling application.

        :param bool autoreload: Enable tracking and reloading bot resource changes.
        """
        # lazy import to speed up load time
        from telegram.ext import ApplicationBuilder, CallbackQueryHandler, MessageHandler, filters

        self.validate_at_least_one_channel()
        self._validate_polling_support()

        builder = ApplicationBuilder()
        builder.token(self.channels.telegram.config["api_token"])

        builder.request(self.channels.telegram.create_request())
        builder.get_updates_request(self.channels.telegram.create_request())

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
        app.add_handler(CallbackQueryHandler(callback=callback, pattern=None))
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

    def validate_at_least_one_channel(self):
        """Raise BotError if at least one channel is missing."""
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
