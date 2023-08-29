import asyncio
import logging
from contextlib import asynccontextmanager, contextmanager
from multiprocessing import current_process, get_context
from os import unlink
from tempfile import NamedTemporaryFile
from time import sleep
from unittest.mock import MagicMock

import pytest

from maxbot.user_locks.mp import (
    _EOF,
    MultiProcessLocks,
    MultiProcessLocksServer,
    ServerClosedConnectionError,
    UnixSocketStreams,
)


@pytest.fixture
def streams():
    with NamedTemporaryFile(prefix="maxbot-pytest-", suffix="-.sock") as f:
        path = f.name
    return UnixSocketStreams(path)


@pytest.fixture
def spawn_ctx():
    return get_context("spawn")


@contextmanager
def server_process(streams, spawn_ctx, args=tuple(), server_stop_=None):
    server_ready, server_stop = spawn_ctx.Event(), server_stop_ or spawn_ctx.Event()
    server_proc = spawn_ctx.Process(
        target=MultiProcessLocksServer(streams.start_server, server_ready, server_stop),
        args=args,
    )
    server_proc.start()
    server_ready.wait()
    try:
        yield
    finally:
        server_stop.set()
        server_proc.join()


@asynccontextmanager
async def mp_locks(open_connection):
    locks = MultiProcessLocks(open_connection)
    yield locks
    await locks.disconnect()


def _common_client(open_connection, dialog, results):
    async def _impl():
        async with mp_locks(open_connection) as locks:
            for _ in range(4):
                async with locks(dialog):
                    results.append(1)
                    results.append(2)

    asyncio.run(_impl())


def test_concurrent_different_processes(streams, spawn_ctx):
    dialog = {"channel_name": "channel_test", "user_id": "user_test"}
    results = spawn_ctx.Manager().list()

    with server_process(streams, spawn_ctx):
        proc_clients = []
        for i in range(2):
            proc_clients.append(
                spawn_ctx.Process(
                    target=_common_client,
                    args=(streams.open_connection, dialog, results),
                    name=f"Client {i}",
                )
            )

        for p in proc_clients:
            p.start()

        for p in proc_clients:
            p.join()

    assert results[:] == [1, 2] * 8


async def test_concurrent_one_process(streams, spawn_ctx):
    with server_process(streams, spawn_ctx):
        async with mp_locks(streams.open_connection) as locks:
            dialog = {"channel_name": "channel_test", "user_id": "user_test"}

            results = []

            async def _request(f1, f2, f3, f4):
                async with locks(dialog):
                    await f1
                    results.append(1)
                    await f2
                    results.append(2)
                async with locks(dialog):
                    await f3
                    results.append(1)
                    await f4
                    results.append(2)

            fs = [asyncio.get_event_loop().create_future() for _ in range(12)]

            async def _wake():
                for f in fs:
                    f.set_result(True)
                    await asyncio.sleep(0.01)

            await asyncio.gather(
                asyncio.create_task(_request(fs[0], fs[3], fs[6], fs[9]), name="r1"),
                asyncio.create_task(_request(fs[1], fs[4], fs[7], fs[10]), name="r2"),
                asyncio.create_task(_request(fs[2], fs[5], fs[8], fs[11]), name="r3"),
                asyncio.create_task(_wake(), name="wake"),
            )
    assert results == [1, 2] * 6


async def test_locked_exception(streams, spawn_ctx):
    dialog = {"channel_name": "channel_test", "user_id": "user_test"}
    with server_process(streams, spawn_ctx):
        async with mp_locks(streams.open_connection) as locks:
            with pytest.raises(RuntimeError):
                async with locks(dialog):
                    raise RuntimeError()

            async with locks(dialog):
                pass


def _locked_exit_client(open_connection, dialog, locked_event):
    async def _impl():
        async with mp_locks(open_connection) as locks:
            async with locks(dialog):
                locked_event.set()
                Event().wait()

    asyncio.run(_impl())


