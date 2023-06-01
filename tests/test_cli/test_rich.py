import pytest
from rich.console import Console

from maxbot.cli._rich import PrettyJournal
from maxbot.context import (
    EntitiesResult,
    IntentsResult,
    RecognizedEntity,
    RecognizedIntent,
    RpcContext,
    RpcRequest,
    TurnContext,
)
from maxbot.errors import BotError, YamlSnippet
from maxbot.maxml import fields, markup
from maxbot.schemas import CommandSchema, ResourceSchema


@pytest.fixture
def console_journal():
    return _create_console_journal(verbose=0)


@pytest.fixture
def console_journal_v():
    return _create_console_journal(verbose=1)


@pytest.fixture
def console_journal_vv():
    return _create_console_journal(verbose=2)


@pytest.fixture
def ctx():
    ctx = TurnContext(
        dialog={"channel_name": "test", "user_id": "321"},
        message={"text": "hello world"},
        command_schema=CommandSchema(many=True),
    )
    return ctx


def test_console_basic(ctx, console_journal):
    ctx.commands.append({"text": markup.Value([markup.Item(markup.TEXT, "Good day to you!")])})

    out = console_journal(ctx)

    assert "test#321" in out, out
    assert "hello world" in out, out
    assert "Good day to you!" in out, out


def test_console_commands_yaml(ctx, console_journal):
    ctx.commands.append({"text": markup.Value([markup.Item(markup.TEXT, "Hello, John!")])})
    ctx.commands.append(
        {
            "text": markup.Value(
                [markup.Item(markup.TEXT, "It's lovely to meet you.\nHow can I help you today?")]
            )
        }
    )

    out = console_journal(ctx)

    assert "<text>Hello, John!</text>" in out, out
    assert "  It&#39;s lovely to meet you." in out, out
    assert "  How can I help you today?" in out, out


def test_console_empty_journal_events(ctx, console_journal):
    out = console_journal(ctx)
    assert "journal_events" not in out
    assert "logs" not in out


def test_console_empty_journal_events_v(ctx, console_journal_v):
    out = console_journal_v(ctx)
    assert "journal_events" not in out
    assert "logs" not in out


def test_console_empty_journal_events_vv(ctx, console_journal_vv):
    out = console_journal_vv(ctx)
    assert "journal_events" not in out
    assert "logs" not in out


def test_console_logs(ctx, console_journal):
    ctx.debug(("what is here?", {"xxx": "yyy"}))
    ctx.warning("something wrong")
    ctx.set_error(BotError("some error"))

    out = console_journal(ctx)

    assert "ⓘ  ('what is here?', {'xxx': 'yyy'})" in out
    assert "⚠  something wrong" in out
    assert "✗  some error" in out


def test_console_error_snippet(ctx, console_journal):
    class C(ResourceSchema):
        s = fields.String()

    data = C().loads("s: hello world")
    ctx.set_error(BotError("some error", YamlSnippet.from_data(data)))

    out = console_journal(ctx)

    assert "✗  some error" in out
    assert 'in "<unicode string>", line 1, column 1' in out
    assert "❱ 1 s: hello world" in out


def test_console_rpc(console_journal):
    ctx = TurnContext(
        dialog={"channel_name": "test", "user_id": "321"}, rpc=RpcContext(RpcRequest("say_hello"))
    )

    out = console_journal(ctx)

    assert "test#321" in out
    assert "method: say_hello" in out


def test_console_intents(console_journal_v):
    ctx = TurnContext(
        dialog={"channel_name": "test", "user_id": "321"},
        message={"text": "hello world"},
        intents=IntentsResult.resolve(
            [RecognizedIntent("i1", 0.98), RecognizedIntent("i2", 0.97)]
        ),
    )

    out = console_journal_v(ctx)
    assert "intents" in out
    assert ".top        name       i1" in out
    assert "confidence 0.98" in out
    assert ".ranking[0] name       i1" in out
    assert "confidence 0.98" in out
    assert ".ranking[1] name       i2" in out
    assert "confidence 0.97" in out


def test_console_intents_irrelevant(ctx, console_journal_v):
    out = console_journal_v(ctx)
    assert "intents" in out
    assert ".irrelevant" in out


def test_console_entities(console_journal_v):
    ctx = TurnContext(
        dialog={"channel_name": "test", "user_id": "321"},
        message={"text": "hello world"},
        entities=EntitiesResult.resolve(
            [
                RecognizedEntity("e1", "v1", "xx", 1, 11),
                RecognizedEntity("e2", "v2", "yy", 2, 22),
            ]
        ),
    )

    out = console_journal_v(ctx)
    assert "entities" in out
    assert ".all_objects[0] name       e1" in out
    assert "value      v1" in out
    assert "literal    xx" in out
    assert "start_char 1" in out
    assert "end_char   11" in out
    assert ".all_objects[1] name       e2" in out
    assert "value      v2" in out
    assert "literal    yy" in out
    assert "start_char 2" in out
    assert "end_char   22" in out


def test_console_entities_value_int(console_journal_v):
    ctx = TurnContext(
        dialog={"channel_name": "test", "user_id": "321"},
        message={"text": "hello world"},
        entities=EntitiesResult.resolve(
            [
                RecognizedEntity("e1", 1, "one", 2, 34),
            ]
        ),
    )

    out = console_journal_v(ctx)
    assert "entities" in out
    assert ".all_objects[0] name       e1" in out
    assert "value      1" in out
    assert "literal    one" in out
    assert "start_char 2" in out
    assert "end_char   34" in out


def test_console_entities_empty(ctx, console_journal_v):
    out = console_journal_v(ctx)
    assert "entities" not in out


def test_console_verbose_less_nlu(console_journal):
    ctx = TurnContext(
        dialog={"channel_name": "test", "user_id": "321"},
        message={"text": "hello world"},
        intents=IntentsResult.resolve([RecognizedIntent("i1", 1)]),
        entities=EntitiesResult.resolve([RecognizedEntity("e1", 1, "one", 2, 34)]),
    )

    out = console_journal(ctx)
    assert "intents" not in out
    assert "entities" not in out


def test_console_journal_events(ctx, console_journal_vv):
    ctx.journal_event("event1", {"data": 1})
    ctx.journal_event("event2", {"level1": {"level2": {"level": 3}}})

    out = console_journal_vv(ctx)
    assert "journal_events" in out
    assert "event1 data: 1" in out
    assert "event2 level1:" in out
    assert "level2:" in out
    assert "level: 3" in out


def test_console_verbose_less_journal_events(ctx, console_journal_v):
    ctx.journal_event("event1", {"data": 1})

    out = console_journal_v(ctx)
    assert "journal_events" not in out


class Value:
    pass


def test_console_journal_events_not_serializable(ctx, console_journal_vv):
    value = Value()
    ctx.journal_event("test", value)

    out = console_journal_vv(ctx)
    assert "journal_events" in out, out
    assert f"test {value!r}" in out, out


def _create_console_journal(verbose):
    console = Console(force_terminal=False, soft_wrap=True)
    journal = PrettyJournal(verbose=verbose, console=console)

    def call(ctx):
        with console.capture() as capture:
            journal(ctx)
        return capture.get()

    return call
