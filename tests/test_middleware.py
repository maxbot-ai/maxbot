import pytest

from maxbot.bot import MaxBot
from maxbot.context import StateVariables
from maxbot.errors import BotError


def test_simple_pagination():
    class Middleware:
        def process_message(self, fn):
            async def wrapper(message, dialog, state):
                assert state
                page = state.components.get("page", 0) + 1
                state.components.update(page=page)
                return [
                    dict(page=page),
                ]

            return wrapper

    builder = MaxBot.builder()
    builder.add_middleware(Middleware())
    builder.use_inline_resources("dialog: []")

    bot = builder.build()

    (command,) = bot.process_message("hi")
    assert command == dict(page=1)

    (command,) = bot.process_message("hi")
    assert command == dict(page=2)

    (command,) = bot.process_message("hi")
    assert command == dict(page=3)
