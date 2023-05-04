"""User Locks allow user requests to be processed in FIFO order."""

import asyncio
from contextlib import asynccontextmanager
from weakref import WeakValueDictionary


class AsyncioLocks:
    """Basic implementation of user locks.

    * The implementation in not thread-safe.
    * The FIFO order is guaranteed by underlying asyncio.Lock.

    See https://docs.python.org/3/library/asyncio-sync.html#asyncio.Lock.acquire.
    """

    def __init__(self):
        """Create new class instance."""
        # Use a weak dict to keap no unused locks
        self._locks = WeakValueDictionary()

    @asynccontextmanager
    async def __call__(self, dialog):
        """Acquire and release a lock on the given dialog.

        :param dict dialog: The dialog that needs to be locked.
        """
        key = (dialog["channel_name"], dialog["user_id"])

        user_lock = self._locks.get(key)
        if user_lock is None:
            user_lock = asyncio.Lock()
            self._locks[key] = user_lock

        async with user_lock:
            yield
