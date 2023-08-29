import asyncio

import pytest

from maxbot.user_locks import AsyncioLocks


class Task:
    def __init__(self, locks, dialog):
        self.locks = locks
        self.dialog = dialog
        self.acquired = asyncio.Future()
        self.done = asyncio.Future()
        self.asyncio_task = asyncio.create_task(self.run())

    async def run(self):
        async with self.locks(self.dialog):
            self.acquired.set_result(None)
            await self.done

    @property
    def is_acquired(self):
        return self.acquired.done()

    @property
    def is_locked(self):
        return not self.is_acquired

    async def complete(self):
        self.done.set_result(None)
        await self._idle()

    async def exception(self, exc):
        self.done.set_exception(exc)
        await self._idle()

    async def cancel(self):
        self.asyncio_task.cancel()
        await self._idle()

    async def _idle(self):
        await asyncio.sleep(0)  # give the task a chance to release
        await asyncio.sleep(0)  # give next task a chance to acquire


DIALOG_1 = {"channel_name": "some_channel", "user_id": "123"}
DIALOG_2 = {"channel_name": "some_channel", "user_id": "456"}


@pytest.fixture
def locks():
    return AsyncioLocks()


async def test_single_user_blocks(locks):
    task1 = Task(locks, DIALOG_1)
    task2 = Task(locks, DIALOG_1)
    await asyncio.sleep(0)  # start tasks

    assert task1.is_acquired
    assert task2.is_locked
    await task1.complete()
    assert task2.is_acquired
    await task2.complete()


async def test_different_users_independent(locks):
    task1 = Task(locks, DIALOG_1)
    task2 = Task(locks, DIALOG_2)
    await asyncio.sleep(0)  # start tasks

    assert task1.is_acquired
    assert task2.is_acquired
    await task1.complete()
    await task2.complete()


async def test_exception(locks):
    task1 = Task(locks, DIALOG_1)
    task2 = Task(locks, DIALOG_1)
    await asyncio.sleep(0)  # start tasks

    exc = RuntimeError("XXX")

    assert task1.is_acquired
    assert task2.is_locked
    await task1.exception(exc)
    assert task1.asyncio_task.exception() is exc
    assert task2.is_acquired
    await task2.complete()


async def test_cancelled(locks):
    task1 = Task(locks, DIALOG_1)
    task2 = Task(locks, DIALOG_1)
    await asyncio.sleep(0)  # start tasks

    assert task1.is_acquired
    assert task2.is_locked
    await task1.cancel()
    assert task1.asyncio_task.cancelled()
    assert task2.is_acquired
    await task2.complete()


async def test_locks_fifo(locks):
    tasks = [Task(locks, DIALOG_1) for i in range(10)]
    await asyncio.sleep(0)  # start tasks

    for i, task in enumerate(tasks):
        assert task.is_acquired
        # the rest of tasks a still locked
        for t in tasks[i + 1 :]:
            assert t.is_locked
        await task.complete()
