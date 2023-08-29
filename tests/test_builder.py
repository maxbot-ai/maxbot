import sys
from unittest.mock import AsyncMock, MagicMock, Mock, sentinel

import pytest

from maxbot.bot import MaxBot
from maxbot.builder import BotBuilder
from maxbot.errors import BotError
from maxbot.maxml import Schema, fields


@pytest.fixture
def builder():
    return BotBuilder()


def test_build(builder):
    assert isinstance(builder.build(), MaxBot)


async def test_bot_created(builder):
    builder.build()
    with pytest.raises(RuntimeError):
        builder.build()


def test_message(builder):
    @builder.message("location")
    class LocationMessage(Schema):
        longitude = fields.Float()
        latitude = fields.Float()

    bot = builder.build()

    data = {"location": {"longitude": -73.7085, "latitude": 40.6643}}
    assert bot.dialog_manager.MessageSchema().load(data) == data


def test_command(builder):
    @builder.command("location")
    class LocationCommand(Schema):
        longitude = fields.Float()
        latitude = fields.Float()

    bot = builder.build()

    data = {"location": {"longitude": -73.7085, "latitude": 40.6643}}
    assert bot.dialog_manager.CommandSchema().load(data) == data


def test_channel_mixin(builder):
    @builder.channel_mixin("telegram")
    class MyChannel:
        pass

    builder.use_inline_resources(
        """
        channels:
            telegram:
                api_token: XXX
    """
    )
    bot = builder.build()
    assert isinstance(bot.channels.telegram, MyChannel)


async def test_channel_unknown(builder):
    builder.use_inline_resources(
        """
        channels:
          some_channel: {}
    """
    )
    with pytest.raises(BotError) as excinfo:
        builder.build()
    assert str(excinfo.value) == (
        "caused by marshmallow.exceptions.ValidationError: Unknown field 'some_channel'.\n"
        '  in "<unicode string>", line 3, column 11:\n'
        "    channels:\n"
        "      some_channel: {}\n"
        "      ^^^\n"
    )


def test_persistence_manager(builder):
    builder.persistence_manager = sentinel.persistence_manager
    assert builder.persistence_manager is sentinel.persistence_manager
    bot = builder.build()
    assert bot.persistence_manager is sentinel.persistence_manager


def test_persistence_manager_default(builder):
    assert type(builder.persistence_manager).__name__ == "SQLAlchemyManager"


def test_user_locks(builder):
    builder.user_locks = sentinel.user_locks
    assert builder.user_locks is sentinel.user_locks
    bot = builder.build()
    assert bot.user_locks is sentinel.user_locks


def test_user_locks_default(builder):
    assert type(builder.user_locks).__name__ == "AsyncioLocks"


def test_nlu(builder):
    nlu = Mock()
    builder.nlu = nlu
    assert builder.nlu is nlu
    bot = builder.build()
    assert bot.dialog_manager.nlu is nlu
    nlu.load_resources.assert_called_once()


def test_nlu_default(builder):
    assert type(builder.nlu).__name__ == "Nlu"


def test_jinja_options(builder):
    builder.jinja_options["optimized"] = False
    assert builder.jinja_env.optimized == False


def test_template_filter(builder):
    @builder.template_filter()
    def reverse(s):
        return s[::-1]

    builder.use_inline_resources(
        """
        dialog:
          - condition: message.text
            response: "{{ message.text|reverse }}"
    """
    )
    bot = builder.build()
    commands = bot.process_message("hey bot")
    assert commands == [{"text": "tob yeh"}]


def test_template_test(builder):
    @builder.template_test()
    def greeting(s):
        return any(h in s for h in ["hello", "hey"])

    builder.use_inline_resources(
        """
        dialog:
          - condition: message.text is greeting
            response: hello world
    """
    )
    bot = builder.build()
    commands = bot.process_message("hey bot")
    assert commands == [{"text": "hello world"}]


def test_template_global(builder):
    @builder.template_global()
    def say_hello(name):
        return f"Hello, {name}!"

    builder.use_inline_resources(
        """
        dialog:
          - condition: message.text
            response: "{{ say_hello('Bob') }}"
    """
    )
    bot = builder.build()
    commands = bot.process_message("hey bot")
    assert commands == [{"text": "Hello, Bob!"}]


def test_before_turn(builder):
    hook = MagicMock(return_value=AsyncMock())
    builder.before_turn(hook)

    bot = builder.build()
    bot.process_message("hey bot")
    assert hook.called


def test_after_turn(builder):
    hook = MagicMock(return_value=AsyncMock())
    builder.after_turn(hook)

    bot = builder.build()
    bot.process_message("hey bot")
    assert hook.called


def test_middleware(builder):
    middleware = Mock(
        process_message=Mock(return_value=sentinel.process_message),
        process_rpc=Mock(return_value=sentinel.process_rpc),
    )
    builder.add_middleware(middleware)

    bot = builder.build()
    assert bot.dialog_manager.process_message is sentinel.process_message
    assert bot.dialog_manager.process_rpc is sentinel.process_rpc


def test_middleware_order(builder):
    calls = []

    class Middleware:
        def __init__(self, ident):
            self.ident = ident

        def process_message(self, fn):
            async def wrapper(message, dialog, state):
                calls.append(self.ident)
                return await fn(message, dialog, state)

            return wrapper

    builder.add_middleware(Middleware(1))
    builder.add_middleware(Middleware(2))
    builder.build().process_message("hey bot")
    assert calls == [2, 1]


def test_use_inline_resources(builder):
    builder.use_inline_resources(
        """
        dialog:
          - condition: message.text == "hey bot"
            response: hello world
    """
    )
    bot = builder.build()
    commands = bot.process_message("hey bot")
    assert commands == [{"text": "hello world"}]


def test_use_file_resources(builder, tmp_path):
    botfile = tmp_path / "bot.yaml"
    botfile.write_text(
        """
        dialog:
          - condition: message.text == "hey bot"
            response: hello world
    """
    )

    builder.use_file_resources(botfile)
    bot = builder.build()
    commands = bot.process_message("hey bot")
    assert commands == [{"text": "hello world"}]


def test_use_directory_resources(builder, tmp_path):
    botfile = tmp_path / "bot.yaml"
    botfile.write_text(
        """
        dialog:
          - condition: message.text == "hey bot"
            response: hello world
    """
    )

    builder.use_directory_resources(tmp_path)
    bot = builder.build()
    commands = bot.process_message("hey bot")
    assert commands == [{"text": "hello world"}]


def test_use_package_resources(builder, tmp_path, monkeypatch):
    package_dir = tmp_path / "xxx"
    package_dir.mkdir()
    botfile = package_dir / "bot.yaml"
    botfile.write_text(
        """
        dialog:
          - condition: message.text == "hey bot"
            response: hello world
    """
    )
    monkeypatch.syspath_prepend(str(package_dir.parent))
    (package_dir / "__init__.py").touch()

    builder.use_package_resources("xxx")
    bot = builder.build()
    commands = bot.process_message("hey bot")
    assert commands == [{"text": "hello world"}]


def test_history_tracked(builder):
    builder.track_history()
    assert builder.build()._history_tracked == True


def test_history_tracked_default(builder):
    assert builder.build()._history_tracked == False
