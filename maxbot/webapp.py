"""Sanic WEB application."""

import logging
import os
from multiprocessing import get_context
from tempfile import NamedTemporaryFile

from .user_locks import MultiProcessLocks, MultiProcessLocksServer

logger = logging.getLogger(__name__)


def run_webapp(
    bot,
    bot_factory,
    host,
    port,
    *,
    init_logging=None,
    public_url=None,
    autoreload=False,
    workers=1,
    fast=False,
    single_process=False,
):
    """Run WEB application.

    Function does not return control.

    :param MaxBot bot: Bot.
    :param calable bot_factory: MaxBot factory.
    :param str host: Hostname or IP address on which to listen.
    :param int port: TCP port on which to listen.
    :param calable init_logging: Initialize logging for new processes.
    :param str public_url: Base url to register webhook.
    :param bool autoreload: Enable tracking and reloading bot resource changes.
    :param int workers: Number of worker processes to spawn.
    :param bool fast: Whether to maximize worker processes.
    :param bool single_process: Single process mode.
    """
    factory = Factory(
        bot, bot_factory, host, port, init_logging, public_url, autoreload, single_process
    )

    # lazy import to speed up load time
    import sanic

    if sanic.__version__.startswith("21."):
        factory.single_process = True
        factory().run(host, port, motd=False, workers=1)
        return

    os.environ["SANIC_IGNORE_PRODUCTION_WARNING"] = "true"
    if single_process:
        factory().run(host, port, motd=False, single_process=True)
        return

    from sanic.worker.loader import AppLoader

    loader = AppLoader(factory=factory)
    app = loader.load()
    app.prepare(
        host,
        port,
        motd=False,
        fast=fast,
        workers=workers,
        single_process=single_process,
    )
    sanic.Sanic.serve(primary=app, app_loader=loader)


class Factory:
    """WEB application factory.

    Re-create MaxBot object in another process and create WEB application.
    """

    def __init__(
        self, bot, bot_factory, host, port, init_logging, public_url, autoreload, single_process
    ):
        """Create new class instance.

        :param MaxBot bot: Bot.
        :param calable bot_factory: MaxBot factory.
        :param str host: Hostname or IP address on which to listen.
        :param int|str port: TCP port on which to listen.
        :param calable init_logging: Initialize logging for new processes.
        :param str public_url: Base url to register webhook.
        :param bool autoreload: Enable tracking and reloading bot resource changes.
        :param bool single_process: Single process mode.
        """
        self.bot = bot
        self.bot_factory = bot_factory
        self.host = host
        self.port = port
        self.init_logging = init_logging
        self.public_url = public_url
        self.autoreload = autoreload
        self.single_process = single_process
        with NamedTemporaryFile(prefix="maxbot-") as f:
            self.base_file_name = f.name

    def __getstate__(self):
        """Transfer state to another process."""
        state = self.__dict__.copy()
        state.update(bot=None)
        return state

    def __setstate__(self, state):
        """Apply transfered state from another process."""
        self.__dict__.update(state)
        if self.init_logging:
            self.init_logging()  # for new process
        self.bot = self.bot_factory()

    def __call__(self):
        """Create and return WEB application."""
        # lazy import to speed up load time
        import sanic

        self.bot.validate_at_least_one_channel()

        app = sanic.Sanic("maxbot", configure_logging=False)
        app.config.FALLBACK_ERROR_FORMAT = "text"

        for channel in self.bot.channels:
            app.blueprint(
                channel.blueprint(
                    self.bot.default_channel_adapter,
                    self.execute_once,
                    public_url=self.public_url,
                    webhook_path=f"/{channel.name}",
                )
            )

        if self.bot.rpc:
            app.blueprint(self.bot.rpc.blueprint(self.bot.channels, self.bot.default_rpc_adapter))

        if self.autoreload:

            @app.after_server_start
            async def start_autoreloader(app, loop):
                app.add_task(self.bot.autoreloader, name="autoreloader")

            @app.before_server_stop
            async def stop_autoreloader(app, loop):
                await app.cancel_task("autoreloader")

        if not self.single_process:
            mp_ctx = {
                "locks_file_path": f"{self.base_file_name}{self.bot.SUFFIX_LOCKS}",
                "db_file_path": f"{self.base_file_name}{self.bot.SUFFIX_DB}",
            }
            mp_ctx["locks_streams"] = self.bot.SocketStreams(mp_ctx["locks_file_path"])
            mp_ctx["default_locks"] = MultiProcessLocks(mp_ctx["locks_streams"].open_connection)

            @app.main_process_start
            async def main_process_started(app, loop):
                logger.info("Sanic multi-process server starting...")
                user_locks = self.bot.setdefault_user_locks(mp_ctx["default_locks"])
                if isinstance(user_locks, MultiProcessLocks):
                    ctx = get_context("spawn")
                    mp_ctx["locks_server_ready"] = ctx.Event()
                    mp_ctx["locks_server_stop"] = ctx.Event()
                    mp_ctx["locks_server"] = ctx.Process(
                        target=MultiProcessLocksServer(
                            mp_ctx["locks_streams"].start_server,
                            mp_ctx["locks_server_ready"],
                            mp_ctx["locks_server_stop"],
                        ),
                        args=(
                            [
                                self.init_logging,
                            ],
                        ),
                        name="MpUserLocks",
                    )
                    mp_ctx["locks_server"].start()

                def _create_default_mp_persistence_manager_and_tables():
                    persistence_manager = self._create_default_mp_persistence_manager(
                        mp_ctx["db_file_path"]
                    )
                    persistence_manager.create_tables()
                    return persistence_manager

                self.bot.setdefault_persistence_manager(
                    _create_default_mp_persistence_manager_and_tables
                )

            @app.main_process_ready
            async def main_process_ready(app, loop):
                if "locks_server" in mp_ctx:
                    mp_ctx["locks_server_ready"].wait()

            @app.main_process_stop
            async def main_process_stopping(app, loop):
                logger.info("Sanic multi-process server stopping...")
                if "locks_server" in mp_ctx:
                    mp_ctx["locks_server_stop"].set()

        @app.after_server_start
        async def server_started(app, loop):
            if not self.single_process:
                self.bot.setdefault_user_locks(mp_ctx["default_locks"])
                self.bot.setdefault_persistence_manager(
                    lambda: self._create_default_mp_persistence_manager(mp_ctx["db_file_path"])
                )

            async def _log_messages_for_user():
                logger.debug("bot.user_locks = %s", self.bot.user_locks)
                logger.debug(
                    "bot.persistence_manager.engine = %s", self.bot.persistence_manager.engine
                )

                if self.public_url is None:
                    for channel in self.bot.channels:
                        logger.warning(
                            "Make sure you have a public URL that is forwarded to -> "
                            f"http://{self.host}:{self.port}/{channel.name} and register webhook for it."
                        )
                logger.info(
                    f"Started webhooks updater on http://{self.host}:{self.port}. Press 'Ctrl-C' to exit."
                )

            await self.execute_once(app, _log_messages_for_user)

        return app

    @staticmethod
    def _create_default_mp_persistence_manager(file_path):
        from .persistence_manager import SQLAlchemyManager, create_engine, create_json_serializer

        persistence_manager = SQLAlchemyManager()
        persistence_manager.engine = create_engine(
            f"sqlite:///{file_path}", json_serializer=create_json_serializer()
        )
        return persistence_manager

    async def execute_once(self, app, fn):
        """Execute only for first worker of WEB application."""
        if self.single_process or (app.m.name.endswith("-0-0") and app.m.state["starts"] == 1):
            # Run in first worker
            await fn()
