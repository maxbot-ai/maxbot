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
from maxbot.flows.slot_filling import SlotFilling, SlotSchema
from maxbot.maxml import fields, markup
from maxbot.schemas import CommandSchema, ResourceSchema


@pytest.fixture
def console_journal_q():
    return _create_console_journal(verbosity=-1)


@pytest.fixture
def console_journal():
    return _create_console_journal(verbosity=0)


@pytest.fixture
def console_journal_v():
    return _create_console_journal(verbosity=1)


@pytest.fixture
def console_journal_vv():
    return _create_console_journal(verbosity=2)


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


def test_console_commands_xml(ctx, console_journal):
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
    _test_console_empty_journal(ctx, console_journal)


def test_console_empty_journal_events_v(ctx, console_journal_v):
    _test_console_empty_journal(ctx, console_journal_v)


def test_console_empty_journal_events_vv(ctx, console_journal_vv):
    _test_console_empty_journal(ctx, console_journal_vv)


def _test_console_empty_journal(ctx, console_journal_):
    out = console_journal_(ctx)
    assert "journal_events" not in out
    assert "logs" not in out
    assert "user" not in out
    assert "slots" not in out


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


def test_console_journal_events_alias(ctx, console_journal_vv):
    d = {"key1": "value1", "key2": "value2", "key3": "value3", "key4": "value4"}
    ctx.journal_event("test", {"d1": d, "d2": d})

    out = console_journal_vv(ctx)
    assert "test d1: &" in out, out
    assert "     d2: *" in out, out


def test_console_journal_q_empty(console_journal_q):
    ctx = TurnContext(
        dialog={"channel_name": "test", "user_id": "321"},
        message={"text": "hello world"},
        intents=IntentsResult.resolve([RecognizedIntent("i1", 1)]),
        entities=EntitiesResult.resolve([RecognizedEntity("e1", 1, "one", 2, 34)]),
    )
    ctx.commands.append({"text": markup.Value([markup.Item(markup.TEXT, "Hello, John!")])})
    ctx.journal_event("event1", {"data": 1})
    ctx.debug(("what is here?", {"xxx": "yyy"}))
    ctx.warning("something wrong")

    assert console_journal_q(ctx) == ""


def test_console_journal_q_error(console_journal_q):
    ctx = TurnContext(
        dialog={"channel_name": "test", "user_id": "321"},
        message={"text": "hello world"},
        intents=IntentsResult.resolve([RecognizedIntent("i1", 1)]),
        entities=EntitiesResult.resolve([RecognizedEntity("e1", 1, "one", 2, 34)]),
    )
    ctx.commands.append({"text": markup.Value([markup.Item(markup.TEXT, "Hello, John!")])})
    ctx.journal_event("event1", {"data": 1})
    ctx.debug(("what is here?", {"xxx": "yyy"}))
    ctx.warning("something wrong")
    ctx.set_error(BotError("some error"))

    assert console_journal_q(ctx).strip() == "✗  some error"


@pytest.mark.parametrize(
    "state_field",
    (
        "user",
        "slots",
    ),
)
def test_console_journal_diff(ctx, console_journal_v, state_field):
    getattr(ctx.state, state_field)["test"] = 1
    del getattr(ctx.state, state_field)["test"]

    out = [s.strip().split() for s in console_journal_v(ctx).splitlines()]
    assert ["journal_events"] in out, out
    assert [f"{state_field}.test", "=", "1"] in out, out
    assert ["❌", "delete", f"{state_field}.test"] in out, out


def test_console_journal_diff_clear(ctx, console_journal_v):
    ctx.state.slots["test1"] = 1
    ctx.state.slots["test2"] = 1
    ctx.clear_state_variables()

    out = [s.strip().split() for s in console_journal_v(ctx).splitlines()]
    assert ["journal_events"] in out, out
    assert ["❌", "delete", "slots.test1"] in out, out
    assert ["❌", "delete", "slots.test2"] in out, out


def test_console_journal_diff_clear_empty(ctx, console_journal_v):
    ctx.clear_state_variables()

    out = console_journal_v(ctx)
    assert f"journal_events" not in out, out


@pytest.mark.parametrize(
    "state_field",
    (
        "user",
        "slots",
    ),
)
def test_console_journal_full(ctx, console_journal_vv, state_field):
    getattr(ctx.state, state_field)["test"] = 1

    out = console_journal_vv(ctx)
    assert f"{state_field}\n" in out, out
    assert ".test 1" in out, out


@pytest.mark.parametrize(
    "state_field",
    (
        "user",
        "slots",
    ),
)
def test_console_journal_full_if_error(ctx, console_journal_v, state_field):
    getattr(ctx.state, state_field)["test"] = 1
    ctx.set_error(BotError("some error"))

    out = console_journal_v(ctx)
    assert f"{state_field}\n" in out, out
    assert ".test 1" in out, out


async def test_jourtnal_slot_filling(ctx, console_journal_vv):
    model = SlotFilling(
        SlotSchema(many=True).loads(
            """
            - name: slot1
              check_for: true
              found: "<prompt_again />" """
        ),
        [],
    )
    await model(ctx, ctx.state.components.setdefault("xxx", {}))

    out = console_journal_vv(ctx)
    assert "journal_events\n" in out, out
    assert "slot_filling  slot: slot1", out
    assert "slots.slot1 = True", out
    assert "found         slot: slot1", out
    assert "                 control_command: prompt_again", out
    assert "❌ delete     slots.slot1", out


def _create_console_journal(verbosity):
    console = Console(force_terminal=False, soft_wrap=True)
    journal = PrettyJournal(verbosity=verbosity, console=console)

    def call(ctx):
        with console.capture() as capture:
            journal(ctx)
        return capture.get()

    return call
