"""Multiprocess implementation of user lock."""
import asyncio
import logging
import os
from base64 import b64encode
from contextlib import asynccontextmanager
from multiprocessing import current_process
from signal import SIGINT, signal

from .asyncio import AsyncioLocks

logger = logging.getLogger(__name__)

_OP_ACQUIRE = b"a"
_ACQ_ACQUIRED = b"\x01"
_OP_RELEASE = b"r"
_EOF = b"\0"


class ServerClosedConnectionError(RuntimeError):
    """Exception from `MultiProcessLocks.__call__`: server closed the connection."""


class UnixSocketStreams:
    """Asyncronus streams implemented on UNIX sockets."""

    def __init__(self, path):
        """Create new class instance.

        :param str|bytes|os.PathLike path: UNIX socket path.
        """
        self.path = path

    @asynccontextmanager
    async def start_server(self, client_connected_cb):
        """Start new server."""
        try:
            yield await asyncio.start_unix_server(client_connected_cb, path=self.path)
        finally:
            os.unlink(self.path)

    async def open_connection(self):
        """Open client connection."""
        return await asyncio.open_unix_connection(path=self.path)


class MultiProcessLocks:
    """Multiprocess implementation of user lock."""

    def __init__(self, open_connection):
        """Create new class instance.

        * The implementation in not thread-safe.
        * The FIFO order is guaranteed by underlying asyncio.Lock.

        Usage example:

            from multiprocessing import Process, Event

            # socket streams implementation (IPC transport)
            streams = UnixSocketStreams("/tmp/maxbot-locks.sock")
            # server ready and server stop events
            ready_event, stop_event = Event(), Event()
            # server in dedicated process
            Process(
                target=MultiProcessLocksServer(streams.start_server, ready_event, stop_event),
                daemon=True
            ).start()
            # waiting for server to be ready to accept connections
            ready_event.wait()

            # asynchronous user locks
            locks = MultiProcessLocks(streams.open_connection)

            # lock-unlock user1 (from dialog1)
            async with locks(dialog1):
                pass

            # lock-unlock user2 (from dialog2)
            async with locks(dialog2):
                pass

        :param callable open_connection: Open connection to server.
        """
        self._open_connection = open_connection
        self._streams_lock = asyncio.Lock()
        self._reader, self._writer = None, None
        self._for_current_process = AsyncioLocks()

    @asynccontextmanager
    async def __call__(self, dialog):
        """Acquire and release a lock on the given dialog.

        :param dict dialog: The dialog that needs to be locked.
        """
        async with self._for_current_process(dialog):
            key = (
                b64encode(str(dialog["channel_name"]).encode())
                + b"|"
                + b64encode(str(dialog["user_id"]).encode())
            )
            try:
                await self._connect()
                await self._acquire(key)
                try:
                    yield
                finally:
                    await self._release(key)
            except (ConnectionResetError, BrokenPipeError) as exc:
                raise ServerClosedConnectionError() from exc  # pragma: not covered

    async def _connect(self):
        async with self._streams_lock:
            if not self._reader:
                assert not self._writer
                self._reader, self._writer = await self._open_connection()
                self._writer.write(current_process().name.encode() + _EOF)
                await self._writer.drain()

    async def _acquire(self, key):
        async with self._streams_lock:
            self._writer.write(_OP_ACQUIRE + key + _EOF)
            await self._writer.drain()

            acq = await self._reader.read(len(_ACQ_ACQUIRED))
            if acq != _ACQ_ACQUIRED:
                if acq:
                    raise AssertionError(f"Unexpected server answer: {acq}")
                raise ServerClosedConnectionError()

    async def _release(self, key):
        async with self._streams_lock:
            self._writer.write(_OP_RELEASE + key + _EOF)
            await self._writer.drain()

    async def disconnect(self):
        """Disconnect from server process."""
        if self._writer:
            self._writer.close()
            await self._writer.wait_closed()

            self._reader, self._writer = None, None


