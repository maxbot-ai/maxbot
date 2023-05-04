"""Utilities for hooking into a bot."""
import inspect


class HookWrapper:
    """Utility wrapper that passes only those keyword arguments to the wrapped function that it declares.

    It accepts either corotine or regular functions.
    """

    def __init__(self, f):
        """Create new class instance.

        :param callable f: A function to be wrapped.
        """
        self.parameters = inspect.signature(f).parameters
        self.f = f

    async def __call__(self, *args, **kwargs):
        """Pass call into into underlying hook with necessary arguments."""
        kwargs = {k: v for k, v in kwargs.items() if k in self.parameters}
        result = self.f(*args, **kwargs)
        if inspect.iscoroutine(result):
            return await result
        return result