async def test_locked_kill(streams, spawn_ctx):
    with server_process(streams, spawn_ctx):
        async with mp_locks(streams.open_connection) as locks:
            dialog = {"channel_name": "channel_test", "user_id": "user_test"}

            locked_event = spawn_ctx.Event()
            p = spawn_ctx.Process(
                target=_locked_exit_client,
                args=(streams.open_connection, dialog, locked_event),
                name="LockedExit",
            )
            p.start()
            locked_event.wait()
            p.kill()
            p.join()

            async with locks(dialog):
                pass


async def test_recursive_lock(streams, spawn_ctx):
    with server_process(streams, spawn_ctx):
        try:
            async with mp_locks(streams.open_connection) as locks:
                locks._for_current_process = MagicMock()
                dialog = {"channel_name": "channel_test", "user_id": "user_test"}
                try:
                    async with locks(dialog):
                        with pytest.raises(ServerClosedConnectionError) as excinfo:
                            async with locks(dialog):
                                pass
                except ServerClosedConnectionError:
                    pass
        except BrokenPipeError:
            pass


async def test_brokenpipe2serverclosedconnectoin(streams, spawn_ctx):
    with server_process(streams, spawn_ctx):
        try:
            async with mp_locks(streams.open_connection) as locks:
                locks._for_current_process = MagicMock()
                dialog = {"channel_name": "channel_test", "user_id": "user_test"}
                try:
                    async with locks(dialog):
                        with pytest.raises(ServerClosedConnectionError) as excinfo:
                            async with locks(dialog):
                                pass
                except ServerClosedConnectionError:
                    pass
                with pytest.raises(ServerClosedConnectionError) as excinfo:
                    async with locks(dialog):
                        pass
        except BrokenPipeError:
            pass


async def test_is_not_locked(streams, spawn_ctx):
    with server_process(streams, spawn_ctx):
        try:
            async with mp_locks(streams.open_connection) as locks:
                dialog = {"channel_name": "channel_test", "user_id": "user_test"}
                async with locks(dialog):
                    pass

                await locks._release(b"")

                with pytest.raises(ServerClosedConnectionError) as excinfo:
                    async with locks(dialog):
                        pass
        except BrokenPipeError:
            pass


async def test_unexpected_op(streams, spawn_ctx):
    with server_process(streams, spawn_ctx):
        try:
            async with mp_locks(streams.open_connection) as locks:
                dialog = {"channel_name": "channel_test", "user_id": "user_test"}
                async with locks(dialog):
                    pass

                locks._writer.write(b"?" + _EOF)
                await locks._writer.drain()

                with pytest.raises(ServerClosedConnectionError) as excinfo:
                    async with locks(dialog):
                        pass
        except BrokenPipeError:
            pass


async def test_different_user(streams, spawn_ctx):
    with server_process(streams, spawn_ctx):
        async with mp_locks(streams.open_connection) as locks:
            dialog = {"channel_name": "channel_test", "user_id": "user_test"}
            async with locks(dialog):
                async with locks({**dialog, **{"user_id": "2"}}):
                    pass


def patch_ACQ_ACQUIRED():
    import maxbot.user_locks.mp

    maxbot.user_locks.mp._ACQ_ACQUIRED = b"?"


async def test_unexpected_server_answer(streams, spawn_ctx):
    with server_process(
        streams,
        spawn_ctx,
        args=(
            [
                patch_ACQ_ACQUIRED,
            ],
        ),
    ):
        async with mp_locks(streams.open_connection) as locks:
            dialog = {"channel_name": "channel_test", "user_id": "user_test"}
            with pytest.raises(AssertionError) as excinfo:
                async with locks(dialog):
                    pass

            assert "Unexpected server answer: b'?'" == str(excinfo.value)


def send_sigint():
    from signal import SIGINT, raise_signal

    raise_signal(SIGINT)


async def test_sigint(streams, spawn_ctx):
    server_stop_ = spawn_ctx.Event()
    with server_process(
        streams,
        spawn_ctx,
        args=(
            [
                send_sigint,
            ],
        ),
        server_stop_=server_stop_,
    ):
        for _ in range(10):
            if server_stop_.is_set():
                break
            sleep(0.1)
        assert server_stop_.is_set()