class MultiProcessLocksServer:
    """Dedicated process of multiprocess user locks."""

    def __init__(self, start_server, ready_event, stop_event):
        """Create new class instance.

        :param callable start_server: Start new server.
        :param Event ready_event: An event that is set when server is accepting new connections.
        :param Event stop_event: Stop server event.
        """
        self._start_server = start_server
        self._ready_event = ready_event
        self._stop_event = stop_event
        self._connected_clients = 0
        self._locks = {}

    async def _log_exception(self, coro, name):
        try:
            await coro
        except Exception:
            logger.exception(f"Unhandled exception in {name}")

    def _create_task(self, coro, name):
        return asyncio.create_task(self._log_exception(coro, name), name=name)

    @staticmethod
    async def _fatal_error(writer, message):
        writer.close()
        await writer.wait_closed()
        raise AssertionError(message)

    async def _client_conected(self, reader, writer):
        await self._log_exception(self._client_conected_impl(reader, writer), "client_connected")

    async def _client_conected_impl(self, reader, writer):
        self._connected_clients += 1
        try:
            client_name = await reader.readuntil(_EOF)
            client_name = client_name[:-1].decode()
            logger.info("%s connected", client_name)

            locked_by_client = {}
            try:
                while True:
                    try:
                        buffer = await reader.readuntil(_EOF)
                    except asyncio.IncompleteReadError as error:
                        assert not error.partial
                        return

                    op = buffer[0:1]
                    key = buffer[1:-1]
                    if op == _OP_ACQUIRE:
                        logger.debug("%s acquire %s", client_name, key)
                        if key in locked_by_client:
                            await self._fatal_error(
                                writer, f"Recursive lock {key!r}: {locked_by_client[key]}"
                            )

                        user_lock = self._locks.get(key)
                        if user_lock is None:
                            user_lock = asyncio.Lock()
                            self._locks[key] = user_lock

                        await user_lock.acquire()
                        locked_by_client[key] = user_lock

                        writer.write(_ACQ_ACQUIRED)
                        await writer.drain()
                    elif op == _OP_RELEASE:
                        logger.debug("%s release %s", client_name, key)
                        user_lock = locked_by_client.pop(key, None)
                        if not user_lock:
                            await self._fatal_error(writer, f"{key} is not locked")

                        user_lock.release()
                    else:
                        await self._fatal_error(writer, f"Unexpected: {buffer}")  # no cov
            finally:
                for key, user_lock in locked_by_client.items():
                    logger.warning(
                        "%s %s unlocked on client %s disconnect", key, user_lock, client_name
                    )
                    user_lock.release()

                logger.info("%s disconnected", client_name)
        finally:
            assert self._connected_clients > 0
            self._connected_clients -= 1

    async def _serve(self, server):
        async with server:
            logger.info("Locks server started")
            while True:
                if server.is_serving():
                    self._ready_event.set()

                if self._stop_event.is_set() and self._connected_clients == 0:
                    logger.info("Locks server stopping...")
                    return

                await asyncio.sleep(0.1)
                continue

    def _sigint_handler(self, signum, frame):
        logger.warning(
            "Locks server has received an %s signal. Waiting for %s clients to disconnect.",
            signum,
            self._connected_clients,
        )
        self._stop_event.set()

    def __call__(self, initialize_process_fns=None):
        """Server process entry point.

        :param iterable[calable] initialize_process_fns: Additional in-process initialization.
        """
        signal(SIGINT, self._sigint_handler)

        for fn in initialize_process_fns or []:
            fn()
        logger.info("Locks server staring...")

        async def main():
            async with self._start_server(self._client_conected) as server:
                await asyncio.gather(
                    self._create_task(self._serve(server), name="serve"),
                    self._create_task(server.serve_forever(), name="serve_forever"),
                    return_exceptions=True,
                )

        asyncio.run(main())
        logger.info("Locks server stopped")
